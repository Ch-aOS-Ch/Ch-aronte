from typing import Any

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from pyinfra.api.operation import add_op
from pyinfra.facts.files import File
from pyinfra.operations import git, pacman, server


class AurHelperRole(Role):
    def __init__(self):
        super().__init__(
            name="Install Declared AUR Helpers",
            needs_secrets=False,
            necessary_chobolo_keys=["aurHelpers"],
        )

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        from pyinfra.facts.server import Command

        declared_helpers = chobolo.get("aurHelpers", [])
        known_helpers = [
            {"name": "yay", "checkFile": "/usr/bin/yay"},
            {"name": "paru", "checkFile": "/usr/bin/paru"},
        ]

        check_files = " ".join([h["checkFile"] for h in known_helpers])
        try:
            installed_paths = (
                host.get_fact(Command, f"ls -1 {check_files} 2>/dev/null || true")
                .strip()
                .splitlines()
            )
        except Exception:
            installed_paths = []

        installed_helpers = {}
        for helper in known_helpers:
            installed_helpers[helper["name"]] = helper["checkFile"] in installed_paths

        return {
            "declared_helpers": declared_helpers,
            "installed_helpers": installed_helpers,
            "known_helpers": [h["name"] for h in known_helpers],
        }

    def delta(self, context: dict[str, Any] = {}) -> Delta:
        declared_helpers = context.get("declared_helpers", [])
        installed_helpers = context.get("installed_helpers", {})
        known_helpers = context.get("known_helpers", [])

        helpers_to_add = []
        helpers_to_remove = []

        for helper in known_helpers:
            is_installed = installed_helpers.get(helper, False)
            is_declared = helper in declared_helpers

            if is_installed and not is_declared:
                helpers_to_remove.append(helper)

            elif is_declared and not is_installed:
                helpers_to_add.append(helper)

        to_add = {}
        if helpers_to_add:
            to_add["aur_helpers"] = helpers_to_add

        to_remove = {}
        if helpers_to_remove:
            to_remove["aur_helpers"] = helpers_to_remove

        return Delta(to_add=to_add, to_remove=to_remove)

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        helpers_to_add = delta.to_add.get("aur_helpers", [])
        helpers_to_remove = delta.to_remove.get("aur_helpers", [])

        command = "makepkg -sirc --noconfirm --needed"

        try:
            if helpers_to_add:
                for helper in helpers_to_add:
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

            if helpers_to_remove:
                add_op(
                    state,
                    pacman.packages,
                    packages=helpers_to_remove,
                    present=False,
                    _sudo=True,
                )

            return ResultPayload(success=True, message=[], error=[], data={})
        except Exception as e:
            return ResultPayload(
                success=False,
                message=[],
                error=[f"Error planning aurHelper role: {str(e)}"],
                data={},
            )
