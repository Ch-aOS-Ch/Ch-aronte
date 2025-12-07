#!/usr/bin/env python3
from omegaconf import OmegaConf
import yaml
import subprocess
from passlib.hash import sha512_crypt

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import server, files
from pyinfra.facts.server import Command

def userDelta(host, ChObolo):
    """Get the users to remove"""
    # This gets all non system users
    if ChObolo.get('users') is None:
        return [], []
    users_raw_str = host.get_fact(Command, "awk -F: '($3>=1000 && $7 ~ /(bash|zsh|fish|sh)$/){print $1}' /etc/passwd")
    users_raw = users_raw_str.strip().splitlines() if users_raw_str else []
    users = set(users_raw) - {'nobody'}

    sysUsers_raw = host.get_fact(Command, "awk -F: '($3<1000){print $1}' /etc/passwd")
    sysUsers = sysUsers_raw.strip().splitlines() if sysUsers_raw else []

    userList = {user.name for user in ChObolo.users}

    toRemove = sorted(users - userList)
    return toRemove, sysUsers

def getUserPass(ChObolo, secFileO, secSopsO):
    secCfg=ChObolo.get('secrets')
    userPass={}
    if not secCfg:
        return userPass

    secMode=secCfg.get('sec_mode')
    secFile=secFileO if secFileO else secCfg.get('sec_file')
    if not secFile or not secMode:
        return userPass
    if secMode=='sops':
        try:
            result=subprocess.run(
                ['sops', '--config', secSopsO, '-d', secFile],
                capture_output=True,
                text=True,
                check=True
            )
            decryptedContent=result.stdout
            userPass=yaml.safe_load(decryptedContent).get('user_secrets',{})
        except FileNotFoundError:
            print(f"WARNING!!!! 'sops' command not found. Is it installed?")
        except subprocess.CalledProcessError as e:
            print(f"warning!!!! Could not decrypt sops file {secFile}: {e.stderr}")
        except Exception as e:
            print(f"WARNING!!!! An unexpected error occured with sops file {secFile}: {e}")
    elif secMode == 'charonte':
        try:
            with open(secFile, 'r') as f:
                userPass=yaml.safe_load(f).get('user_secrets', {})
        except Exception as e:
            print(f"WARNING!!!! Could not read file {secFile}: {e}")
    return userPass

def userLogic(state, toRemove, toAdd, skip, ChObolo, userPass):
    if toRemove or toAdd:
        print(f"\n--- users to remove ---")
        for user in toRemove:
            print(user)
        print(f"\n--- users to add/manage ---")
        for user in toAdd:
            print(user)
        confirm = "y" if skip else input("\nIs This correct (Y/n)? ")
        if confirm.lower() in ["y", "yes", "", "s", "sim"]:
            if toRemove:
                for user_name in toRemove:
                    add_op(
                        state,
                        server.user,
                        user=user_name,
                        present=False,
                        _sudo=True
                    )
            if toAdd:
                filteredUsers = [
                    next((u for u in ChObolo.users if u.name == user_name), None)
                    for user_name in toAdd
                ]
                filteredUsers = [u for u in filteredUsers if u]

                groupsToAdd = set()
                for user_details in filteredUsers:
                    if user_details.get('groups'):
                        for group in user_details.get('groups'):
                            groupsToAdd.add(group)

                for group_name in groupsToAdd:
                    add_op(
                        state,
                        server.group,
                        group=group_name,
                        _sudo=True
                    )

                for user_details in filteredUsers:
                    password=userPass.get(user_details.name, {}).get("password")
                    if not password:
                        print(f"IF YOU'RE SEEING THIS MESSAGE, IT MEANS {user_details.name}'S PASSWORD FAILED.\nPLEASE READ THE DOCUMENTATION AS TO HOW TO MANAGE YOUR PASSWORDS.")
                    if password and not password.startswith("$"):
                        print(f"WARNING! {user_details.name}'s password is not hashed, hashing the password for security...")
                        password = sha512_crypt.hash(password)
                    add_op(
                        state,
                        server.user,
                        user=user_details.name,
                        home=user_details.get('home', f'/home/{user_details.get("name")}'),
                        shell=f"/bin/{user_details.get('shell', 'bash')}",
                        groups=user_details.get('groups'),
                        password=password,
                        _sudo=True
                    )
    else:
        print(f"\nNo users to be managed.")

def manageHostname(state, ChObolo):
    hostname = ChObolo.get('hostname')
    if hostname:
        add_op(
            state,
            files.put,
            name=f"Set hostname to {hostname}",
            src=StringIO(f"{hostname}\n"),
            dest="/etc/hostname",
            _sudo=True
        )

def manageSudoAccess(state, host, ChObolo):
    desiredRules = {}
    if ChObolo.get('users'):
        for user in ChObolo.users:
            sudoAcc = user.get('sudo')
            if sudoAcc:
                userRule=f"{user.name} ALL=(ALL:ALL) ALL\n"
                ruleFile=f"99-charonte-{user.name}"
                desiredRules[ruleFile] = userRule
    try:
        actualFilesStr = host.get_fact(Command, "find /etc/sudoers.d/ -type f -name '99-charonte-*' -printf '%f\n'", _sudo=True)
        if actualFilesStr is None:
            actualFiles = []
        else:
            actualFiles = actualFilesStr.strip().splitlines()
    except Exception as e:
        print(f"WARNING: Not able to list /etc/sudoers.d/. {e}")
        actualFiles = []
    managedFiles = set(actualFiles)
    filesToManage = set(desiredRules.keys())
    filesToRemove = managedFiles - filesToManage

    for filename in filesToRemove:
        add_op(
            state,
            files.file,
            name=f"Remove old sudo rule {filename}",
            path=f"/etc/sudoers.d/{filename}",
            present=False,
            _sudo=True
        )

    for filename, content in desiredRules.items():
        rulePath = f"/etc/sudoers.d/{filename}"
        add_op(
            state,
            files.put,
            name=f"Ensure sudo rule {filename}",
            src=StringIO(content),
            dest=rulePath,
            mode="0440",
            user="root",
            group="root",
            _sudo=True
        )
        add_op(
            state,
            server.shell,
            name=f"Validate sudo rule {filename}",
            commands=[f"visudo -c -f {rulePath}"],
            _sudo=True
        )

def run_user_logic(state, host, chobolo_path, skip, secrets_file_override, sops_file_override):
    ChObolo = OmegaConf.load(chobolo_path)

    toRemove, sysUsers = userDelta(host, ChObolo)
    # We manage all users defined in the config, not just new ones.
    toAdd=[]
    if ChObolo.get('users'):
        for user in ChObolo.get('users'):
            if user.name not in sysUsers:
                toAdd.append(user.name)
            else:
                print(f"cannot manage {user.name}, it is a system user.")
    userPass = getUserPass(ChObolo, secrets_file_override, sops_file_override)

    manageHostname(state, ChObolo)
    manageSudoAccess(state, host, ChObolo)
    userLogic(state, toRemove, toAdd, skip, ChObolo, userPass)

