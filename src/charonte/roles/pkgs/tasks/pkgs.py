#!/usr/bin/env python3
import re
from typing import cast
from omegaconf import OmegaConf

from pyinfra.api.operation import add_op
from pyinfra.operations import server
from pyinfra.facts.server import Command
from pyinfra.facts.files import Directory

def validate_input(input: list[str]) -> list[str]:
    output = []
    for i in input:
        if not re.match(r'^[a-zA-Z0-9_-]+$', i):
            print(f"Invalid package name: {i}, ignoring.")
            continue

        output.append(i)
    return output

def checkBootMode(host):
    path = "/sys/firmware/efi/"
    if host.get_fact(Directory, path=path):
        print("System is booted in UEFI mode.")
        return "UEFI"
    else:
        print("System is booted in BIOS mode.")
        return "BIOS"

def natPkgLogic(ChObolo, aur_helper_list, native, dependencies, host):
    pkgs = ChObolo.get('packages', [])
    necOver = ChObolo.get('baseOverride', [])
    necessaries = ["linux", "linux-firmware", "linux-headers", "base", "base-devel", "nano", "networkmanager", "openssh", "git", "ansible", "arch-install-scripts", "sops"]

    if necOver:
        necessaries = necOver

    Users = ChObolo.get('users', [])

    basePkgs = list(pkgs + necessaries + [user.shell for user in Users if user and 'shell' in user])

    if aur_helper_list:
        basePkgs.extend(aur_helper_list)

    Parts = ChObolo.get('partitioning', [])
    if Parts and hasattr(Parts, 'partitions'):
        root_partition = next((p for p in Parts.partitions if p.get('important') == 'root'), None)
        if root_partition and root_partition.get("type") == "btrfs":
            basePkgs.append("btrfs-progs")

        boot_partition = next((p for p in Parts.partitions if p.get('important') == 'boot'), None)
        if boot_partition:
            basePkgs.append("dosfstools")


    Firm = checkBootMode(host)
    Boot = ChObolo.get('bootloader', [])

    if Firm and Firm=="UEFI" and Boot and Boot=="grub":
        basePkgs.append("efibootmgr")

    if Boot:
        basePkgs.append(ChObolo.bootloader)
    else:
        basePkgs.append("grub")

    toAddNative = sorted(set(basePkgs) - set(native) - set(dependencies))
    toRemoveNative = sorted(set(native) - set(basePkgs))
    return toAddNative, toRemoveNative

def aurPkgLogic(ChObolo, aur_helper, aur, aurDependencies, native):
    if aur_helper:
        if aur_helper not in aur and aur_helper not in native:
            aur_helper = None
    if 'aurPackages' in ChObolo:
        aurPkgs = ChObolo.get('aurPackages', [])
        toRemoveAur = sorted(set(aur) - set(aurPkgs))
        toAddAur = sorted(set(aurPkgs) - set(aur) - set(aurDependencies))
        return toAddAur, toRemoveAur, aur_helper
    return [], [], aur_helper

def nativeLogic(state, toAddNative, toRemoveNative, skip):
    """Applies changes to Native packages"""
    if toAddNative or toRemoveNative:
        toAddNative = validate_input(toAddNative)
        toRemoveNative = validate_input(toRemoveNative)
        print("\n--- Native packages to Add: ---")
        for pkg in toAddNative:
            print(pkg)

        print("--- Native packages to be removed: ---")
        for pkg in toRemoveNative:
            print(pkg)

        confirm = "y" if skip else input("\nIs This correct (Y/n)? ")
        if confirm.lower() in ["y", "yes", "", "s", "sim"]:
            print("\nInitiating Native package management...")
            if toAddNative:
                # We use server.shell here cause all of the idempotency has already
                # Been calculated. The use of packages.pacman makes it slower.
                add_cmd = [
                    'pacman',
                    '-S',
                    '--needed',
                    '--noconfirm',
                    '--needed',
                    '--noprogressbar',
                    '--quiet',
                    '--asexplicit'
                ]
                add_cmd.extend(toAddNative)
                add_op(
                    state,
                    server.shell,
                    name="Installing packages",
                    commands=' '.join(add_cmd),
                    _sudo=True
                )
            if toRemoveNative:
                # We use server.shell here cause all of the idempotency has already
                # Been calculated. The use of packages.pacman makes it slower.
                remove_cmd = [
                    'pacman',
                    '-Rcns',
                    '--noconfirm',
                    '--noprogressbar',
                    '--quiet',
                ]
                remove_cmd.extend(toRemoveNative)
                add_op(
                    state,
                    server.shell,
                    name="Uninstalling packages",
                    commands = ' '.join(remove_cmd),
                    _sudo=True
                )
    else:
        print("No native packages to be managed.")

