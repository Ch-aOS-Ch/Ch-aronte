class UsersExplain():
    def explain_users(self, detail_level='basic'):
        return {
            'concept': 'User Management',
            'what': 'Manages the lifecycle of user accounts on the system, including their properties (like shell), groups, and privileges. Basically, it defines "who can access the system and how."',
            'why': 'To ensure the separation of privileges and environments (each with their own home directory), follow the principle of least privilege, and improve security and traceability, as using the root account for daily tasks is strongly discouraged.',
            'how': 'Compares the desired state of users (defined in the configuration) with the current state on the system and applies the differences. To list existing users, it filters out non-system users with the command: `awk -F: "($3>=1000 && $7 ~ /(bash|zsh|fish|sh)$/){print $1}" /etc/passwd`.',
            'commands': ['useradd', 'usermod', 'userdel', 'groupadd', 'chpasswd'],
            'files': ['/etc/passwd', '/etc/shadow', '/etc/group', '/etc/sudoers.d/', '/etc/skel'],
            'examples': [
                {
                    'yaml': """users:
  - name: "dex"
    shell: "zsh"
    sudo: True
    groups:
      - wheel
      - docker""",
                }
            ],
            'equivalent': [ """# Adds the user 'dex', creates their /home and sets the shell
useradd -m -s /bin/zsh dex

# Sets the password
# (Ch-aOS uses a pre-hashed password for security)
echo 'dex:securepassword' | chpasswd

# Adds the 'docker' group if it doesn't exist
groupadd docker

# Adds the user to the 'wheel' and 'docker' groups
usermod -aG wheel,docker dex

# Grants sudo permissions via a managed file
echo 'dex ALL=(ALL:ALL) ALL' > /etc/sudoers.d/99-charonte-dex

# Removal is also automated:
# userdel -r dex
""", ],
            'learn_more': ['man useradd', 'man userdel', 'man passwd', 'man sudoers', 'man groupadd']
        }

    def explain_sudo(self, detail_level='basic'):
        return {
            'concept': 'Sudo Access',
            'what': 'Grants administrative (root) privileges to a specific user via sudo, allowing the execution of commands as the superuser.',
            'why': 'To allow non-root users to perform administrative tasks in a secure and auditable way, without needing to share the root password.',
            'how': 'It creates a user-specific configuration file inside `/etc/sudoers.d/`. This approach is safer and more modular than editing the main `/etc/sudoers` file, as it allows permissions to be granted and revoked atomically and without the risk of corrupting the main file.',
            'technical': 'Creates the file `/etc/sudoers.d/99-charonte-<username>`, ensuring the rule is loaded last and can be managed individually. After creating the file, it is validated with `visudo -c` to ensure the syntax is correct before being applied.',
            'security': 'ATTENTION: Granting sudo access allows a user to execute commands with root privileges. Use with caution and only for trusted users.',
            'equivalent': "echo 'dex ALL=(ALL:ALL) ALL' > /etc/sudoers.d/99-charonte-dex",
            'validation': 'visudo -c -f /etc/sudoers.d/99-charonte-dex'
        }

    def explain_root(self, detail_level='basic'):
        return {
            'concept': 'The Root User',
            'what': 'The `root` user is the superuser, an account with unrestricted privileges to perform any action on the system.',
            'why': 'It is necessary for initial system setup and for certain administrative tasks that cannot be delegated. However, for security, its direct use should be minimized.',
            'how': 'Ch-aOS avoids direct modification of the `root` account. The philosophy is to manage standard user accounts and grant them elevated privileges via `sudo` as needed. This is a security best practice.',
            'security': 'ATTENTION: Operating as `root` is dangerous. A single mistake can render the system unusable. Always prefer using a standard user with `sudo` privileges for administrative tasks.',
            'learn_more': ['man sudo', 'man sudoers']
        }

    def explain_group(self, detail_level='basic'):
        return {
            'concept': 'User Groups',
            'what': 'The `groups` key assigns a user to a list of supplementary groups. Groups are a standard Unix mechanism for managing collective permissions.',
            'why': 'To grant a set of users specific permissions simultaneously. For example, adding a user to the `docker` group grants them permission to interact with the Docker daemon, while the `wheel` group is often used to grant `sudo` access.',
            'how': 'For each group in the list, Ch-aOS ensures the group exists (running `groupadd` if needed) and then adds the user to that group.',
            'technical': 'The `usermod -aG <groups> <user>` command is used to append the user to supplementary groups, modifying the `/etc/group` file.',
            'equivalent': 'groupadd docker\nusermod -aG wheel,docker dex',
            'learn_more': ['man groups', 'man usermod', 'man groupadd']
        }

    def explain_shell(self, detail_level='basic'):
        return {
            'concept': 'Login Shell',
            'what': "The `shell` key defines the user's default command-line interpreter, which is started upon a successful login.",
            'why': 'To provide a personalized and productive command-line environment. Users may prefer shells like `zsh` or `fish` over the default `bash` for their advanced features like better autocompletion and plugin support.',
            'how': 'Ch-aOS sets the login shell when creating a user or modifies it for an existing user.',
            'technical': "This action modifies the final field of the user's entry in the `/etc/passwd` file. The specified shell must be listed in `/etc/shells` to be considered a valid login shell.",
            'equivalent': 'usermod -s /bin/zsh dex',
            'learn_more': ['man chsh', 'man shells', 'man usermod']
        }
