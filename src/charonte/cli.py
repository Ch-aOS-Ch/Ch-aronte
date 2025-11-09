#!/usr/bin/env python3
import logging
import argparse
import getpass
from pyinfra.api.inventory import Inventory
from pyinfra.api.config import Config
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.state import StateStage, State
from pyinfra.context import ctx_state

from charonte.roles.pkgs.tasks import pkgs as pkgs_role

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
    parser.add_argument('-ikwid', '-y', '--i-know-what-im-doing', action='store_true', help="I Know What I'm Doing mode, basically skips confirmations, only leaving sudo calls")
    parser.add_argument('--dry', '-d', action='store_true', help="Execute in dry mode.")
    parser.add_argument('-v', action='count', default=0, help="Increase verbosity level. -v for WARNING, -vvv for DEBUG.")
    parser.add_argument('--verbose', type=int, choices=[1, 2, 3], help="Set log level directly. 1=WARNING, 2=INFO, 3=DEBUG.")
    args = parser.parse_args()

    log_level = None
    if args.verbose:
        if args.verbose == 1:
            log_level = logging.WARNING
        elif args.verbose == 2:
            log_level = logging.INFO
        elif args.verbose == 3:
            log_level = logging.DEBUG
    elif args.v == 1:
        log_level = logging.WARNING
    elif args.v == 2:
        log_level = logging.INFO
    elif args.v == 3:
        log_level = logging.DEBUG

    if log_level:
        logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    chobolo_path = args.chobolo
    ikwid = args.i_know_what_im_doing
    dry = args.dry
    drySkip = dry

    hosts = ["@local"]
    inventory = Inventory((hosts, {}))
    config = Config()
    state = State(inventory, config)
    state.current_stage = StateStage.Prepare
    ctx_state.set(state)

    config.SUDO_PASSWORD = getpass.getpass("Sudo password: ")

    skip = ikwid

    print("Connecting to localhost...")
    connect_all(state)
    host = state.inventory.get_host("@local")
    print("Connection established.")
    # -----------------------------------------

    # --- Role orchestration ---
    for tag in args.tags:
        normalized_tag = ROLE_ALIASES.get(tag,tag)
        if normalized_tag in ROLES_DISPATCHER:
                print(f"\n--- Executing {normalized_tag} role with Ch-obolo: {chobolo_path} ---\n")
                ROLES_DISPATCHER[normalized_tag](state, host, chobolo_path, skip, drySkip)
                print(f"\n--- '{normalized_tag}' role finalized. ---")
        else:
            print(f"\nWARNING: Unknown tag '{normalized_tag}'. Skipping.")

    # --- Desconexão ---
    print("\nDisconnecting...")
    disconnect_all(state)
    print("Finalized.")

if __name__ == "__main__":
    main()
