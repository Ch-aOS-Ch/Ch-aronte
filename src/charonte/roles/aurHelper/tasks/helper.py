import os

from omegaconf import OmegaConf
from pyinfra.api.operation import add_op
from pyinfra.facts.files import File
from pyinfra.operations import pacman, git, server

def helperDelta(host, ChObolo):
    declaredHelpers = ChObolo.get('aurHelpers', [])
    knownHelpers = [
        {"name": 'yay', 'checkFile': '/usr/bin/yay'},
        {"name": "paru", "checkFile": "/usr/bin/paru"},
    ]
    helpersToAdd=[]
    helpersToRemove=[]
    for helper in knownHelpers:
        isInstalled = host.get_fact(File, path=helper['checkFile'])
        isDeclared = helper['name'] in declaredHelpers
        if isInstalled and not isDeclared:
            helpersToRemove.append(helper['name'])
        elif isDeclared and not isInstalled:
            helpersToAdd.append(helper['name'])
    return helpersToAdd, helpersToRemove

def helperLogic(state, host, helpersToAdd, helpersToRemove):
    command="makepkg -sirc --noconfirm --needed"
    if helpersToAdd:
        for helper in helpersToAdd:
            repo = f"https://aur.archlinux.org/{helper}.git"
            if not host.get_fact(File, path=f"/tmp/{helper}/PKGBUILD"):
                add_op(
                    state,
                    git.repo,
                    name=f"Clone {helper}",
                    src=repo,
                    dest=f"/tmp/{helper}",
                )
            add_op(
                state,
                server.shell,
                name=f"Build and install {helper}",
                commands=command,
                chdir=f"/tmp/{helper}",
            )
    if helpersToRemove:
        add_op(
            state,
            pacman.packages,
            packages=helpersToRemove,
            present=False,
            _sudo=True
        )

def run_aur(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)
    helpersToAdd, helpersToRemove = helperDelta(host, ChObolo)
    if helpersToAdd:
        print("\n--- AUR Helpers To Add ---")
        for helper in helpersToAdd:
            print(helper)
    if helpersToRemove:
        print("\n--- AUR Helpers To Remove ---")
        for helper in helpersToRemove:
            print(helper)

    if helpersToAdd or helpersToRemove:
        confirm = "y" if skip else input("\nIs This correct (Y/n)? ")
        if confirm.lower() in ["y", "yes", "", "s", "sim"]:
            if helpersToAdd or helpersToRemove:
                helperLogic(state, host, helpersToAdd, helpersToRemove)
    else:
        print("Nothing to be done.")
