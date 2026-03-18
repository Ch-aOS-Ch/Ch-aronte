import re
from typing import Any

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from pyinfra.api.operation import add_op
from pyinfra.facts.files import Directory
from pyinfra.facts.server import Command
from pyinfra.operations import server


class _PkgsBaseRole(Role):
    """
    Base class for package management roles, containing common logic.
    """

    @staticmethod
    def _validate_input(input_list: list[str]) -> tuple[list[str], list[str]]:
        valid = []
        invalid = []
        for i in input_list:
            if not re.match(r"^[a-zA-Z0-9._+-]+$", i):
                invalid.append(i)
                continue
            valid.append(i)
        return valid, invalid

    @staticmethod
    def _check_boot_mode(host) -> str:
        path = "/sys/firmware/efi/"
        if host.get_fact(Directory, path=path):
            return "UEFI"
        else:
            return "BIOS"

    def _get_native_delta(self, context: dict[str, Any]) -> tuple[list[str], list[str]]:
        ChObolo = context
        aur_helper_list = ChObolo.get("aurHelpers", [])
        native = context.get("native_packages", [])
        dependencies = context.get("native_dependencies", [])

        pkgs = ChObolo.get("packages", [])
        necOver = ChObolo.get("baseOverride", [])
        necessaries = [
            "linux",
            "linux-firmware",
            "linux-headers",
            "base",
            "base-devel",
            "nano",
            "networkmanager",
            "openssh",
            "git",
            "ansible",
            "arch-install-scripts",
            "sops",
        ]

        if necOver:
            necessaries = necOver

        Users = ChObolo.get("users", [])
        basePkgs = list(
            pkgs
            + necessaries
            + [user["shell"] for user in Users if user and "shell" in user]
        )

        if aur_helper_list:
            basePkgs.extend(aur_helper_list)

        Parts = ChObolo.get("partitioning", {})
        if Parts and "partitions" in Parts:
            partitions = Parts.get("partitions", [])
            root_partition = next(
                (p for p in partitions if p.get("important") == "root"), None
            )
            if root_partition and root_partition.get("type") == "btrfs":
                basePkgs.append("btrfs-progs")

            boot_partition = next(
                (p for p in partitions if p.get("important") == "boot"), None
            )
            if boot_partition:
                basePkgs.append("dosfstools")

        Firm = context.get("boot_mode")
        Boot = ChObolo.get("bootloader")

        if Firm and Firm == "UEFI" and Boot and Boot == "grub":
            basePkgs.append("efibootmgr")

        if Boot:
            basePkgs.append(Boot)
        else:
            basePkgs.append("grub")

        toAddNative = sorted(set(basePkgs) - set(native) - set(dependencies))
        toRemoveNative = sorted(set(native) - set(basePkgs))
        return toAddNative, toRemoveNative

    def _get_aur_delta(
        self, context: dict[str, Any]
    ) -> tuple[list[str], list[str], str | None]:
        ChObolo = context
        aur = context.get("aur_packages", [])
        aurDependencies = context.get("aur_dependencies", [])
        native = context.get("native_packages", [])

        aur_helper_list = ChObolo.get("aurHelpers", [])
        aur_helper = aur_helper_list[0] if aur_helper_list else None

        if aur_helper:
            if aur_helper not in aur and aur_helper not in native:
                aur_helper = None

        aurPkgs = ChObolo.get("aurPackages", [])
        if aurPkgs:
            toRemoveAur = sorted(set(aur) - set(aurPkgs))
            toAddAur = sorted(set(aurPkgs) - set(aur) - set(aurDependencies))
            return toAddAur, toRemoveAur, aur_helper
        return [], [], aur_helper

    def _plan_native(self, state, delta: Delta) -> list[str]:
        to_add_native = delta.to_add.get("native", [])
        to_remove_native = delta.to_remove.get("native", [])

        if not to_add_native and not to_remove_native:
            return []

        if to_add_native:
            add_cmd = [
                "pacman",
                "-S",
                "--needed",
                "--noconfirm",
                "--noprogressbar",
                "--asexplicit",
            ]
            add_cmd.extend(to_add_native)
            add_op(
                state,
                server.shell,
                name="Installing native packages",
                commands=" ".join(add_cmd),
                _sudo=True,
            )
        if to_remove_native:
            remove_cmd = ["pacman", "-Rcns", "--noconfirm", "--noprogressbar"]
            remove_cmd.extend(to_remove_native)
            add_op(
                state,
                server.shell,
                name="Uninstalling native packages",
                commands=" ".join(remove_cmd),
                _sudo=True,
            )
        return []

    def _plan_aur(self, state, delta: Delta) -> list[str]:
        to_add_aur = delta.to_add.get("aur", [])
        to_remove_aur = delta.to_remove.get("aur", [])
        aur_helper = delta.metadata.get("aur_helper")
        aur_work_to_do = to_add_aur or to_remove_aur

        if not aur_work_to_do:
            return []

        if not aur_helper:
            return ["AUR_HELPER_MISSING"]

        if to_add_aur:
            add_command = [
                aur_helper,
                "-S",
                "--noconfirm",
                "--answerdiff",
                "None",
                "--answerclean",
                "All",
                "--removemake",
            ]
            add_command.extend(to_add_aur)
            add_op(
                state,
                server.shell,
                commands=" ".join(add_command),
                name="Installing AUR packages.",
            )
        if to_remove_aur:
            remove_command = [aur_helper, "-Rns", "--noconfirm"]
            remove_command.extend(to_remove_aur)
            add_op(
                state,
                server.shell,
                commands=" ".join(remove_command),
                name="Uninstalling AUR packages.",
            )
        return []


