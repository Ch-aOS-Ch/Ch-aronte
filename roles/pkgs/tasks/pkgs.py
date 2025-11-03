#!/usr/bin/env python3
from omegaconf import OmegaConf

from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.operations import server, pacman
from pyinfra.facts.server import Command

def pkgLogic(host, chobolo_path):
    """Get the packages delta"""
    ChObolo = OmegaConf.load(chobolo_path)
    aur_helper = ChObolo.aur_helpers[0] if ChObolo.aur_helpers else None

    basePkgs = list(ChObolo.pacotes + ChObolo.pacotes_base_override + [user.shell for user in ChObolo.users if 'shell' in user])
    if aur_helper:
        basePkgs.append(aur_helper)

    root_partition = next((p for p in ChObolo.particoes.partitions if p.get('important') == 'root'), None)
    if root_partition and root_partition.type=="btrfs":
        basePkgs.append("btrfs-progs")

    boot_partition = next((p for p in ChObolo.particoes.partitions if p.get('important') == 'boot'), None)
    if boot_partition:
        basePkgs.append("dosfstools")

    if ChObolo.firmware=="UEFI" and ChObolo.bootloader=="grub":
        basePkgs.append("efibootmgr")

    if ChObolo.bootloader:
        basePkgs.append(ChObolo.bootloader)
    else:
        basePkgs.append("grub")

    wntNotNatPkgs = ChObolo.aur_pkgs

    native = host.get_fact(Command, "pacman -Qqen").strip().splitlines()
    dependencies = host.get_fact(Command, "pacman -Qqdn").strip().splitlines()
    aur = host.get_fact(Command, "pacman -Qqem").strip().splitlines()
    aurDependencies= host.get_fact(Command, "pacman -Qqdm").strip().splitlines()

    toRemoveNative = sorted(set(native) - set(basePkgs))
    toRemoveAur = sorted(set(aur) - set(wntNotNatPkgs))

    toAddNative = sorted(set(basePkgs) - set(native) - set(dependencies))
    toAddAur = sorted(set(wntNotNatPkgs) - set(aur) - set(aurDependencies))

    return toAddNative, toRemoveNative, toAddAur, toRemoveAur, aur_helper

def nativeLogic(state, toAddNative, toRemoveNative, skip, dry):
    """Applies changes to Native packages""" # <~ Btw, I'm using """ here cause it get's a better highlighting on my screen than #
    if toAddNative or toRemoveNative:
        print("--- Native packages to be removed: ---")
        for pkg in toRemoveNative:
            print(pkg)

        print("\n--- Native packages to Add: ---")
        for pkg in toAddNative:
            print(pkg)

        confirm = "y" if skip else input("\nIs This correct (Y/n)? ")
        if confirm.lower() in ["y", "yes", "", "s", "sim"]:
            print("\nInitiating Native package management...")
            if toAddNative:
                add_op(
                    state,
                    pacman.packages,
                    name="Installing packages",
                    packages=toAddNative,
                    present=True,
                    update=True,
                    _sudo=True
                )
            if toRemoveNative:
                add_op(
                    state,
                    pacman.packages,
                    name="Uninstalling packages",
                    packages=toRemoveNative,
                    present=False,
                    update=True,
                    _sudo=True
                )
    else:
        print("No native packages to be managed.")

def aurLogic(state, toAddAur, toRemoveAur, aur_helper, skip, dry):
    """Applies AUR changes"""
    aur_work_to_do = toAddAur or toRemoveAur

    print("\nInitiating AUR package management...")
    if aur_work_to_do and aur_helper:
        print("\n--- AUR packages to Remove: ---")
        for pkg in toRemoveAur:
            print(pkg)

        print("\n--- AUR packages to Add: ---")
        for pkg in toAddAur:
            print(pkg)

        confirmAur = "y" if skip else input("\nIs This correct (Y/n)? ")
        if confirmAur.lower() in ["y", "yes", "", "s", "sim"]:
            if toAddAur:
                packagesStr = " ".join(toAddAur)
                fullCommand = f"{aur_helper} -S --noconfirm --answerdiff None --answerclean All --removemake {packagesStr}"
                add_op(
                    state,
                    server.shell,
                    commands=[fullCommand],
                    name="Instaling AUR packages.",
                )
            if toRemoveAur:
                packagesRmvStr = " ".join(toRemoveAur)
                fullRemoveCommand = f"{aur_helper} -Rns --noconfirm {packagesRmvStr}"
                add_op(
                    state,
                    server.shell,
                    commands=[fullRemoveCommand],
                    name="Uninstalling AUR packages.",
                )
    elif aur_work_to_do and not aur_helper:
        print("\nThere ARE aur packages to be managed, but you still don't have an AUR helper.\n run python3 main.py aur -e path/to/ch-obolo to manage your aur helpers.")
    else:
        print("\nNo AUR packages to be managed.")

def run_all_pkg_logic(state, host, chobolo_path, skip, dry):
    """Point of entry for this role"""
    toAddNative, toRemoveNative, toAddAur, toRemoveAur, aur_helper = pkgLogic(host, chobolo_path)
    nativeLogic(state, toAddNative, toRemoveNative, skip, dry)
    aurLogic(state, toAddAur, toRemoveAur, aur_helper, skip, dry)
    if not dry:
        run_ops(state)
    else:
        print(f"dry mode active, skipping.")
