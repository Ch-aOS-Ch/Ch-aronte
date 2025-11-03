#!/usr/bin/env python3
import logging
import argparse
from pyinfra.api import State, Config, Inventory
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.state import StateStage
from pyinfra.context import ctx_state

from roles.pkgs.tasks import pkgs as pkgs_role

ROLE_ALIASES = {
    "pkgs": "packages",
    "usr": "users"
}

ROLES_DISPATCHER = {
    "packages": pkgs_role.run_all_pkg_logic,
}

def main():
    parser = argparse.ArgumentParser(description="Pyinfra Ch-aronte orquestrator.")
    parser.add_argument('tags', nargs='+', help="The tag(s) for the role(s) to be executed(ex: pkgs, users).")
    parser.add_argument('-e', '--chobolo', required=True, help="Path to Ch-obolo to be used.")
    args = parser.parse_args()
    chobolo_path = args.chobolo

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    hosts = ["@local"]
    inventory = Inventory((hosts, {}))
    config = Config()
    state = State(inventory, config)
    state.current_stage = StateStage.Prepare
    ctx_state.set(state)

    print("Connecting to localhost...")
    connect_all(state)
    host = state.inventory.get_host("@local")
    print("Connection established.")
    # -----------------------------------------

    # --- Role orchestration ---
    for tag in args.tags:
        normalized_tag = ROLE_ALIASES.get(tag,tag)
        if normalized_tag in ROLES_DISPATCHER:
                print(f"\n--- Executing {normalized_tag} role with Ch-obolo: {chobolo_path} ---")
                ROLES_DISPATCHER[normalized_tag](state, host, chobolo_path)
                print(f"--- '{normalized_tag}' role finalized. ---")
        else:
            logging.warning(f"Unknown tag '{normalized_tag}'. Skipping.")

    # --- Desconexão ---
    print("\nDisconnecting...")
    disconnect_all(state)
    print("Finalized.")

if __name__ == "__main__":
    main()