def aurLogic(state, toAddAur, toRemoveAur, aur_helper, skip):
    """Applies AUR changes"""
    aur_work_to_do = toAddAur or toRemoveAur

    if aur_work_to_do and aur_helper:
        toAddAur, toRemoveAur = validate_input(toAddAur), validate_input(toRemoveAur)
        print("\n--- AUR packages to Remove: ---")
        for pkg in toRemoveAur:
            print(pkg)

        print("\n--- AUR packages to Add: ---")
        for pkg in toAddAur:
            print(pkg)

        confirmAur = "y" if skip else input("\nIs This correct (Y/n)? ")
        if confirmAur.lower() in ["y", "yes", "", "s", "sim"]:
            print("\nInitiating AUR package management...")
            if toAddAur:
                # We use server.shell here cause all of the idempotency has already
                # Been calculated.
                add_command = [
                    aur_helper,
                    '-S',
                    '--noconfirm',
                    '--answerdiff', 'None',
                    '--answerclean', 'All',
                    '--removemake'
                ]
                add_command.extend(toAddAur)
                add_op(
                    state,
                    server.shell,
                    commands=' '.join(add_command),
                    name="Instaling AUR packages.",
                )
            if toRemoveAur:
                # We use server.shell here cause all of the idempotency has already
                # Been calculated.
                remove_command = [
                    aur_helper,
                    '-Rns',
                    '--noconfirm'
                ]
                remove_command.extend(toRemoveAur)
                add_op(
                    state,
                    server.shell,
                    commands=' '.join(remove_command),
                    name="Uninstalling AUR packages.",
                )
    elif aur_work_to_do and not aur_helper:
        print("\nThere ARE aur packages to be managed, but you still don't have an AUR helper.\nIf you have declared an AUR helper run python3 main.py aur -e path/to/ch-obolo to manage your aur helpers.\nIf you have an AUR helper, declare it under aurHelpers")
    else:
        print("\nNo AUR packages to be managed.")

def run_all_pkg_logic(state, host, chobolo_path, skip):
    """Point of entry for all packages"""
    ChObolo = OmegaConf.load(chobolo_path)
    ChObolo = cast(dict, ChObolo)

    native = host.get_fact(Command, "pacman -Qqen || true").strip().splitlines()
    dependencies = host.get_fact(Command, "pacman -Qqdn || true").strip().splitlines()

    aur = host.get_fact(Command, "pacman -Qqem || true").strip().splitlines()
    aurDependencies= host.get_fact(Command, "pacman -Qqdm || true").strip().splitlines()

    aur_helper_list = ChObolo.get('aurHelpers', [])
    aur_helper = aur_helper_list[0] if aur_helper_list else None

    toAddNative, toRemoveNative = natPkgLogic(ChObolo, aur_helper_list, native, dependencies, host)
    toAddAur, toRemoveAur, aur_helper = aurPkgLogic(ChObolo, aur_helper, aur, aurDependencies, native)

    nativeLogic(state, toAddNative, toRemoveNative, skip)
    aurLogic(state, toAddAur, toRemoveAur, aur_helper, skip)

def run_nat_logic(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)
    ChObolo = cast(dict, ChObolo)

    try:
        native = host.get_fact(Command, "pacman -Qqen || true").strip().splitlines()
    except Exception:
        native = []
    try:
        dependencies = host.get_fact(Command, "pacman -Qqdn || true").strip().splitlines()
    except Exception:
        dependencies = []
    aur_helper_list = ChObolo.get('aurHelpers', [])


    toAddNative, toRemoveNative = natPkgLogic(ChObolo, aur_helper_list, native, dependencies, host)
    nativeLogic(state, toAddNative, toRemoveNative, skip)

def run_aur_logic(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)
    ChObolo = cast(dict, ChObolo)

    try:
        aur = host.get_fact(Command, "pacman -Qqem || true").strip().splitlines()
    except Exception:
        aur = []

    try:
        aurDependencies = host.get_fact(Command, "pacman -Qqdm || true").strip().splitlines()
    except Exception:
        aurDependencies = []

    try:
        native = host.get_fact(Command, "pacman -Qqen || true").strip().splitlines()
    except Exception:
        native = []

    aur_helper_list = ChObolo.get('aurHelpers', [])
    aur_helper = aur_helper_list[0] if aur_helper_list else None

    toAddAur, toRemoveAur, aur_helper = aurPkgLogic(ChObolo, aur_helper, aur, aurDependencies, native)
    aurLogic(state, toAddAur, toRemoveAur, aur_helper, skip)
