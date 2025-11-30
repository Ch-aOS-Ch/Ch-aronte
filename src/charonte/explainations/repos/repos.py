class ReposExplain():
    _order=['managed', 'TPRepos', 'override']
    def explain_repos(self, detail_level='basic'):
        return {
            'concept': 'Pacman Repositories Management',
            'what': 'Manages the entire `/etc/pacman.conf` file, which defines the package repositories `pacman` will use for installing and updating packages.',
            'why': 'To declaratively control your package sources. This allows you to enable/disable official Arch repositories (like `testing` or `multilib`) and securely add trusted third-party repositories.',
            'how': 'The role generates the complete content of `/etc/pacman.conf` based on the `repos` block in your configuration. To avoid unnecessary changes, it calculates a SHA1 hash of the desired content and compares it to the hash of the current file on the system. The file is only replaced if the hashes differ.',
            'files': ['/etc/pacman.conf', '/etc/pacman.d/mirrorlist'],
            'examples': [
                {
                    'yaml': """repos:
  managed:
    extras: True
    multilib: True
    unstable: False
  third_party:
    - name: "cachyos"
      include: "/etc/pacman.d/cachyos-mirrorlist"
""",
                }
            ],
            'equivalent': """# This role generates the entire pacman.conf file.
# The equivalent shell command is to write the file from scratch:
cat <<EOF > /etc/pacman.conf
# Options block
[options]
HoldPkg     = pacman glibc
Architecture = auto
Color
ILoveCandy
CheckSpace
ParallelDownloads = 5
SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional

# Third-party repo
[cachyos]
Include = /etc/pacman.d/cachyos-mirrorlist

# Official repos
[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist

[multilib]
Include = /etc/pacman.d/mirrorlist
EOF
""",
            'learn_more': ['man pacman.conf']
        }

    def explain_TPRepos(self, detail_level='basic'):
        return {
            'concept': 'Third-Party Repositories',
            'what': 'The `third_party` key is a list that allows you to add custom, non-official pacman repositories to your system.',
            'why': 'To access packages not available in the official Arch repositories. This is common for custom Linux kernels, specialized tools, or community-maintained package collections.',
            'technical': 'For each item in the list, a new repository entry (e.g., `[cachyos]`) is added to `/etc/pacman.conf`, using the `Server` or `Include` directive as specified.',
            'security': 'ATTENTION: Only add repositories from sources you absolutely trust. Packages from third-party repositories can potentially compromise your system`s security and stability.',
            'equivalent': 'echo -e "[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist" >> /etc/pacman.conf',
            'learn_more': ['man pacman.conf']
        }

    def explain_managed(self, detail_level='basic'):
        return {
            'concept': 'Managed Official Repositories',
            'what': 'The `managed` key is a block of booleans that controls which official Arch Linux repositories (`core`, `extra`, `multilib`, and their `testing` counterparts) are enabled.',
            'why': 'It provides an easy and readable way to enable repositories like `multilib` (for 32-bit application support) or to switch to the `testing` repositories to get newer package versions.',
            'how': 'Based on the boolean flags (`True`/`False`), the role will either include or omit the corresponding repository blocks from the final `/etc/pacman.conf` file.',
            'examples': [
                {
                    'yaml': """# Enables extra and multilib, but keeps testing repos disabled.
managed:
  core: True # Core is always recommended, 
             # even when defaulted to True
  extras: True
  unstable: False
""",
                }
            ],
        }

    def explain_override(self, detail_level='basic'):
        return {
            'concept': 'Options Block Override',
            'what': 'The `i_know_exactly_what_im_doing` key, when set to a string, replaces the default, safe `[options]` block in `pacman.conf` with the provided custom string.',
            'why': "For advanced users who need to fine-tune pacman's behavior, for example, by changing signature verification levels (`SigLevel`), holding back packages from updates (`HoldPkg`), or altering other core settings.",
            'how': 'If this key is present, the role uses its string content for the `[options]` block. If it`s absent, a hardcoded safe default is used.',
            'security': "CRITICAL: This is a feature for experts. Misconfiguring the options block can severely compromise your system's security (e.g., by disabling signature checks) or break your package manager entirely. Use with extreme caution.",
            'examples': [
                {
                    'yaml': """repos:
  i_know_exactly_what_im_doing: |
    [options]
    HoldPkg = pacman glibc linux
    Architecture = auto
    Color
    CheckSpace
    SigLevel = Required DatabaseOptional
    LocalFileSigLevel = Optional
"""
                }
            ]
        }
