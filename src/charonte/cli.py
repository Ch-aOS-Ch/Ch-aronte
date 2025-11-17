#!/usr/bin/env python3
import logging
import argparse
import getpass
import os
import sys
import subprocess

from omegaconf import OmegaConf
from pathlib import Path

from pyinfra.api.inventory import Inventory
from pyinfra.api.config import Config
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.state import StateStage, State
from pyinfra.api.operations import run_ops
from pyinfra.context import ctx_state


try:
    from importlib.metadata import entry_points
except ImportError:
    from importlib_metadata import entry_points

def discoverAliases():
    discoveredAliases = {}
    eps = entry_points()
    if hasattr(eps, "select"):
        selected = eps.select(group="charonte.aliases")
    elif isinstance(eps, dict):
        selected = eps.get("charonte.aliases", [])
    else:
        selected = getattr(eps, "get", lambda *_: [])("charonte.aliases", [])
    for ep in selected:
        discoveredAliases[ep.name] = ep.value

    return discoveredAliases

def discoverRoles():
    discovered_roles = {}
    eps = entry_points()
    if hasattr(eps, "select"):
        selected = eps.select(group="charonte.roles")
    elif isinstance(eps, dict):
        selected = eps.get("charonte.roles", [])
    else:
        selected = getattr(eps, "get", lambda *_: [])("charonte.roles", [])
    for ep in selected:
        discovered_roles[ep.name] = ep.load()

    return discovered_roles

