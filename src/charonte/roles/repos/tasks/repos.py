import hashlib
from io import StringIO
from omegaconf import OmegaConf
from pyinfra.api.operation import add_op
from pyinfra.operations import files
from pyinfra.facts.files import Sha1File

PACMAN_OPTIONS_BLOCK = """
[options]
HoldPkg     = pacman glibc
Architecture = auto
Color
ILoveCandy
CheckSpace
ParallelDownloads = 5
DownloadUser = alpm
SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional
"""

def isValidRepoField(field):
    return all(char not in field for char in '\n\r[]')

def buildPacmanConfSecure(chObolo):
    reposCfg = chObolo.get('repos', {})
    if not reposCfg.get('i_know_exactly_what_im_doing'):
        pacmanConf = [PACMAN_OPTIONS_BLOCK]
    else:
        pacmanConf = [reposCfg.get('i_know_exactly_what_im_doing')]
    managed = reposCfg.get('managed', {})
    thirdParty = reposCfg.get('third_party', [])

    if thirdParty:
        for repo in thirdParty:
            repoName = repo.get('name')
            repoUrl = repo.get('url')
            repoInclude = repo.get('include')

            if not all(isValidRepoField(field) for field in [repoName, repoUrl, repoInclude] if field):
                print(f"WARNING: Repository '{repoName}' contains invalid characters and will be skipped.")
                continue

            if not (repoUrl or repoInclude):
                print(f"WARNING: No url or include path to manage repo {repoName}. Skipping.")
                continue

            repoBlock = [f"\n[{repoName}]"]
            if repoUrl:
                repoBlock.append(f"Server = {repoUrl}")
            if repoInclude:
                repoBlock.append(f"Include = {repoInclude}")
            pacmanConf.append("\n".join(repoBlock))

    if managed:
        if managed.get('core', True):
            pacmanConf.append("\n[core]\nInclude=/etc/pacman.d/mirrorlist")
        if managed.get('extras', False):
            pacmanConf.append("\n[extra]\nInclude=/etc/pacman.d/mirrorlist")
            pacmanConf.append("\n[multilib]\nInclude=/etc/pacman.d/mirrorlist")
        if managed.get('unstable', False):
            pacmanConf.append("\n[core-testing]\nInclude=/etc/pacman.d/mirrorlist")
            pacmanConf.append("\n[extra-testing]\nInclude=/etc/pacman.d/mirrorlist")
            pacmanConf.append("\n[multilib-testing]\nInclude=/etc/pacman.d/mirrorlist")

    return "\n".join(pacmanConf)

def run_repo_logic(state, host, choboloPath, skip):
    chObolo = OmegaConf.load(choboloPath)

    if not chObolo.get('repos', {}):
        print("No repos to be managed.")
        return

    desiredContent = buildPacmanConfSecure(chObolo)
    desiredHash = hashlib.sha1(desiredContent.encode('utf-8')).hexdigest()
    currentHash = host.get_fact(Sha1File, path="/etc/pacman.conf", _sudo=True)

    if desiredHash != currentHash:
        print("New pacman.conf to be applied:")
        print(desiredContent)
        confirm = "y" if skip else input("\nIs this correct (Y/n)? ")
        if confirm.lower() in ["y", "yes", "", "s", "sim"]:
            add_op(
                state,
                files.put,
                name="Deploy /etc/pacman.conf",
                src=StringIO(desiredContent),
                dest="/etc/pacman.conf",
                _sudo=True,
                mode="0644"
            )
    else:
        print("Desired state is already current state.")
