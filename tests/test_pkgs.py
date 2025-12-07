import pytest
from omegaconf import OmegaConf
from charonte.roles.pkgs.tasks.pkgs import natPkgLogic, aurPkgLogic

def test_nat_pkg_logic():
    chobolo_str = """
packages:
  - firefox
  - docker
users:
  - name: "test"
    shell: "zsh"
bootloader: "grub"
"""
    chobolo = OmegaConf.create(chobolo_str)
    native_installed = ["nano", "git", "docker"]
    dependencies = ["some-dep"]
    
    to_add, to_remove = natPkgLogic(chobolo, [], native_installed, dependencies)
    
    assert "firefox" in to_add
    assert "zsh" in to_add
    assert "grub" in to_add
    assert "base" in to_add # from necessaries
    assert "docker" not in to_add # already installed
    
    chobolo_override = OmegaConf.create("""
baseOverride:
  - nano
    """)
    native_installed_2 = ["git", "nano"]
    
    to_add_2, to_remove_2 = natPkgLogic(chobolo_override, [], native_installed_2, [])
    assert "git" in to_remove_2
    assert "nano" not in to_remove_2


def test_aur_pkg_logic():
    chobolo_str = """
aurPackages:
  - visual-studio-code-bin
  - google-chrome
"""
    chobolo = OmegaConf.create(chobolo_str)
    aur_installed = ["google-chrome", "slack-desktop", "yay"]
    aur_dependencies = []
    native = []
    aur_helper = "yay"

    to_add, to_remove, helper = aurPkgLogic(chobolo, aur_helper, aur_installed, aur_dependencies, native)

    assert "visual-studio-code-bin" in to_add
    assert "google-chrome" not in to_add
    assert "slack-desktop" in to_remove
    assert helper == "yay"

def test_aur_pkg_logic_no_helper():
    chobolo_str = """
aurPackages:
  - visual-studio-code-bin
"""
    chobolo = OmegaConf.create(chobolo_str)
    # Helper não está instalado ainda
    to_add, to_remove, helper = aurPkgLogic(chobolo, None, [], [], ["yay"])
    assert helper is None

def test_aur_pkg_logic_no_packages_key():
    chobolo = OmegaConf.create({}) # a chave aurPackages está faltando
    to_add, to_remove, helper = aurPkgLogic(chobolo, "yay", ["some-package"], [], [])
    assert to_add == []
    assert to_remove == []
