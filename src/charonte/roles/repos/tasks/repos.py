import hashlib
from io import StringIO
from typing import Any

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from pyinfra.api.operation import add_op
from pyinfra.facts.files import Sha1File
from pyinfra.operations import files

PACMAN_OPTIONS_BLOCK = """
[options]
HoldPkg           = pacman glibc
Architecture      = auto
ParallelDownloads = 5
DownloadUser      = alpm
SigLevel          = Required DatabaseOptional
LocalFileSigLevel = Optional
Color
ILoveCandy
CheckSpace
"""


class ReposRole(Role):
    def __init__(self):
        super().__init__(
            name="Configure Pacman Repositories",
            needs_secrets=False,
            necessary_chobolo_keys=["repos"],
        )

    @staticmethod
    def _is_valid_repo_field(field: str) -> bool:
        return all(char not in field for char in "\n\r[]")

    def _build_pacman_conf_secure(self, repos_cfg: dict) -> tuple[str, list[str]]:
        warnings: list[str] = []
        pacman_conf: list[str] = []

        custom_conf = repos_cfg.get("i_know_exactly_what_im_doing")
        if custom_conf:
            pacman_conf.append(str(custom_conf))
        else:
            pacman_conf.append(PACMAN_OPTIONS_BLOCK)

        managed = repos_cfg.get("managed", {})
        third_party = repos_cfg.get("third_party", [])

        if third_party:
            for repo in third_party:
                repo_name = repo.get("name")
                repo_url = repo.get("url")
                repo_include = repo.get("include")

                if not all(
                    self._is_valid_repo_field(field)
                    for field in [repo_name, repo_url, repo_include]
                    if field
                ):
                    warnings.append(
                        f"Repository '{repo_name}' contains invalid characters and will be skipped."
                    )
                    continue

                if not (repo_url or repo_include):
                    warnings.append(
                        f"No url or include path to manage repo {repo_name}. Skipping."
                    )
                    continue

                repo_block = [f"\n[{repo_name}]"]
                if repo_url:
                    repo_block.append(f"Server = {repo_url}")
                if repo_include:
                    repo_block.append(f"Include = {repo_include}")
                pacman_conf.append("\n".join(repo_block))

        if managed:
            if managed.get("core", True):
                pacman_conf.append("\n[core]\nInclude=/etc/pacman.d/mirrorlist")

            if managed.get("extras", False):
                pacman_conf.append("\n[extra]\nInclude=/etc/pacman.d/mirrorlist")
                pacman_conf.append("\n[multilib]\nInclude=/etc/pacman.d/mirrorlist")

            if managed.get("unstable", False):
                pacman_conf.append("\n[core-testing]\nInclude=/etc/pacman.d/mirrorlist")
                pacman_conf.append(
                    "\n[extra-testing]\nInclude=/etc/pacman.d/mirrorlist"
                )
                pacman_conf.append(
                    "\n[multilib-testing]\nInclude=/etc/pacman.d/mirrorlist"
                )

        return "\n".join(pacman_conf), warnings

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        repos_cfg = chobolo.get("repos", {})
        try:
            current_hash = host.get_fact(Sha1File, path="/etc/pacman.conf", _sudo=True)
        except Exception:
            current_hash = None

        return {
            "repos_cfg": repos_cfg,
            "current_hash": current_hash,
        }

    def delta(self, context: dict[str, Any] = {}) -> Delta:
        repos_cfg = context.get("repos_cfg", {})
        if not repos_cfg:
            return Delta()

        desired_content, warnings = self._build_pacman_conf_secure(repos_cfg)
        desired_hash = hashlib.sha1(desired_content.encode("utf-8")).hexdigest()
        current_hash = context.get("current_hash")

        if desired_hash != current_hash:
            return Delta(
                to_add={"pacman.conf": ["Deploy new /etc/pacman.conf"]},
                metadata={"desired_content": desired_content, "warnings": warnings},
            )

        return Delta(metadata={"warnings": warnings})

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        desired_content = delta.metadata.get("desired_content")
        warnings = delta.metadata.get("warnings", [])

        if not desired_content:
            return ResultPayload(success=True, message=warnings, error=[], data={})

        try:
            add_op(
                state,
                files.put,
                name="Deploy /etc/pacman.conf",
                src=StringIO(desired_content),
                dest="/etc/pacman.conf",
                _sudo=True,
                mode="0644",
            )
            return ResultPayload(success=True, message=warnings, error=[], data={})
        except Exception as e:
            return ResultPayload(
                success=False,
                message=[],
                error=[f"Error planning repos role: {str(e)}"],
                data={},
            )
