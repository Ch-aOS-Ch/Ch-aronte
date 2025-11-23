from omegaconf import OmegaConf
import subprocess
from io import StringIO
from pyinfra.api.operation import add_op
from pyinfra.operations import server, files, systemd
from pyinfra.facts.server import Command
from pyinfra.facts.files import File, FindFiles

SERVICES_BLACKLIST = {
    "dbus-broker.service",
    "dbus.service",
    "getty@.service",
    "kmod-static-nodes.service",
    "polkit.service",
    "systemd-binfmt.service",
    "systemd-boot-clear-sysfail.service",
    "systemd-boot-update.service",
    "systemd-confext.service",
    "systemd-fsck-root.service",
    "systemd-fsck@.service",
    "systemd-homed-activate.service",
    "systemd-homed.service",
    "systemd-journal-flush.service",
    "systemd-journald.service",
    "systemd-logind.service",
    "systemd-modules-load.service",
    "systemd-network-generator.service",
    "systemd-networkd-wait-online.service",
    "systemd-networkd.service",
    "systemd-pstore.service",
    "systemd-random-seed.service",
    "systemd-remount-fs.service",
    "systemd-resolved.service",
    "systemd-sysctl.service",
    "systemd-sysext.service",
    "systemd-timesyncd.service",
    "systemd-tmpfiles-setup-dev-early.service",
    "systemd-tmpfiles-setup-dev.service",
    "systemd-tmpfiles-setup.service",
    "systemd-tpm2-clear.service",
    "systemd-udev-load-credentials.service",
    "systemd-udev-trigger.service",
    "systemd-udevd.service",
    "systemd-update-utmp.service",
    "systemd-user-sessions.service",
    "systemd-userdb-load-credentials.service",
    "systemd-userdbd.service",
    "systemd-validatefs@.service",
    "systemd-vconsole-setup.service",
    "user-runtime-dir@.service",
    "user@.service",
}

def servicesDelta(host, ChObolo):
    servicesRawStr = host.get_fact(Command, "systemctl list-unit-files --type=service --no-pager --no-legend | awk '{print $1}'")
    all_services = set(servicesRawStr.strip().splitlines()) if servicesRawStr else set()

    enabledServicesRawStr = host.get_fact(Command, "systemctl list-unit-files --type=service --state=enabled | grep -Ev 'getty|timesyncd|UNIT|unit' | awk '{print $1}'")
    enabledServicesFull = set(enabledServicesRawStr.strip().splitlines()) if enabledServicesRawStr else set()
    enabledServices = {s for s in enabledServicesFull if "@." not in s and "initrd" not in s}

    declaredServices = ChObolo.get('services', [])

    expanded_desired_services = set()
    service_name_to_config = {}

    for serviceConfig in declaredServices:
        serviceName = serviceConfig.get('name')

        if serviceConfig.get('dense_service', False):
            for s in all_services:
                # Filter out template units and initrd services
                if "@." in s or "initrd" in s:
                    continue
                if s.startswith(serviceName):
                    expanded_desired_services.add(s)
                    service_name_to_config[s] = serviceConfig

        else:
            if not serviceName.endswith('.service'):
                serviceName = f"{serviceName}.service"
            expanded_desired_services.add(serviceName)
            service_name_to_config[serviceName] = serviceConfig

    toAdd_names = expanded_desired_services - enabledServices
    toRemove_names = (enabledServices - expanded_desired_services) - SERVICES_BLACKLIST

    return sorted(list(toAdd_names)), sorted(list(toRemove_names)), service_name_to_config

def servicesLogic(state, toAdd, toRemove, config_map):
    for service_name in toAdd:
        config = config_map[service_name]
        sState = config.get('running', True)
        enabled = config.get('on_boot', True)
        add_op(
            state,
            systemd.service,
            name=f"Ensure service {service_name} is running={sState} and enabled={enabled}",
            service=service_name,
            running=sState,
            enabled=enabled,
            _sudo=True
        )

    for service_name in toRemove:
        add_op(
            state,
            systemd.service,
            name=f"Ensure service {service_name} is stopped and disabled",
            service=service_name,
            running=False,
            enabled=False,
            _sudo=True
        )

def run_service_logic(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)
    toAdd, toRemove, config_map = servicesDelta(host, ChObolo)
    work_to_do = toAdd or toRemove

    if work_to_do:
        if toAdd:
            print(f"\n--- Services to converge (add/enable) ---")
            for s in toAdd:
                print(s)
        if toRemove:
            print(f"\n--- Services to stop/disable ---")
            for s in toRemove:
                print(s)

        if toAdd or toRemove:
            confirm = "y" if skip else input("\nIs This correct (Y/n)? ")
            if confirm.lower() in ["y", "yes", "", "s", "sim"]:
                servicesLogic(state, toAdd, toRemove, config_map)
        else:
            print("Nothing to be done.")
    else:
        print("\nAll services are in the desired state.")
