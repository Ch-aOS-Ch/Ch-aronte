from typing import Any

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from pyinfra.api.operation import add_op
from pyinfra.facts.server import Command
from pyinfra.operations import systemd

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


class ServicesRole(Role):
    def __init__(self):
        super().__init__(
            name="Set Declared Services to be Enabled and Running",
            needs_secrets=False,
            necessary_chobolo_keys=["services"],
        )

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        try:
            services_raw_str = host.get_fact(
                Command,
                "systemctl list-unit-files --type=service --no-pager --no-legend | awk '{print $1}'",
            )
            all_services = (
                set(services_raw_str.strip().splitlines())
                if services_raw_str
                else set()
            )

        except Exception:
            all_services = set()

        try:
            enabled_services_raw_str = host.get_fact(
                Command,
                "systemctl list-unit-files --type=service --state=enabled | grep -Ev 'getty|timesyncd|UNIT|unit' | awk '{print $1}'",
            )
            enabled_services_full = (
                set(enabled_services_raw_str.strip().splitlines())
                if enabled_services_raw_str
                else set()
            )
        except Exception:
            enabled_services_full = set()

        enabled_services = {
            s for s in enabled_services_full if "@." not in s and "initrd" not in s
        }

        declared_services = chobolo.get("services", [])

        return {
            "all_services": list(all_services),
            "enabled_services": list(enabled_services),
            "declared_services": declared_services,
        }

    def delta(self, context: dict[str, Any] = {}) -> Delta:
        all_services = set(context.get("all_services", []))
        enabled_services = set(context.get("enabled_services", []))
        declared_services = context.get("declared_services", [])

        expanded_desired_services = set()
        service_name_to_config = {}

        for service_config in declared_services:
            service_name = service_config.get("name")
            if not service_name:
                continue

            if service_config.get("dense_service", False):
                for s in all_services:
                    # Filter out template units and initrd services
                    if "@." in s or "initrd" in s:
                        continue
                    if s.startswith(service_name):
                        expanded_desired_services.add(s)
                        service_name_to_config[s] = service_config

            else:
                if not service_name.endswith(".service"):
                    service_name = f"{service_name}.service"
                expanded_desired_services.add(service_name)
                service_name_to_config[service_name] = service_config

        to_add_names = expanded_desired_services - enabled_services
        to_remove_names = (
            enabled_services - expanded_desired_services
        ) - SERVICES_BLACKLIST

        to_add = sorted(list(to_add_names))
        to_remove = sorted(list(to_remove_names))

        delta_to_add = {}
        if to_add:
            delta_to_add["services"] = to_add

        delta_to_remove = {}
        if to_remove:
            delta_to_remove["services"] = to_remove

        return Delta(
            to_add=delta_to_add,
            to_remove=delta_to_remove,
            metadata={"config_map": service_name_to_config},
        )

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        to_add = delta.to_add.get("services", [])
        to_remove = delta.to_remove.get("services", [])
        config_map = delta.metadata.get("config_map", {})

        try:
            for service_name in to_add:
                config = config_map.get(service_name, {})
                s_state = config.get("running", True)
                enabled = config.get("on_boot", True)
                add_op(
                    state,
                    systemd.service,
                    name=f"Ensure service {service_name} is running={s_state} and enabled={enabled}",
                    service=service_name,
                    running=s_state,
                    enabled=enabled,
                    _sudo=True,
                )

            for service_name in to_remove:
                add_op(
                    state,
                    systemd.service,
                    name=f"Ensure service {service_name} is stopped and disabled",
                    service=service_name,
                    running=False,
                    enabled=False,
                    _sudo=True,
                )

            return ResultPayload(success=True, message=[], error=[], data={})
        except Exception as e:
            return ResultPayload(
                success=False,
                message=[],
                error=[f"Error planning services role: {str(e)}"],
                data={},
            )
