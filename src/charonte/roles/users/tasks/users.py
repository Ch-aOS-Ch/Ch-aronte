import base64
from io import StringIO
from typing import Any, Optional

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from passlib.hash import sha512_crypt
from pyinfra.api.operation import add_op
from pyinfra.facts.server import Command, Users
from pyinfra.operations import files, server


class BaseUsersRole(Role):
    """
    Base class for UsersRole containing the helper functions for context, delta, and plan generation.
    """

    def _get_users_context(self, host, context: dict[str, Any]) -> None:
        all_users = host.get_fact(Users) or {}

        context["existing_users"] = {
            name
            for name, info in all_users.items()
            if info.get("uid", 0) >= 1000 and name != "nobody"
        }

        context["system_users"] = {
            name for name, info in all_users.items() if info.get("uid", 0) < 1000
        }

        context["all_users_info"] = all_users

    def _get_sudoers_context(self, host, context: dict[str, Any]) -> None:
        try:
            sudo_cmd = r"""for f in /etc/sudoers.d/99-charonte-*; do if [ -f "$f" ]; then echo "${f##*/}|$(base64 < "$f" | tr -d '\n')"; fi; done"""
            actual_files_output = host.get_fact(
                Command,
                sudo_cmd,
                _sudo=True,
            )

            managed_sudo_files = {}

            if actual_files_output:
                for line in actual_files_output.strip().splitlines():
                    if "|" in line:
                        name, b64_content = line.split("|", 1)
                        try:
                            managed_sudo_files[name] = base64.b64decode(
                                b64_content
                            ).decode("utf-8")
                        except Exception:
                            pass

            context["managed_sudo_files"] = managed_sudo_files

        except Exception:
            context["managed_sudo_files"] = {}

    def _get_shadow_context(self, host, context: dict[str, Any]) -> None:
        try:
            shadow_output = host.get_fact(Command, "cat /etc/shadow", _sudo=True)
            shadow_hashes = {}

            if shadow_output:
                for line in shadow_output.strip().splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        shadow_hashes[parts[0]] = parts[1]

            context["shadow_hashes"] = shadow_hashes
        except Exception:
            context["shadow_hashes"] = {}

    def _compute_users_delta(
        self,
        safe_context: dict[str, Any],
        to_add: dict,
        to_remove: dict,
        metadata: dict,
    ) -> None:
        chobolo_users = safe_context.get("users") or []
        user_list_from_chobolo = {user.get("name") for user in chobolo_users}
        existing_users = safe_context.get("existing_users", set())
        system_users = safe_context.get("system_users", set())
        all_users_info = safe_context.get("all_users_info", {})
        shadow_hashes = safe_context.get("shadow_hashes", {})
        user_pass = safe_context.get("secrets", {}).get("user_secrets", {})

        to_remove["users"] = sorted(existing_users - user_list_from_chobolo)

        users_for_vitrine = []
        users_to_enforce = []

        for u in chobolo_users:
            name = u["name"]
            if name in system_users:
                continue

            needs_update = False

            if name not in existing_users:
                needs_update = True
            else:
                existing_info = all_users_info.get(name, {})

                desired_shell = f"/bin/{u.get('shell', 'bash')}"
                if existing_info.get("shell") != desired_shell:
                    needs_update = True

                desired_home = u.get("home", f"/home/{name}")
                if existing_info.get("home") != desired_home:
                    needs_update = True

                desired_groups = set(u.get("groups") or [])
                existing_groups = set(existing_info.get("groups") or [])

                if not desired_groups == existing_groups:
                    needs_update = True

                password = user_pass.get(name, {}).get("password")
                if password:
                    existing_hash = shadow_hashes.get(name)
                    if not existing_hash:
                        needs_update = True
                    elif password.startswith("$"):
                        if password != existing_hash:
                            needs_update = True
                    else:
                        if existing_hash.startswith("$"):
                            try:
                                if not sha512_crypt.verify(password, existing_hash):
                                    needs_update = True
                            except ValueError:
                                needs_update = True
                        else:
                            needs_update = True

            if needs_update:
                users_for_vitrine.append(name)
                users_to_enforce.append(u)

        to_add["users"] = users_for_vitrine

        metadata["enforce_users"] = users_to_enforce

        metadata["shadow_hashes"] = shadow_hashes

        metadata["user_pass"] = user_pass

    def _compute_sudo_delta(
        self,
        safe_context: dict[str, Any],
        to_add: dict,
        to_remove: dict,
        metadata: dict,
    ) -> None:
        chobolo_users = safe_context.get("users") or []
        desired_sudo_rules = {}
        for user in chobolo_users:
            if user.get("sudo"):
                desired_sudo_rules[f"99-charonte-{user['name']}"] = (
                    f"{user['name']} ALL=(ALL:ALL) ALL\n"
                )

        managed_sudo_files = safe_context.get("managed_sudo_files", {})

        to_remove["sudo_rules"] = list(
            set(managed_sudo_files.keys()) - set(desired_sudo_rules.keys())
        )

        to_enforce_sudo = {}
        for filename, content in desired_sudo_rules.items():
            if (
                filename not in managed_sudo_files
                or managed_sudo_files[filename] != content
            ):
                to_enforce_sudo[filename] = content

        to_add["sudo_rules"] = list(to_enforce_sudo.keys())

        metadata["enforce_sudo_rules"] = to_enforce_sudo

    def _plan_hostname(self, state, host, safe_delta: Delta) -> None:
        hostname = safe_delta.to_add.get("hostname")
        if hostname:
            add_op(
                state,
                files.put,
                name=f"Set hostname to {hostname}",
                src=StringIO(f"{hostname}\n"),
                dest="/etc/hostname",
                _sudo=True,
            )

    def _plan_sudo_rules(self, state, host, safe_delta: Delta) -> None:
        sudo_rules_to_remove = safe_delta.to_remove.get("sudo_rules", [])
        for filename in sudo_rules_to_remove:
            add_op(
                state,
                files.file,
                name=f"Remove old sudo rule {filename}",
                path=f"/etc/sudoers.d/{filename}",
                present=False,
                _sudo=True,
            )

        sudo_rules_to_enforce = safe_delta.metadata.get("enforce_sudo_rules", {})
        for filename, content in sudo_rules_to_enforce.items():
            tmp_path = f"/tmp/{filename}"
            final_path = f"/etc/sudoers.d/{filename}"

            add_op(
                state,
                files.put,
                name=f"Upload sudo rule {filename} to temporary location",
                src=StringIO(content),
                dest=tmp_path,
                mode="0440",
                user="root",
                group="root",
                _sudo=True,
            )

            add_op(
                state,
                server.shell,
                name=f"Validate sudo rule {filename}",
                commands=[f"visudo -c -f {tmp_path}"],
                _sudo=True,
            )

            add_op(
                state,
                server.shell,
                name=f"Deploy validated sudo rule {filename}",
                commands=[f"mv {tmp_path} {final_path}"],
                _sudo=True,
            )

    def _plan_users(self, state, host, safe_delta: Delta, errors: list) -> None:
        users_to_remove = safe_delta.to_remove.get("users", [])
        for user_name in users_to_remove:
            add_op(state, server.user, user=user_name, present=False, _sudo=True)

        user_details_list = safe_delta.metadata.get("enforce_users", [])
        user_pass = safe_delta.metadata.get("user_pass", {})
        shadow_hashes = safe_delta.metadata.get("shadow_hashes", {})

        if user_details_list:
            groups_to_add = {
                group
                for user_details in user_details_list
                for group in user_details.get("groups", [])
            }

            for group_name in groups_to_add:
                add_op(state, server.group, group=group_name, present=True, _sudo=True)

            for user_details in user_details_list:
                username = user_details["name"]
                password = user_pass.get(username, {}).get("password")
                if not password:
                    errors.append(f"NO_PASSWORD_FOR_USER:{username}")

                if password and not password.startswith("$"):
                    existing_hash = shadow_hashes.get(username)
                    if existing_hash and existing_hash.startswith("$"):
                        try:
                            if sha512_crypt.verify(password, existing_hash):
                                password = existing_hash
                            else:
                                password = sha512_crypt.hash(password)
                        except ValueError:
                            password = sha512_crypt.hash(password)
                    else:
                        password = sha512_crypt.hash(password)

                add_op(
                    state,
                    server.user,
                    name=f"Manage user {username}",
                    user=username,
                    home=user_details.get("home", f"/home/{username}"),
                    shell=f"/bin/{user_details.get('shell', 'bash')}",
                    groups=user_details.get("groups"),
                    password=password,
                    present=True,
                    _sudo=True,
                )


