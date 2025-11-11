import hashlib
from io import StringIO
from omegaconf import OmegaConf
from pyinfra.api.operation import add_op
from pyinfra.operations import files, pacman
from pyinfra.facts.files import Sha1File

# Você pode definir seu bloco [options] como uma constante
PACMAN_OPTIONS_BLOCK = """
[options]
#RootDir     = /
#DBPath      = /var/lib/pacman/
#CacheDir    = /var/cache/pacman/pkg/
#LogFile     = /var/log/pacman.log
#GPGDir      = /etc/pacman.d/gnupg/
#HookDir     = /etc/pacman.d/hooks/
HoldPkg     = pacman glibc
#XferCommand = /usr/bin/curl -L -C - -f -o %o %u
#XferCommand = /usr/bin/wget --passive-ftp -c -O %o %u
#CleanMethod = KeepInstalled
Architecture = auto

#IgnorePkg   =
#IgnorePkg   =
#IgnoreGroup =

#NoUpgrade   =
#NoExtract   =

# Misc options
#UseSyslog
Color
ILoveCandy
#NoProgressBar
CheckSpace
#VerbosePkgLists
ParallelDownloads = 5
DownloadUser = alpm
#DisableSandbox

# By default, pacman accepts packages signed by keys that its local keyring
# trusts (see pacman-key and its man page), as well as unsigned packages.
SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional
#RemoteFileSigLevel = Required

# NOTE: You must run `pacman-key --init` before first using pacman; the local
# keyring can then be populated with the keys of all official Arch Linux
# packagers with `pacman-key --populate archlinux`.

#
# REPOSITORIES
#   - can be defined here or included from another file
#   - pacman will search repositories in the order defined here
#   - local/custom mirrors can be added here or in separate files
#   - repositories listed first will take precedence when packages
#     have identical names, regardless of version number
#   - URLs will have $repo replaced by the name of the current repo
#   - URLs will have $arch replaced by the name of the architecture
#
# Repository entries are of the format:
#       [repo-name]
#       Server = ServerName
#       Include = IncludePath
#
# The header [repo-name] is crucial - it must be present and
# uncommented to enable the repo.
#

# The testing repositories are disabled by default. To enable, uncomment the
# repo name header and Include lines. You can add preferred servers immediately
# after the header, and they will be used before the default mirrors.
"""

def buildPacmanConf(ChObolo):
    reposCfg = ChObolo.get('repos',{})
    if not reposCfg.get('i_know_exactly_what_im_doing'):
        pacmanConf = [PACMAN_OPTIONS_BLOCK]
    else:
        pacmanConf = [reposCfg.get('i_know_exactly_what_im_doing')]
    managed = reposCfg.get('managed', {})
    thirdParty = reposCfg.get('third_party', {})

    if thirdParty:
        for repo in thirdParty:
            repoBlock = [f"\n[{repo.name}]"]
            if not (repo.get('url') or repo.get('include')):
                print(f"No way to manage repo {repo.name}")
            else:
                if repo.get('url'):
                    repoBlock.append(f"\nServer = {repo.url}")
                if repo.get('include'):
                    repoBlock.append(f"\nInclude = {repo.include}")
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
            pacmanConf.append("\n[multilibtesting]\nInclude=/etc/pacman.d/mirrorlist")

    return "\n".join(pacmanConf)


def run_repo_logic(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)

    if not ChObolo.get('repos', {}):
        print("No repos to be managed.")
    else:
        desiredContent = buildPacmanConf(ChObolo)
        desiredHash = hashlib.sha1(desiredContent.encode('utf-8')).hexdigest()

        currentHash = host.get_fact(Sha1File, path="/etc/pacman.conf", _sudo=True)

        if desiredHash != currentHash:
            print(desiredContent)

            print("Changes will be applied.")
            confirm = "y" if skip else input("\nIs This correct (Y/n)? ")
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

                add_op(
                    state,
                    pacman.update,
                    name="Update pacman cache",
                    _sudo=True
                )
        else:
            print("Desired state is already current state.")