class PkgsNativeRole(_PkgsBaseRole):
    """
    Manages native packages for Arch Linux.
    """

    def __init__(self):
        super().__init__(
            name="Install Arch Native Packages",
            needs_secrets=False,
            necessary_chobolo_keys=[
                "packages",
                "baseOverride",
                "users",
                "partitioning",
                "bootloader",
                "aurHelpers",
            ],
        )

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        context = chobolo.copy()
        try:
            context["native_packages"] = (
                host.get_fact(Command, "pacman -Qqen || true").strip().splitlines()
            )
        except Exception:
            context["native_packages"] = []
        try:
            context["native_dependencies"] = (
                host.get_fact(Command, "pacman -Qqdn || true").strip().splitlines()
            )
        except Exception:
            context["native_dependencies"] = []
        context["boot_mode"] = self._check_boot_mode(host)
        return context

    def delta(self, state, context: dict[str, Any] = {}) -> Delta:
        to_add_native, to_remove_native = self._get_native_delta(context)
        valid_add, invalid_add = self._validate_input(to_add_native)
        valid_remove, invalid_remove = self._validate_input(to_remove_native)
        return Delta(
            to_add={"native": valid_add},
            to_remove={"native": valid_remove},
            metadata={"invalid_packages": invalid_add + invalid_remove},
        )

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        errors = [
            f"INVALID_PACKAGE_NAME:{pkg}"
            for pkg in delta.metadata.get("invalid_packages", [])
        ]
        errors.extend(self._plan_native(state, delta))
        return ResultPayload(success=not errors, message=[], error=errors, data=delta)