class UsersRole(BaseUsersRole):
    """
    Manages users, their sudo access, and the system hostname.
    """

    def __init__(self):
        super().__init__(
            name="Configure users and sudo access",
            needs_secrets=True,
            necessary_chobolo_keys=["users", "hostname"],
            necessary_secret_dict_keys=["user_secrets"],
        )

    def get_context(
        self,
        state,
        host,
        chobolo: Optional[dict] = None,
        secrets: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        chobolo = chobolo or {}
        secrets = secrets or {}

        context = chobolo.copy()
        context["secrets"] = secrets

        self._get_users_context(host, context)
        self._get_sudoers_context(host, context)
        self._get_shadow_context(host, context)

        return context

    def delta(self, context: Optional[dict[str, Any]] = None) -> Delta:
        safe_context = context if context is not None else {}
        to_add = {}
        to_remove = {}
        metadata = {}

        self._compute_users_delta(safe_context, to_add, to_remove, metadata)
        self._compute_sudo_delta(safe_context, to_add, to_remove, metadata)

        # Hostname delta
        hostname = safe_context.get("hostname")
        if hostname:
            to_add["hostname"] = hostname

        return Delta(to_add=to_add, to_remove=to_remove, metadata=metadata)

    def plan(self, state, host, delta: Optional[Delta] = None) -> ResultPayload:
        safe_delta: Delta = delta if delta is not None else Delta()

        errors = []

        self._plan_hostname(state, host, safe_delta)
        self._plan_sudo_rules(state, host, safe_delta)
        self._plan_users(state, host, safe_delta, errors)

        return ResultPayload(success=not errors, error=errors, data=delta)
