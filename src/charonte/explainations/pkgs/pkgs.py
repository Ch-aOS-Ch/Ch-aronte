class PkgsExplain():
    def explain_pkgs(self, detail_level='basic'):
        return {
            'concept': 'System Package Management',
            'what': 'A package is a bundle of files, information, and instructions that constitutes a piece of software. A package manager is a tool that automates the process of installing, updating, configuring, and removing these software packages in a consistent manner.',
            'why': 'Using a package manager prevents "dependency hell" by automatically handling software dependencies. It keeps software organized, allows for easy updates, and ensures that packages can be removed cleanly, which is crucial for system stability.',
            'how': 'The `packages` role in Ch-aOS manages packages from both the official repositories (using `pacman`) and the AUR. By defining lists like `packages` and `aurPackages` in your configuration, you create a single source of truth, and this role ensures your system matches it.',
            'commands': ['pacman', 'yay', 'paru'],
            'examples': [
                {
                    'yaml': """# Defines packages from official repositories
packages:
  - firefox
  - docker

# Defines the helper to be used for AUR packages
aurHelpers:
  - yay

# Defines packages from the Arch User Repository
aurPackages:
  - visual-studio-code-bin""",
                }
            ],
            'equivalent': """# Install native packages
pacman -S --noconfirm --needed firefox docker
# Install AUR packages using a helper
yay -S --noconfirm visual-studio-code-bin""",
            'learn_more': ['man pacman', 'Arch Wiki: pacman']
        }

    def explain_aur(self, detail_level='basic'):
        """Explains the aurPackages field"""
        return {
            'concept': 'The Arch User Repository (AUR)',
            'what': 'The AUR is a community-driven repository for Arch users. It contains package descriptions, called `PKGBUILD`s, that allow you to compile a package from source and install it with `pacman`. It is one of the defining features of Arch Linux.',
            'why': 'It provides access to a vast, community-curated library of software that has not yet been accepted into the official repositories. If a piece of software exists for Linux, it is likely in the AUR.',
            'how': 'The `aurPackages` key in your configuration lists all the AUR packages you want on your system. Ch-aOS uses a configured AUR helper to automatically download, build, and install them for you.',
            'security': 'CRITICAL: AUR packages are user-produced content. While the AUR has a voting and flagging system, you should always inspect the `PKGBUILD` of any package you install, especially if it is complex or not well-known, to check for malicious or dangerous commands.',
            'equivalent': 'yay -S visual-studio-code-bin',
            'learn_more': ['Arch Wiki: Arch User Repository', 'man PKGBUILD']
        }

    def explain_helper(self, detail_level='basic'):
        """Explains the aurHelpers field"""
        return {
            'concept': 'AUR Helper',
            'what': 'An AUR helper is a command-line tool that automates the use of the Arch User Repository. They make searching, building, and installing AUR packages as seamless as using `pacman`.',
            'why': 'To simplify the process of installing and updating AUR packages. The manual process requires several steps (cloning a git repo, inspecting the PKGBUILD, running `makepkg`, and then `pacman -U`). A helper condenses this into a single command.',
            'how': 'The `aurHelpers` key tells Ch-aOS which helper (e.g., `yay` or `paru`) you want to use. The role will ensure this helper is installed and will then use it for all subsequent operations involving your `aurPackages` list.',
            'equivalent': """# To install yay, for example:
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si --noconfirm""",
            'learn_more': ['Arch Wiki: AUR helpers']
        }
