class RegionExplain():
    def explain_region(self, detail_level='basic'):
        return {
            'concept': 'System Region and Localization',
            'what': 'Localization is the process of adapting software to a specific region or language. This role configures the system`s locale (language, character sets), keyboard layout, and time settings.',
            'why': 'To ensure the system is usable and intuitive for you. This means displaying text in your language, using a keyboard layout that matches your hardware, and showing the correct local time.',
            'how': 'The role reads the `region` block from your configuration and applies the settings using standard Linux utilities like `timedatectl` and by managing configuration files like `/etc/locale.gen` and `/etc/vconsole.conf`.',
            'files': ['/etc/locale.gen', '/etc/locale.conf', '/etc/vconsole.conf', '/etc/localtime'],
            'commands': ['timedatectl', 'locale-gen'],
            'examples': [
                {
                    'yaml': """region:
  locale:
    - "en_US.UTF-8"
    - "pt_BR.UTF-8"
  keymap: "us"
  timezone: "America/Sao_Paulo"
  ntp: True
""",
                }
            ],
            'learn_more': ['Arch Wiki: Localization']
        }

    def explain_locale(self, detail_level='basic'):
        """Explains the locale field"""
        return {
            'concept': 'System Locale',
            'what': 'A "locale" is a set of parameters that defines the user`s language, country, and any special variant preferences. It affects language, number formatting, date and time formatting, and currency symbols.',
            'why': 'To have the system interface and applications display text and formats that you can understand and are familiar with.',
            'how': 'The `locale` key accepts a list of locales to make available on the system. The role uncomments them in `/etc/locale.gen` and runs `locale-gen`. The *first* locale in your list is then set as the system-wide default language in `/etc/locale.conf`.',
            'equivalent': """# Generate the locale
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen

# Set it as the default
echo "LANG=en_US.UTF-8" > /etc/locale.conf""",
            'learn_more': ['man locale', 'Arch Wiki: Locale']
        }

    def explain_keymap(self, detail_level='basic'):
        """Explains the keymap field"""
        return {
            'concept': 'Virtual Console Keymap',
            'what': 'The "keymap" defines the keyboard layout used in the virtual console (the text-based interface outside of a graphical environment).',
            'why': 'To ensure that the keys you press on your physical keyboard correspond to the correct characters on the screen in the TTY.',
            'how': 'The `keymap` key specifies which keyboard layout to use. The role writes this setting to `/etc/vconsole.conf` to make it persistent across reboots.',
            'technical': 'This setting does not affect your keyboard layout within a graphical desktop environment (like GNOME or KDE), which has its own independent keyboard settings.',
            'equivalent': 'echo "KEYMAP=us" > /etc/vconsole.conf',
            'learn_more': ['man vconsole.conf', 'man loadkeys']
        }

    def explain_timezone(self, detail_level='basic'):
        """Explains the timezone field"""
        return {
            'concept': 'System Timezone',
            'what': 'A timezone is a region of the globe that observes a uniform standard time for legal, commercial, and social purposes.',
            'why': 'Setting the correct timezone is critical for the system clock to display the correct local time, which affects everything from file timestamps and logs to calendar events.',
            'how': 'The `timezone` key takes a `Region/City` string. The role uses the `timedatectl set-timezone` command to apply this setting system-wide.',
            'equivalent': 'timedatectl set-timezone America/Sao_Paulo',
            'learn_more': ['man timedatectl', 'timedatectl list-timezones']
        }

    def explain_ntp(self, detail_level='basic'):
        """Explains the ntp field"""
        return {
            'concept': 'Network Time Protocol (NTP)',
            'what': 'NTP is a networking protocol for clock synchronization between computer systems over packet-switched, variable-latency data networks.',
            'why': 'To automatically keep the system clock accurate by synchronizing it with internet time servers. This corrects any "drift" in the hardware clock and is the modern, recommended way to manage time.',
            'how': "The `ntp` key is a boolean (`True` or `False`) that simply enables or disables the system's NTP client using the `timedatectl set-ntp` command.",
            'equivalent': 'timedatectl set-ntp true',
            'learn_more': ['man systemd-timesyncd.service', 'Arch Wiki: systemd-timesyncd']
        }
