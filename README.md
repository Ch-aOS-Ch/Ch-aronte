[versão pt br](./READMEpt_BR.md)
# Ch-aronte

**An declarative Arch linux installer and manager**

[![Project Status: Active](https://img.shields.io/badge/status-active-success.svg)](https://github.com/Dexmachi/Ch-aronte)

---

> [!WARNING]
>
> This is the Legacy code, I am currently working on switching both the bash scripts with OmegaConf and ansible playbooks with pyinfra.

> [!NOTE]
>
> Findings:
>
> Pyinfra is about 3 times faster than ansible for the simple task of getting all pacman native and all pacman non native packages, putting them in a list and printing them.
>
> this, along with the fact that it will enable easier logic down the line shows that i really should just use pyinfra (even if it's install method is shitty on arch)
```bash
time ansible-playbook Ch-obolos/dex/playbook_test.yaml # <~ time got: 2,67s user 0,45s system 94% cpu 3,294 total

time uv run Ch-obolos/dex/example_pyinfra.py # time got: 0,95s user 0,13s system 92% cpu 1,175 total
```

***An guided arch-installer and declarative system manager***

***PART OF THE Ch-aOS (Ch-aronte + Ch-imera for nix + Ch-obolos [studying the ideas of an Ch-iron for fedora and an Ch-ronos for debian]) PROJECT SUITE***

## Key Features

- **An *guided* instalation process**: Instead of automating everything, the script displays a series of questions and explanations about what it's doing to the reader, they gather information about the _how_ the reader wants their system, it then writes an singular file in yaml –for easy readability– and uses _that_ file to install the system, it is not automated at all (Im working on an automated mode)
- **The plugin –or better yet, Ch-obolos– system**: Akin to nix, the Ch-aOS plugin system is fully declarative, written exclusively in yaml, it helps the user manage their whole entire system with one singular file by using ansible + the (WIP) Ch-imera project will be able to take these plugins and compile them into nixlang, allowing for an easy transition.

## The Architecture: Orchestrator + Worker

The project uses a hybrid architecture, delegating to different languages their do's and don't's:

* **Shell Script (The Orchestrator)**: Used to gather user input, transform the input into an declarative file and call in–
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
2. While you can put everything in one file, I recommend separating concerns into multiple files and using a main file to import them. This makes your configuration cleaner and more reusable.

For example, you could have the following structure in your `./Ch-obolos/` directory:
```
.
├── custom-main.yml
├── dotfiles.yml
├── packages.yml
├── partitions.yml
├── region.yml
├── repos/repos.yml
├── services.yml
└── users.yml
```

Your main file, `custom-main.yml`, would then use `imports` to combine the other files. The `strategy` key (`override`, `combine`, `merge`) determines how data is merged if keys conflict.
```YAML
# ./Ch-obolos/custom-main.yml
# This is the main entrypoint file for your plugin.
plug_name: custom-main.yml # <- essential, this identifies the plugin

imports:
  - file: 'users.yml'
    strategy: merge
    merge_keys:
      - users

  - file: 'packages.yml'
    strategy: override

  - file: 'services.yml'
    strategy: combine

  - file: 'repos/repos.yml' # note that repos/ should still be inside your Ch-obolos directory path.
    strategy: combine

  - file: 'dotfiles.yml'
    strategy: merge
    merge_keys:
      - dotfiles

  - file: 'partitions.yml'
    strategy: override

  - file: 'region.yml'
    strategy: override
```

And the corresponding files would contain the specific configurations, for example:
```YAML
# ./Ch-obolos/packages.yml
pacotes:
  - neovim
  - fish
  - starship

bootloader: "grub"
```

Or:
```YAML
# ./Ch-obolos/users.yml
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
wheel_access: true
secrets:
  sec_mode: "sops" # <~ charonte sec_mode is provably going to be deprecated, since sops does what the system needs with no drawbacks
  sec_file: "Ch-obolos/secrets.yml" #<- secrets file (passwords), must be secret and is REQUIRED for sec_mode "charonte"
                                    # btw, you can commit your secrets file if they are in sec_mode sops
  sec_sops: "Ch-obolos/secrets-sops.yml" # <~ fully integrated with sops, your secrets are safe as long as you have tour gpg key
                                         # this means that, if you use sec_mode sops, you need to backup
                                         # your .gnupg and copy it to the live boot manually, since these are fully secret.
```

### Example of a complete file with everything in one:
```YAML
# It's recommended to separate these configurations into different files
# (e.g., users.yml, packages.yml) and use a main plugin file to import them,
# but for this example, everything is in one place.

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

aur_pkgs: # <~ yeah, I sepparated them, this is a safety net for when you DON'T have an damn aur helper (how could you?)
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

  - name: bluetooth.service # <~ ".service" _is_ required when there's an .service in the service name (do NOT use dense for these types.)

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
      distribution: "arch" #<~ Allows for quick Ch-imera parsing, it tells it to not use it as an nix repo
      url: "https://mirror.cachyos.org/cachyos-repo.tar.xz"

# Manages dotfiles from git repositories
dotfiles: # Translatable with Ch-imera with the manager: tag, it will only use the nix manager tho
  - repo: https://github.com/your-user/your-dotfiles.git #<~ To decide how the script will behave, you have 3 options as to how it will work.
    install_command: "your_custom_dotfile_command.sh" # <~ It uses the root of your repo as a base point, so be aware of that.
    manager: "charonte" # <~ MUTUALLY EXCLUSIVE FROM INSTALL_COMMAND. Options are charonte OR stow (as of now), this allows for using an proper manager, I personally recommend that you use "charonte" since it is modular AND it is declarative.
    # btw, I'm actively using this dotfile manager rn, it is not dangerous.
    links: # <~ this is only available with the charonte manager.
      - from: "zsh" # <~ this is an _folder_ inside of my dotfiles folder
        to: . # <~ this is . by default, it takes the home of the first user on the list of users to define which home to go to
        open: true # <~ defines if the script should symlink the files _inside_ the folder _or_ the folder itself.
      - from: "bash"
        open: true
      - from: ".config"
# ATTENTION: _ALL_ THE FILES YOU PUT HERE _AND_ ALREADY EXIST ARE BACKED UP BESIDE THE NEW ONES. IF YOU _REMOVE_ A FILE FROM THE LIST, IT WILL BE REMOVED FROM THE PATH YOU SET AS WELL. (duh, it's declarative)

        # Your third option is leaving this blank, it will simply search for an install.sh inside your root folder, it'll do nothing if it doesn't find one.

# Defines disk partitions (usually filled by the interactive script)
firmware: UEFI
particoes: # <~ is not and never will be translatable to an configurations.nix :( but it is translatable to an disko.nix :)
  disk: "/dev/sdb" # <~ what disk you want to partition into
  partitions:
    - name: chronos # <~ Ch-aronte uses label for fstab andother things, this changes nothing to your overall experience, but it is an commodity for me
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

### To generate your current system's plugin, run:
```bash
cd Ch-aronte
DIR="./Ch-obolos/" && FILENAME="custom-meu-sistema-atual.yml" && mkdir -p "$DIR" && echo "pacotes:" > "$DIR/$FILENAME" && pacman -Qqen | sed 's/^/  - /' >> "$DIR/$FILENAME" && echo "Plugin gerado com sucesso em '$DIR/$FILENAME'!"
```

## Project Roadmap

- [-] = In Progress, probably in another branch, either being worked on or already implemented, but not fully tested.

### MVP
- [x] Minimal Installer with Firmware Detection
- [x] Plugin System for Custom Packages

### Modularity + Automation
- [x] Dotfile Manager integrated with the Plugin System
- [x] Import system (hell)
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
