#!/usr/bin/env python3
import logging
import argparse
import getpass
import os
import sys

from omegaconf import OmegaConf

from pyinfra.api.inventory import Inventory
from pyinfra.api.config import Config
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.state import StateStage, State
from pyinfra.api.operations import run_ops
from pyinfra.context import ctx_state

from charonte.roles.pkgs.tasks import pkgs as pkgs_role
from charonte.roles.users.tasks import users as users_role
from charonte.roles.repos.tasks import repos as repos_role
from charonte.roles.bootloader.tasks import bootloader as boot_role

ROLE_ALIASES = {
  "pkgs": "packages",
  "usr": "users",
  "repos": "repositories",
  "boot": "bootloader",
}

ROLES_DISPATCHER = {
  "packages": pkgs_role.run_all_pkg_logic,
  "users": users_role.run_user_logic,
  "repositories": repos_role.run_repo_logic,
  "bootloader": boot_role.run_bootloader,
}

CONFIG_DIR = os.path.expanduser("~/.config/charonte")
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.yml")

def main():
  parser = argparse.ArgumentParser(description="Ch-aronte orquestrator.")
  parser.add_argument('tags', nargs='*', help=f"The tag(s) for the role(s) to be executed(usable: users, packages, repositories).\nAvailable aliases: usr, pkgs, repos")
  parser.add_argument('-e', dest='chobolo', help="Path to Ch-obolo to be used (overrides config file).")
  parser.add_argument('-ikwid', '-y', '--i-know-what-im-doing', action='store_true', help="I Know What I'm Doing mode, basically skips confirmations, only leaving sudo calls")
  parser.add_argument('--dry', '-d', action='store_true', help="Execute in dry mode.")
  parser.add_argument('-v', action='count', default=0, help="Increase verbosity level. -v for WARNING, -vvv for DEBUG.")
  parser.add_argument('--verbose', type=int, choices=[1, 2, 3], help="Set log level directly. 1=WARNING, 2=INFO, 3=DEBUG.")
  parser.add_argument(
    '--secrets-file',
    '-sf',
    dest='secrets_file_override',
    help="Path to the sops-encrypted secrets file (overrides secrets.sec_file value in ch-obolo)."
  )
  parser.add_argument(
    '--sops-file',
    '-ss',
    dest='sops_file_override',
    help="Path to the .sops.yaml config file (overrides secrets.sec_sops value in ch-obolo)."
  )
  parser.add_argument(
    '--set-chobolo', '-chobolo',
    dest='set_chobolo_file',
    help="Set and save the default Ch-obolo file path."
  )
  parser.add_argument(
    '--set-sec-file', '-sec',
    dest='set_secrets_file',
    help="Set and save the default secrets file path."
  )
  parser.add_argument(
    '--set-sops-file', '-sops',
    dest='set_sops_file',
    help="Set and save the default sops config file path."
  )
  args = parser.parse_args()
 
  is_setter_mode = any([args.set_chobolo_file, args.set_secrets_file, args.set_sops_file])

  if is_setter_mode:
    print(f"Saving configuration to {CONFIG_FILE_PATH}...")

    os.makedirs(CONFIG_DIR, exist_ok=True)

    if os.path.exists(CONFIG_FILE_PATH):
      global_config = OmegaConf.load(CONFIG_FILE_PATH)
    else:
      global_config = OmegaConf.create()

    if args.set_chobolo_file:
      global_config.chobolo_file = args.set_chobolo_file
      print(f"- Default Ch-obolo set to: {args.set_chobolo_file}")
    if args.set_secrets_file:
      global_config.secrets_file = args.set_secrets_file
      print(f"- Default secrets file set to: {args.set_secrets_file}")
    if args.set_sops_file:
      global_config.sops_config = args.set_sops_file
      print(f"- Default sops config set to: {args.set_sops_file}")

    OmegaConf.save(global_config, CONFIG_FILE_PATH)
    print("Configuration saved.")
    sys.exit(0)

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

  ikwid = args.i_know_what_im_doing
  dry = args.dry

  if not args.tags:
     print('No tags passed.')
     sys.exit(0)

  global_config = {}
  if os.path.exists(CONFIG_FILE_PATH):
    global_config = OmegaConf.load(CONFIG_FILE_PATH) or OmegaConf.create()

  chobolo_path = args.chobolo or global_config.get('chobolo_file')
  secrets_file_override = args.secrets_file_override or global_config.get('secrets_file')
  sops_file_override = args.sops_file_override or global_config.get('sops_config')

  if not chobolo_path:
    print("ERROR: No Ch-obolo passed", file=sys.stderr)
    print("   Use '-e /path/to/file.yml' or configure a base Ch-obolo with 'B-coin --set-chobolo /path/to/file.yml'.", file=sys.stderr)
    sys.exit(1)

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

  # ----- args -----
  commonArgs = (state, host, chobolo_path, skip)
  secArgs = (
    state,
    host,
    chobolo_path,
    skip,
    secrets_file_override,
    sops_file_override
  )
  SEC_HAVING_ROLES={'users','secrets'}
  # --- Role orchestration ---
  for tag in args.tags:
    normalized_tag = ROLE_ALIASES.get(tag,tag)
    if normalized_tag in ROLES_DISPATCHER:
      print(f"\n--- Executing {normalized_tag} role with Ch-obolo: {chobolo_path} ---\n")
      if normalized_tag in SEC_HAVING_ROLES:
        ROLES_DISPATCHER[normalized_tag](*secArgs)
      else:
        ROLES_DISPATCHER[normalized_tag](*commonArgs)
      print(f"\n--- '{normalized_tag}' role finalized. ---")
    else:
      print(f"\nWARNING: Unknown tag '{normalized_tag}'. Skipping.")

  if not dry:
    run_ops(state)
  else:
    print(f"dry mode active, skipping.")
  # --- Disconnection ---
  print("\nDisconnecting...")
  disconnect_all(state)
  print("Finalized.")

if __name__ == "__main__":
  main()
