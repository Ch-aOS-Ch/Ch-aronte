[versão pt br](./READMEpt_BR.md)
# Ch-aronte

**A declarative Arch linux installer and manager**

[![Project Status: Active](https://img.shields.io/badge/status-active-success.svg)](https://github.com/Dexmachi/Ch-aronte)

---

> [!WARNING]
>
> This is the Legacy code, I am currently working on switching both the bash scripts with OmegaConf and ansible playbooks with pyinfra OR pulumi (considering both).

***A guided arch-installer and declarative system manager***

***PART OF THE Ch-aOS (Ch-aronte + Ch-imera for nix + Ch-obolos [studying the ideas of a Ch-iron for fedora and a Ch-ronos for debian]) PROJECT SUITE***

## Key Features

- **An *guided* instalation process**: Instead of automating everything, the script displays a series of questions and explanations about what it's doing to the reader, they gather information about the _how_ the reader wants their system, it then writes a singular file in yaml –for easy readability– and uses _that_ file to install the system, it is not automated at all (Im working on an automated mode)
- **The plugin –or better yet, Ch-obolos– system**: Akin to nix, the Ch-aOS plugin system is fully declarative, written exclusively in yaml, it helps the user manage their whole entire system with one singular file by using ansible + the (WIP) Ch-imera project will be able to take these plugins and compile them into nixlang, allowing for an easy transition.

## The Architecture: Orchestrator + Worker

The project uses a hybrid architecture, delegating to different languages their do's and don't's:

* **Shell Script (The Orchestrator)**: Used to gather user input, transform the input into a declarative file and call in–
* **Ansible (The Worker)**: Used to make sure the system state is the same as the one declared in the Ch-obolo file.

## Getting Started

Run directly from the Arch Linux Live ISO environment.

### Prerequisites:

* An internet connection (use `iwctl` in the live environment).
* A running Arch Linux Live ISO.

### Installation Steps:

```bash
# 1. In the live environment, connect to the internet
iwctl

# 2. (Optional, but recommended) Increase the RAM space for the liveboot
mount -o remount,size=2G /run/archiso/cowspace

# 3. Install the dependencies
pacman -Sy --noconfirm ansible git yq sops # this last one is only if you
                                           # want to encript and commit your passwords (recommended)

# 4. Clone the repository and start the installer
git clone [https://github.com/Dexmachi/Ch-aronte.git](https://github.com/Dexmachi/Ch-aronte.git)
cd Ch-aronte

# IMPORTANT: Run the script from inside the project folder
chmod +x A-coin.sh
./A-coin.sh
```
> [!WARNING]
>
> The script is your guide. Follow the instructions in the terminal and answer the questions, the system will install the system based on it

## Ch-obolos System

Customize your installation by creating your own presets.
1. Create a file named custom-YOUR-PLUGIN.yml inside ./Ch-obolos/.

### Example of a complete file with everything in one:
```YAML
# Defines system users, groups, and hostname
users:
  - name: "dexmachina"
    shell: "zsh"
    groups:
      - wheel
      - dexmachina
  - name: "root"
    shell: "bash"
    groups:
      - root
hostname: "Dionysus"
wheel_access: true # Grants sudo access to the 'wheel' group

secrets:
  sec_mode: sops
  sec_file: Ch-obolos/secrets-here.yml
  sec_sops: Ch-obolos/sops-secs.yml

# Defines the list of packages to be declaratively managed
pacotes:
  - neovim
  - fish
  - starship
  - btop

aur_pkgs: # <~ yeah, I sepparated them, this is a safety net for when you DON'T have a damn aur helper (how could you?)
  - 1password-cli
  - aurroamer # <~ Highly recommend, very good package
  - aurutils
  - bibata-cursor-theme-bin
 
bootloader: "grub" # or "refind"

# pacotes_base_override:  <~ very dangerous, it allows you to change the core base packages (e.g: linux linux-firmware ansible ~~cowsay~~ etc)
#   - linux-cachyos-headers
#   - linux-cachyos
#   - linux-firmware

aur_helpers: # <~ Only yay and paru are available right now, the script will _install_ any aur_helpers you want, but it'll only declaratively manage these 2
  - yay
  - paru

mirrors: # <~ this was made to translate to reflector, I'll probably be able to translate it with overlays, but it'll be very hard ://
  countries:
    - "br"
    - "us"
  count: 25

# Manages systemd services
services:
  - name: NetworkManager
    state: started # <~ You are able to not define this, since it defaults to started
    enabled: true # <~ You are able to not define this, since it defaults to enabled
                  # I like to keep these for granularity
    dense_service: true # <~ this tells the script to use regex to find all services with "NetworkManager" in it's name

  - name: bluetooth.service # <~ ".service" _is_ required when there's a .service in the service name (do NOT use dense for these types.)

  - name: sshd

  - name: nvidia
    dense_service: true

  - name: sddm.service

# Manages pacman repositories
repos:
  managed:
    extras: true      # Enables the [extras+multilib] repository
    unstable: false   # Disables the [testing] repositories
  third_party:
    - name: "cachyOS"
      distribution: "arch" #<~ Allows for quick Ch-imera parsing, it tells it to not use it as a nix repo
      url: "https://mirror.cachyos.org/cachyos-repo.tar.xz"

# Manages dotfiles from git repositories
dotfiles: # Translatable with Ch-imera with the manager: tag, it will only use the nix manager tho
  - repo: https://github.com/your-user/your-dotfiles.git #<~ To decide how the script will behave, you have 3 options as to how it will work.
    install_command: "your_custom_dotfile_command.sh" # <~ It uses the root of your repo as a base point, so be aware of that.
    manager: "charonte" # <~ MUTUALLY EXCLUSIVE FROM INSTALL_COMMAND. Options are charonte OR stow (as of now), this allows for using a proper manager, I personally recommend that you use "charonte" since it is modular AND it is declarative.
    # btw, I'm actively using this dotfile manager rn, it is not dangerous.
    links: # <~ this is only available with the charonte manager.
      - from: "zsh" # <~ this is a _folder_ inside of my dotfiles folder
        to: . # <~ this is . by default, it takes the home of the first user on the list of users to define which home to go to
        open: true # <~ defines if the script should symlink the files _inside_ the folder _or_ the folder itself.
      - from: "bash"
        open: true
      - from: ".config"
# ATTENTION: _ALL_ THE FILES YOU PUT HERE _AND_ ALREADY EXIST ARE BACKED UP BESIDE THE NEW ONES. IF YOU _REMOVE_ A FILE FROM THE LIST, IT WILL BE REMOVED FROM THE PATH YOU SET AS WELL. (duh, it's declarative)

        # Your third option is leaving this blank, it will simply search for an install.sh inside your root folder, it'll do nothing if it doesn't find one.

# Defines disk partitions (usually filled by the interactive script)
firmware: UEFI
particoes: # <~ is not and never will be translatable to a configurations.nix :( but it is translatable to a disko.nix :)
  disk: "/dev/sdb" # <~ what disk you want to partition into
  partitions:
    - name: chronos # <~ Ch-aronte uses label for fstab andother things, this changes nothing to your overall experience, but it is a commodity for me
      important: boot # <~ Only 4 of these, boot, root, swap and home, it uses this to define how the role should be treated (mainly boot and swap)
      size: 1GB # <~ Use G, MiB might work, but it might not, it's still not well stabilized
      mount_point: "/boot" # <~ required (duh)
      part: 1 # <~ this tells what partition it is (sdb1,2,3,4...)
      type: vfat # <~ or ext4, btrfs, well, you get the idea

    - name: Moira
      important: swap
      size: 4GB
      part: 2
      type: linux-swap

    - name: dionysus_root
      important: root
      size: 46GB
      mount_point: "/"
      part: 3
      type: ext4

    - name: dionysus_home
      important: home
      size: 100%
      mount_point: "/home"
      part: 4
      type: ext4

# Defines region, language, and keyboard settings
region:
  timezone: "America/Sao_Paulo"
  locale:
    - "pt_BR.UTF-8"
    - "en_US.UTF-8"
  keymap: "br-abnt2"

```
> [!WARNING]
>
> You can find a more complete example in [My-Ch-obolos](Ch-obolos/dex/custom-plug-dex.yml), these are the Ch-obolos I am actively using to manage my own system!

# Example of usage:
![B-coin usage](./imagens/B-coin-test.gif)
Note: This GIF shows the new B-coin executor (Pyinfra-based) that is currently under development and not yet fully in the main branch. The installation steps above are for the legacy Ansible version.

## Project Roadmap

- [-] = In Progress, probably in another branch, either being worked on or already implemented, but not fully tested.

### MVP
- [x] Minimal Installer with Firmware Detection
- [x] Plugin System for Custom Packages

### Modularity + Automation
- [x] Dotfile Manager integrated with the Plugin System
- [ ] B-coin system manager CLI helper.

### Declarativity
- [-] Fully declarative installation mode, with it's only necessity being the custom*.yml file. (I just need to implement the checker on the start of the script and if the plugin file exists and is selected, run in declarative mode)
- [-] Fully declarative post-install system configuration with only one custom*.yml file. (I just need to implement the B-coin helper for this one)
- [x] Declarative package state manager (Install and uninstall declaratively).
- [x] Repo manager.

### Quality + security
- [-] ansible-lint and ansible-test tests. (Currently being done manually)

### Ideas being studied
- [-] Secrets management (HIGHLY expansible, currently only used for user passwords).
  - Now that I finally integrated [sops](https://github.com/getsops/sops) to the system,
    I can easily do secrets management with encryption and safe commiting.
- [ ] ALA/ALHA (Arch Linux Archive/Arch Linux Historical Archive) Support, as a flakes.lock equivalent.

## Contributing

Contributions are higly welcomed. If you have ideas to improve Ch-aronte, your help is very welcome! Check out CONTRIBUTING.md to get started.

Areas of particular interest include:

- Creative translations and improvements to the narrative style.
- Suggestions and implementations for post-install configurations.
- Help to check if the Ch-obolos are truly declarative or not.
- Creation of issues.

## Acknowledgements

The primary inspiration for this project came from [archible](https://github.com/0xzer0x/archible) from [0xzer0x](https://github.com/0xzer0x).
> If you're reading this (I doubt it but oh well), thank you very much for your amazing tool, I hope to achieve this level of creativity and expertise you've got to make it come true.
