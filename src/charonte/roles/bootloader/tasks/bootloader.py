from io import StringIO
from omegaconf import OmegaConf
import omegaconf
from pyinfra.api.operation import add_op
from pyinfra.operations import server, files

def checkBootMode(host):
    efiDir = host.get_fact(files.Directory, path="/sys/firmware/efi/")
    if efiDir:
        print(f"The system is booted in UEFI mode.")
        return "UEFI"
    else:
        print("The system is booted in BIOS mode.")
        return "BIOS"

def installBootloader(state, ChObolo, firmware):
    bootloader=ChObolo.get('bootloader')
    partitioningTab=ChObolo.get('partitioning')
    disk=partitioningTab.get('disk')
    bootPart=next((p for p in partitioningTab.partitions if p.get('important') == 'boot'), None)
    bootMount=bootPart.get('mountpoint') if bootPart else None
    rootPart=next((p for p in partitioningTab.partitions if p.get('important') == 'root'), None)
    rootName=rootPart.get('name') if rootPart else None
    if bootMount:
        if disk:
            if not bootloader:
                print("no bootloader set. using grub.")
                bootloader = "grub"
            if rootName:
                match bootloader:
                    case "grub":
                        if firmware == "BIOS":
                            add_op(
                                state,
                                server.shell,
                                name=f"Installing grub in BIOS",
                                commands=[f"grub-install --target=i386-pc {disk} --bootloader-id={rootName}"],
                                _sudo=True
                            )
                        elif firmware == "UEFI":
                            grubCfgPath = f"{bootMount}/grub/grub.cfg"
                            commands=[f"test -f {grubCfgPath} || grub-install --target=x86_64-efi --efi-directory={bootMount} --bootloader-id={rootName}"]
                            add_op(
                                state,
                                server.shell,
                                name=f"Installing grub in UEFI",
                                commands=commands,
                                _sudo=True
                            )
                        else:
                            print("Unsupported boot mode.")
                            return
                        add_op(
                            state,
                            server.shell,
                            name="Generating grub.cfg",
                            commands=[f"grub-mkconfig -o {bootMount}/grub/grub.cfg"],
                            _sudo=True
                        )
                    case "refind":
                        hostname=ChObolo.get('hostname','charonte')
                        desiredRefindConf = f"""
                            menuentry "{hostname}" {{
                                icon /EFI/refind/icons/os_arch.png
                                volume "{rootName}"
                                loader /vmlinuz-linux
                                initrd /initramfs-linux.img
                                options "root=LABEL={rootName} rw add_efi_memmap"
                                submenuentry "fallback" {{
                                    initrd /initramfs-linux-fallback.img
                                }}
                            }}
                            """

                        if firmware == "UEFI":
                            refind_cfg_path = f"{bootMount}/efi/refind/refind.conf"
                            commands=[f"test -f {refind_cfg_path} || refind-install"]
                            add_op(
                                state,
                                server.shell,
                                name=f"Installing refind in UEFI",
                                commands=commands,
                                _sudo=True
                            )
                            add_op(
                                state,
                                files.block,
                                src=StringIO(desiredRefindConf),
                                marker=f"# BEGIN {hostname} CHARONTE MANAGED.\nEND {hostname} CHARONTE MANAGED.",
                                dest=f"{bootMount}/efi/refind/refind.conf",
                                _sudo=True
                            )
                        else:
                            print("Unsupported boot mode.")
                    case _:
                        print("No supported Bootloader")
            else:
                print("root should have a name.")
        else:
            print("No disk declared.")
    else:
        print("Boot should have a mountpoint.")

def run_bootloader(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)
    firmware = checkBootMode(host)
    installBootloader(state, ChObolo, firmware)
