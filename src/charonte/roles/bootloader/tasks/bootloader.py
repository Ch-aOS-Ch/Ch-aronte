from io import StringIO
from omegaconf import OmegaConf
from pyinfra.api.operation import add_op
from pyinfra.operations import server, files
from pyinfra.facts.files import Directory
import re

def isValidDiskPath(path):
    return re.match(r'^/dev/[a-zA-Z0-9/]+$', path)

def isValidLabel(label):
    return re.match(r'^[a-zA-Z0-9_-]+$', label)

def checkBootMode(host):
    path = "/sys/firmware/efi/"
    if host.get_fact(Directory, path=path):
        print("System is booted in UEFI mode.")
        return "UEFI"
    else:
        print("System is booted in BIOS mode.")
        return "BIOS"

def installBootloaderSecure(state, chObolo, firmware):
    bootloader = chObolo.get('bootloader')
    partitioningTab = chObolo.get('partitioning')
    disk = partitioningTab.get('disk')
    bootPart = next((p for p in partitioningTab.partitions if p.get('important') == 'boot'), None)
    bootMount = bootPart.get('mountpoint') if bootPart else None
    rootPart = next((p for p in partitioningTab.partitions if p.get('important') == 'root'), None)
    rootName = rootPart.get('name') if rootPart else None

    if not bootMount:
        print("ERROR: Boot partition must have a mountpoint.")
        return
    if not disk or not isValidDiskPath(disk):
        print(f"ERROR: Disk path '{disk}' is invalid.")
        return
    if not rootName or not isValidLabel(rootName):
        print(f"ERROR: Root partition name '{rootName}' is invalid.")
        return

    if not bootloader:
        print("No bootloader set. Defaulting to grub.")
        bootloader = "grub"

    match bootloader:
        case "grub":
            if firmware == "BIOS":
                grubCommand = ['grub-install', '--target=i386-pc', '--bootloader-id', rootName, disk]
                add_op(
                    state,
                    server.shell,
                    name="Installing grub in BIOS",
                    commands=[grubCommand],
                    _sudo=True
                )
            elif firmware == "UEFI":
                grubCfgPath = f"{bootMount}/grub/grub.cfg"
                grubCommand = f"test -f {grubCfgPath} || grub-install --target=x86_64-efi --efi-directory={bootMount} --bootloader-id={rootName}"
                add_op(
                    state,
                    server.shell,
                    name="Installing grub in UEFI",
                    commands=[grubCommand],
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
            hostname = chObolo.get('hostname', 'charonte')
            if not isValidLabel(hostname):
                print(f"ERROR: Hostname '{hostname}' contains invalid characters.")
                return

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
                refindCfgPath = f"{bootMount}/efi/refind/refind.conf"
                refindCommand = f"test -f {refindCfgPath} || refind-install"
                add_op(
                    state,
                    server.shell,
                    name="Installing rEFInd in UEFI",
                    commands=[refindCommand],
                    _sudo=True
                )
                add_op(
                    state,
                    files.block,
                    name=f"Ensure rEFInd menuentry for {hostname}",
                    path=refindCfgPath,
                    content=desiredRefindConf,
                    marker=f"# {{mark}} CH-ARONTE MANAGED BLOCK FOR {hostname}",
                    _sudo=True
                )
            else:
                print("Unsupported boot mode for rEFInd.")
        case _:
            print("No supported bootloader specified.")

def runBootloader(state, host, choboloPath, skip):
    chObolo = OmegaConf.load(choboloPath)
    firmware = checkBootMode(host)
    installBootloaderSecure(state, chObolo, firmware)
