import re
from typing import Any

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from pyinfra.api.operation import add_op
from pyinfra.facts.files import Directory
from pyinfra.operations import files, server


class BootloaderRole(Role):
    def __init__(self):
        super().__init__(
            name="Install and Configure Bootloader",
            needs_secrets=False,
            necessary_chobolo_keys=["bootloader", "partitioning", "hostname"],
        )

    @staticmethod
    def _is_valid_disk_path(path: str) -> bool:
        return bool(re.match(r"^/dev/[a-zA-Z0-9/]+$", path))

    @staticmethod
    def _is_valid_label(label: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", label))

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        path = "/sys/firmware/efi/"
        firmware = "UEFI" if host.get_fact(Directory, path=path) else "BIOS"

        bootloader = chobolo.get("bootloader", "grub")
        hostname = chobolo.get("hostname", "charonte")
        partitioning_tab = chobolo.get("partitioning", {})

        disk = partitioning_tab.get("disk")
        partitions = partitioning_tab.get("partitions", [])

        boot_part = next((p for p in partitions if p.get("important") == "boot"), None)
        boot_mount = boot_part.get("mountpoint") if boot_part else None

        root_part = next((p for p in partitions if p.get("important") == "root"), None)
        root_name = root_part.get("name") if root_part else None

        return {
            "firmware": firmware,
            "bootloader": bootloader,
            "hostname": hostname,
            "disk": disk,
            "boot_mount": boot_mount,
            "root_name": root_name,
        }

    def delta(self, context: dict[str, Any] = {}) -> Delta:
        errors = []

        boot_mount = context.get("boot_mount")
        disk = context.get("disk")
        root_name = context.get("root_name")
        hostname = context.get("hostname")

        if not boot_mount:
            errors.append("Boot partition must have a mountpoint.")
        if not disk or not self._is_valid_disk_path(disk):
            errors.append(f"Disk path '{disk}' is invalid or missing.")
        if not root_name or not self._is_valid_label(root_name):
            errors.append(f"Root partition name '{root_name}' is invalid or missing.")
        if hostname and not self._is_valid_label(hostname):
            errors.append(f"Hostname '{hostname}' contains invalid characters.")

        if errors:
            return Delta(metadata={"errors": errors})

        return Delta(
            metadata={
                "firmware": context.get("firmware"),
                "bootloader": context.get("bootloader"),
                "hostname": context.get("hostname"),
                "disk": context.get("disk"),
                "boot_mount": context.get("boot_mount"),
                "root_name": context.get("root_name"),
            }
        )

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        errors = delta.metadata.get("errors", [])
        if errors:
            return ResultPayload(success=False, message=[], error=errors, data={})

        firmware = delta.metadata.get("firmware")
        bootloader = delta.metadata.get("bootloader")
        hostname = delta.metadata.get("hostname")
        disk = delta.metadata.get("disk")
        boot_mount = delta.metadata.get("boot_mount")
        root_name = delta.metadata.get("root_name")

        match bootloader:
            case "grub":
                if firmware == "BIOS":
                    grub_command = [
                        "grub-install",
                        "--target=i386-pc",
                        "--bootloader-id",
                        root_name,
                        disk,
                    ]
                    add_op(
                        state,
                        server.shell,
                        name="Installing grub in BIOS",
                        commands=[" ".join(grub_command)],
                        _sudo=True,
                    )
                elif firmware == "UEFI":
                    grub_cfg_path = f"{boot_mount}/grub/grub.cfg"
                    grub_command = f"test -f {grub_cfg_path} || grub-install --target=x86_64-efi --efi-directory={boot_mount} --bootloader-id={root_name}"
                    add_op(
                        state,
                        server.shell,
                        name="Installing grub in UEFI",
                        commands=[grub_command],
                        _sudo=True,
                    )
                else:
                    return ResultPayload(
                        success=False,
                        message=[],
                        error=["Unsupported boot mode."],
                        data={},
                    )

                add_op(
                    state,
                    server.shell,
                    name="Generating grub.cfg",
                    commands=[f"grub-mkconfig -o {boot_mount}/grub/grub.cfg"],
                    _sudo=True,
                )

            case "refind":
                desired_refind_conf = f"""
                    menuentry "{hostname}" {{
                        icon /EFI/refind/icons/os_arch.png
                        volume "{root_name}"
                        loader /vmlinuz-linux
                        initrd /initramfs-linux.img
                        options "root=LABEL={root_name} rw add_efi_memmap"
                        submenuentry "fallback" {{
                            initrd /initramfs-linux-fallback.img
                        }}
                    }}
                    """
                if firmware == "UEFI":
                    refind_cfg_path = f"{boot_mount}/efi/refind/refind.conf"
                    refind_command = f"test -f {refind_cfg_path} || refind-install"
                    add_op(
                        state,
                        server.shell,
                        name="Installing rEFInd in UEFI",
                        commands=[refind_command],
                        _sudo=True,
                    )
                    add_op(
                        state,
                        files.block,
                        name=f"Ensure rEFInd menuentry for {hostname}",
                        path=refind_cfg_path,
                        content=desired_refind_conf,
                        marker=f"# {{mark}} CH-ARONTE MANAGED BLOCK FOR {hostname}",
                        _sudo=True,
                    )
                else:
                    return ResultPayload(
                        success=False,
                        message=[],
                        error=["Unsupported boot mode for rEFInd."],
                        data={},
                    )

            case _:
                return ResultPayload(
                    success=False,
                    message=[],
                    error=[f"No supported bootloader specified: {bootloader}"],
                    data={},
                )

        return ResultPayload(success=True, message=[], error=[], data={})