def argParsing():
    parser = argparse.ArgumentParser(description="Ch-aronte orquestrator.")
    parser.add_argument('tags', nargs='*', help=f"The tag(s) for the role(s) to be executed.")
    parser.add_argument('-e', dest="chobolo", help="Path to Ch-obolo to be used (overrides all calls).")
    parser.add_argument('-r', '--roles', action='store_true', help="Check which roles are available.")
    parser.add_argument('-a', '--aliases', action='store_true', help="Check which aliases are available.")
    parser.add_argument('-ikwid', '-y', '--i-know-what-im-doing', action='store_true', help="Skips all confirmations, only leaving sudo calls")
    parser.add_argument('--dry', '-d', action='store_true', help="Execute in dry mode.")
    parser.add_argument('-v', action='count', default=0, help="Increase verbosity level. (3 levels allowed)")
    parser.add_argument('--verbose', type=int, choices=[1, 2, 3], help="Set log level directly. 1=WARNING, 2=INFO, 3=DEBUG.")
    parser.add_argument(
    '--secrets-file',
    '-sf',
    dest='secrets_file_override',
    help="Path to the sops-encrypted secrets file (overrides all calls)."
    )
    parser.add_argument(
    '--sops-file',
    '-ss',
    dest='sops_file_override',
    help="Path to the .sops.yaml config file (overrides all calls)."
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
    parser.add_argument(
        '--check-sec', '-cs',
        action='store_true',
        help="Check the secrets encrypted file. Do not run publicly."
    )
    parser.add_argument(
        '--edit-sec', '-es',
        action='store_true',
        help="Edit the secrets encrypted file using sops. Do not run publicly."
    )
    parser.add_argument(
        '-ec', '--edit-chobolo',
        action='store_true',
        help="Edit the Ch-obolo file using the default editor."
    )
    args = parser.parse_args()
    return args

def checkRoles(ROLES_DISPATCHER):
    print("Discovered Roles:")
    if not ROLES_DISPATCHER:
        print("No roles found.")
    else:
        for p in ROLES_DISPATCHER:
            print(f"  -{p}")
    sys.exit(0)

def checkAliases(ROLE_ALIASES):
    print("Discovered Aliases for Roles:")
    if not ROLE_ALIASES:
        print("No aliases found.")
    else:
        for p, r in ROLE_ALIASES.items():
            print(f"\n  -{p} ~> -{r}")
            print("_____________________________________________")
    sys.exit(0)

def setMode(args):
    CONFIG_DIR = os.path.expanduser("~/.config/charonte")
    CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.yml")

    print(f"Saving configuration to {CONFIG_FILE_PATH}...")

    os.makedirs(CONFIG_DIR, exist_ok=True)

    if os.path.exists(CONFIG_FILE_PATH):
        global_config = OmegaConf.load(CONFIG_FILE_PATH)
    else:
        global_config = OmegaConf.create()

    if args.set_chobolo_file:
        inputPath = Path(args.set_chobolo_file)
        try:
            absolutePath = inputPath.resolve(strict=True)
            global_config.chobolo_file = str(absolutePath)
            print(f"- Default Ch-obolo set to: {args.set_chobolo_file}")
        except FileNotFoundError:
            print(f"ERRO: Arquivo não encontrado em: {inputPath}", file=sys.stderr)
            sys.exit(1)
    if args.set_secrets_file:
        inputPath = Path(args.set_secrets_file)
        try:
            absolutePath = inputPath.resolve(strict=True)
            global_config.secrets_file = str(absolutePath)
            print(f"- Default secrets file set to: {args.set_secrets_file}")
        except FileNotFoundError:
            print(f"ERRO: Arquivo não encontrado em: {inputPath}", file=sys.stderr)
            sys.exit(1)
    if args.set_sops_file:
        inputPath = Path(args.set_sops_file)
        try:
            absolutePath = inputPath.resolve(strict=True)
            global_config.sops_file = str(absolutePath)
            print(f"- Default sops file set to: {args.set_sops_file}")
        except FileNotFoundError:
            print(f"ERRO: Arquivo não encontrado em: {inputPath}", file=sys.stderr)
            sys.exit(1)

    OmegaConf.save(global_config, CONFIG_FILE_PATH)
    print("Configuration saved.")

def handleVerbose(args):
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

def handleOrchestration(args, dry, ikwid, ROLES_DISPATCHER, ROLE_ALIASES=None):
    CONFIG_DIR = os.path.expanduser("~/.config/charonte")
    CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.yml")
    global_config = {}
    if os.path.exists(CONFIG_FILE_PATH):
        global_config = OmegaConf.load(CONFIG_FILE_PATH) or OmegaConf.create()

    chobolo_path = args.chobolo or global_config.get('chobolo_file')
    secrets_file_override = args.secrets_file_override or global_config.get('secrets_file')
    sops_file_override = args.sops_file_override or global_config.get('sops_file')

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
    secArgs = commonArgs + (
        secrets_file_override,
        sops_file_override
    )

    SEC_HAVING_ROLES={'users','secrets'}
    # --- Role orchestration ---
    for tag in args.tags:
        normalized_tag = ROLE_ALIASES.get(tag,tag)
        if normalized_tag in ROLES_DISPATCHER:
            if normalized_tag in SEC_HAVING_ROLES:
                ROLES_DISPATCHER[normalized_tag](*secArgs)
            elif normalized_tag == 'packages':
                mode = ''
                if tag in ['allPkgs', 'packages', 'pkgs']:
                    mode = 'all'
                elif tag == 'natPkgs':
                    mode = 'native'
                elif tag == 'aurPkgs':
                    mode = 'aur'

                if mode:
                    pkgArgs = commonArgs + (mode,)
                    ROLES_DISPATCHER[normalized_tag](*pkgArgs)
                else:
                    print(f"\nWARNING: Could not determine a mode for tag '{tag}'. Skipping.")

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

def runSopsCheck(sops_file_override, secrets_file_override):
    secretsFile = secrets_file_override
    sopsFile = sops_file_override

    CONFIG_DIR = os.path.expanduser("~/.config/charonte")
    CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.yml")

    global_config = {} # Inicia vazio
    if os.path.exists(CONFIG_FILE_PATH):
        global_config = OmegaConf.load(CONFIG_FILE_PATH) or OmegaConf.create()

    if not secretsFile:
        secretsFile = global_config.get('secrets_file')
    if not sopsFile:
        sopsFile = global_config.get('sops_config')

    if not secretsFile or not sopsFile:
        ChOboloPath = global_config.get('chobolo_file', None)
        if ChOboloPath:
            try:
                ChObolo = OmegaConf.load(ChOboloPath)
                secrets_config = ChObolo.get('secrets', None)
                if secrets_config:
                    if not secretsFile:
                        secretsFile = secrets_config.get('sec_file')
                    if not sopsFile:
                        sopsFile = secrets_config.get('sec_sops')
            except Exception as e:
                print(f"WARNING: Could not load Chobolo fallback '{ChOboloPath}': {e}", file=sys.stderr)

    if not secretsFile or not sopsFile:
        print("ERROR: SOPS check requires both secrets file and sops config file paths.", file=sys.stderr)
        print("       Configure them using 'B-coin -sec' and 'B-coin -sops', or pass them with '-sf' and '-ss'.", file=sys.stderr)
        sys.exit(1)

    try:
        result = subprocess.run(['sops', '--config', sopsFile, '--decrypt', secretsFile], check=True)
        okCodes= [0,200]
        if result.returncode not in okCodes:
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    except subprocess.CalledProcessError as e:
        print("ERROR: SOPS decryption failed.")
        print("Details:", e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("ERROR: 'sops' command not found. Please ensure sops is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)

def runSopsEdit(sops_file_override, secrets_file_override):
    secretsFile = secrets_file_override
    sopsFile = sops_file_override

    CONFIG_DIR = os.path.expanduser("~/.config/charonte")
    CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.yml")

    global_config = {} # Inicia vazio
    if os.path.exists(CONFIG_FILE_PATH):
        global_config = OmegaConf.load(CONFIG_FILE_PATH) or OmegaConf.create()

    if not secretsFile:
        secretsFile = global_config.get('secrets_file')
    if not sopsFile:
        sopsFile = global_config.get('sops_config')

    if not secretsFile or not sopsFile:
        ChOboloPath = global_config.get('chobolo_file', None)
        if ChOboloPath:
            try:
                ChObolo = OmegaConf.load(ChOboloPath)
                secrets_config = ChObolo.get('secrets', None)
                if secrets_config:
                    if not secretsFile:
                        secretsFile = secrets_config.get('sec_file')
                    if not sopsFile:
                        sopsFile = secrets_config.get('sec_sops')
            except Exception as e:
                print(f"WARNING: Could not load Chobolo fallback '{ChOboloPath}': {e}", file=sys.stderr)

    if not secretsFile or not sopsFile:
        print("ERROR: SOPS check requires both secrets file and sops config file paths.", file=sys.stderr)
        print("       Configure them using 'B-coin -sec' and 'B-coin -sops', or pass them with '-sf' and '-ss'.", file=sys.stderr)
        sys.exit(1)

    try:
        result = subprocess.run(['sops', '--config', sopsFile, secretsFile], check=True)
        okCodes= [0,200]
        if result.returncode not in okCodes:
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    except subprocess.CalledProcessError as e:
        sys.exit(0)
    except FileNotFoundError:
        print("ERROR: 'sops' command not found. Please ensure sops is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)

def runChoboloEdit(chobolo_path):
    editor = os.getenv('EDITOR', 'nano')
    if not chobolo_path:
        CONFIG_DIR = os.path.expanduser("~/.config/charonte")
        CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.yml")
        cfg = OmegaConf.load(CONFIG_FILE_PATH)
        chobolo_path = cfg.get('chobolo_file', None)
    if chobolo_path:
        try:
            result = subprocess.run(
                [editor, chobolo_path],
            )
        except subprocess.CalledProcessError as e:
            print("ERROR: Ch-obolo editing failed.")
            print("Details: Editor exited with error code", e.returncode)
            sys.exit(1)
        except FileNotFoundError:
            print(f"ERROR: Editor '{editor}' not found. Please ensure it is installed and in your PATH.", file=sys.stderr)
            sys.exit(1)
    else:
        print("ERROR: No Ch-obolo file configured to edit.", file=sys.stderr)
        sys.exit(1)

def main():
    ROLES_DISPATCHER = discoverRoles()
    ROLE_ALIASES = discoverAliases()
    args = argParsing()
    ikwid = args.i_know_what_im_doing
    dry = args.dry

    if args.verbose or args.v>0:
        handleVerbose(args)

    if args.check_sec:
        runSopsCheck(args.sops_file_override, args.secrets_file_override)
        sys.exit(0)

    if args.edit_sec:
        runSopsEdit(args.sops_file_override, args.secrets_file_override)
        sys.exit(0)

    if args.edit_chobolo:
        runChoboloEdit(args.chobolo)
        sys.exit(0)

    if args.aliases:
        checkAliases(ROLE_ALIASES)

    if args.roles:
        checkRoles(ROLES_DISPATCHER)

    is_setter_mode = any([args.set_chobolo_file, args.set_secrets_file, args.set_sops_file])
    if is_setter_mode:
        setMode(args)
        sys.exit(0)

    if not args.tags:
        print('No tags passed.')
        sys.exit(0)
    else:
        handleOrchestration(args, dry, ikwid, ROLES_DISPATCHER, ROLE_ALIASES)

if __name__ == "__main__":
  main()