class PkgsAurRole(_PkgsBaseRole):
    """
    Manages AUR packages for Arch Linux.
    """

    def __init__(self):
        super().__init__(
            name="Install AUR Packages",
            needs_secrets=False,
            necessary_chobolo_keys=["aurPackages", "aurHelpers"],
        )

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        context = chobolo.copy()
        try:
            context["native_packages"] = (
                host.get_fact(Command, "pacman -Qqen || true").strip().splitlines()
            )
        except Exception:
            context["native_packages"] = []
        try:
            context["aur_packages"] = (
                host.get_fact(Command, "pacman -Qqem || true").strip().splitlines()
            )
        except Exception:
            context["aur_packages"] = []
        try:
            context["aur_dependencies"] = (
                host.get_fact(Command, "pacman -Qqdm || true").strip().splitlines()
            )
        except Exception:
            context["aur_dependencies"] = []
        return context

    def delta(self, state, context: dict[str, Any] = {}) -> Delta:
        to_add_aur, to_remove_aur, aur_helper = self._get_aur_delta(context)
        valid_add, invalid_add = self._validate_input(to_add_aur)
        valid_remove, invalid_remove = self._validate_input(to_remove_aur)
        return Delta(
            to_add={"aur": valid_add},
            to_remove={"aur": valid_remove},
            metadata={
                "aur_helper": aur_helper,
                "invalid_packages": invalid_add + invalid_remove,
            },
        )

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        errors = [
            f"INVALID_PACKAGE_NAME:{pkg}"
            for pkg in delta.metadata.get("invalid_packages", [])
        ]
        errors.extend(self._plan_aur(state, delta))
        return ResultPayload(success=not errors, message=[], error=errors, data=delta)


class PkgsAllRole(_PkgsBaseRole):
    """
    Manages both native and AUR packages for Arch Linux.
    """

    def __init__(self):
        super().__init__(
            name="Install All Declared Packages for Arch Linux",
            needs_secrets=False,
            necessary_chobolo_keys=[
                "packages",
                "baseOverride",
                "users",
                "partitioning",
                "bootloader",
                "aurPackages",
                "aurHelpers",
            ],
        )

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        context = chobolo.copy()
        try:
            context["native_packages"] = (
                host.get_fact(Command, "pacman -Qqen || true").strip().splitlines()
            )
        except Exception:
            context["native_packages"] = []
        try:
            context["native_dependencies"] = (
                host.get_fact(Command, "pacman -Qqdn || true").strip().splitlines()
            )
        except Exception:
            context["native_dependencies"] = []
        try:
            context["aur_packages"] = (
                host.get_fact(Command, "pacman -Qqem || true").strip().splitlines()
            )
        except Exception:
            context["aur_packages"] = []
        try:
            context["aur_dependencies"] = (
                host.get_fact(Command, "pacman -Qqdm || true").strip().splitlines()
            )
        except Exception:
            context["aur_dependencies"] = []
        context["boot_mode"] = self._check_boot_mode(host)
        return context

    def delta(self, state, context: dict[str, Any] = {}) -> Delta:
        to_add_native, to_remove_native = self._get_native_delta(context)
        to_add_aur, to_remove_aur, aur_helper = self._get_aur_delta(context)

        valid_add_nat, invalid_add_nat = self._validate_input(to_add_native)
        valid_remove_nat, invalid_remove_nat = self._validate_input(to_remove_native)
        valid_add_aur, invalid_add_aur = self._validate_input(to_add_aur)
        valid_remove_aur, invalid_remove_aur = self._validate_input(to_remove_aur)

        invalid_pkgs = (
            invalid_add_nat + invalid_remove_nat + invalid_add_aur + invalid_remove_aur
        )

        return Delta(
            to_add={
                "native": valid_add_nat,
                "aur": valid_add_aur,
            },
            to_remove={
                "native": valid_remove_nat,
                "aur": valid_remove_aur,
            },
            metadata={"aur_helper": aur_helper, "invalid_packages": invalid_pkgs},
        )

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        errors = [
            f"INVALID_PACKAGE_NAME:{pkg}"
            for pkg in delta.metadata.get("invalid_packages", [])
        ]
        errors.extend(self._plan_native(state, delta))
        errors.extend(self._plan_aur(state, delta))
        return ResultPayload(success=not errors, message=[], error=errors, data=delta)
