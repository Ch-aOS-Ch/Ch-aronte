#!/usr/bin/env python3
from omegaconf import OmegaConf
from pyinfra.api import State, Config, Inventory, connect, FactBase
from pyinfra.facts.server import Command
from pyinfra.connectors.local import LocalConnector

# ------------------- NECESSARY FOR PYINFRA -----------------------
inventory = Inventory(names_data=(["@local"], {}),)
config = Config()
config.connectors = {"@local": (LocalConnector, {})}
state = State(inventory,config)
connect.connect_all(state)
host = state.inventory.get_host("@local")
# ------------------- NECESSARY FOR PYINFRA -----------------------

# ------------------- GET VALUES -----------------------
ChObolo = OmegaConf.load("custom-plug-dex.yml")
basePkgs = list(ChObolo.pacotes
                + ChObolo.pacotes_base_override
                + [ChObolo.bootloader]
                + ChObolo.aur_helpers
                + [ChObolo.users[0].shell])

wntNotNatPkgs = ChObolo.aur_pkgs


native = host.get_fact(Command, "pacman -Qqen").strip().splitlines()
aur = host.get_fact(Command, "pacman -Qqem").strip().splitlines()

toRemoveNative = sorted(set(native) - set(basePkgs))
toRemoveAur = sorted(set(aur) - set(wntNotNatPkgs))

toAddNative = sorted(set(basePkgs) - set(native))
toAddAur = sorted(set(wntNotNatPkgs) - set(aur))

print("--- Pacotes nativos a remover ---")
for pkg in toRemoveNative:
    print(pkg)

print("\n--- Pacotes AUR a remover ---")
for pkg in toRemoveAur:
    print(pkg)

print("\n--- Pacotes nativos a adicionar ---")
for pkg in toAddNative:
    print(pkg)

print("\n--- Pacotes AUR a remover ---")
for pkg in toAddAur:
    print(pkg)

connect.disconnect_all(state)
