class ServicesExplain():
    _order=['dense', 'blacklist']
    def explain_services(self, detail_level='basic'):
        return {
            'concept': 'Systemd Services',
            'what': 'A service is a program managed by the `systemd` init system that runs in the background. It can be started at boot time or on demand. Common examples include network managers, database engines, and web servers.',
            'why': 'To manage long-running applications, ensuring they start automatically when the system boots and are restarted if they fail. `systemd` provides a robust framework for process supervision, dependency management, and logging.',
            'how': 'The `services` role ensures that the list of services in your configuration is active and enabled. It compares your desired state with the services currently enabled on the system and then enables/disables or starts/stops services as needed to reconcile any differences.',
            'commands': ['systemctl start', 'systemctl stop', 'systemctl enable', 'systemctl disable', 'systemctl status'],
            'files': ['/etc/systemd/system/', '/usr/lib/systemd/system/'],
            'examples': [
                {
                    'yaml': """services:
  - name: "bluetooth.service"
    on_boot: True
    running: True
  - name: "docker.service"
  # defaults to on_boot: True and running: True
""",
                }
            ],
            'equivalent': """# To enable and start a service now:
systemctl enable --now bluetooth.service

# To stop and disable a service:
systemctl disable --now graphical.target
""",
            'learn_more': ['man systemd.service', 'man systemctl', 'Arch Wiki: systemd']
        }

    def explain_blacklist(self, detail_level='basic'):
        """Explains the service blacklist feature"""
        return {
            'concept': 'Service Blacklist',
            'what': 'A built-in, hardcoded list of critical system services that this role is forbidden from ever disabling.',
            'why': 'This is a core safety feature. It prevents you from accidentally disabling a service essential for the system to boot or function, such as `dbus.service`, `polkit.service`, or `systemd-logind.service`.',
            'how': 'Normally, if a service is enabled on your system but not declared in your configuration, this role would try to disable it. However, if that service is found in the blacklist, the role will deliberately ignore it, leaving it untouched to prevent system instability.',
            'technical': 'This list is not configurable and is part of the role\'s core logic to ensure a baseline of system stability, protecting users from common mistakes.',
        }

    def explain_dense(self, detail_level='basic'):
        """Explains the dense_service field"""
        return {
            'concept': 'Dense Service Matching',
            'what': 'A "dense service" is a special declaration that uses a name as a prefix to match and manage multiple related services at once.',
            'why': 'It simplifies configuration when you need to manage a group of services that share a common naming convention, like those for virtualization (`libvirt*`) or other complex software suites, without listing every single service unit.',
            'how': 'When you set `dense_service: True` on a service entry named `virt`, this role will find and manage all installed services that start with that prefix, such as `virt-manager.service`, `virtlogd.service`, and `virtqemud.service`. The same state (`running`, `on_boot`) will be applied to all matched services.',
            'security': 'Use this feature with care, as it can affect many services simultaneously. Ensure your prefix is specific enough to not accidentally match unintended services.',
            'examples': [
                {
                    'yaml': """# This will find and enable all services starting with 'libvirt'
services:
  - name: "libvirt"
    dense_service: True
""",
                }
            ]
        }
