import re
from io import StringIO
from typing import Any

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from pyinfra.api.operation import add_op
from pyinfra.facts.server import Command
from pyinfra.operations import files, server


class RegionRole(Role):
    def __init__(self):
        super().__init__(
            name="region",
            needs_secrets=False,
            necessary_chobolo_keys=["region"],
        )

    @staticmethod
    def _is_valid_timezone(tz: str) -> bool:
        return bool(re.match(r"^[A-Za-z_-]+/[A-Za-z_-]+$", tz))

    @staticmethod
    def _is_valid_for_conf(value: str) -> bool:
        return "\n" not in value and "\r" not in value

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        region = chobolo.get("region", {})

        locales = region.get("locale", [])
        keymap = region.get("keymap", "")
        timezone = region.get("timezone", "")
        ntp = region.get("ntp", False)

        try:
            original_locale_gen = host.get_fact(
                Command, "cat /etc/locale.gen", _sudo=True
            )
            if original_locale_gen is None:
                original_locale_gen = ""
        except Exception:
            original_locale_gen = ""

        return {
            "locales": locales,
            "keymap": keymap,
            "timezone": timezone,
            "ntp": ntp,
            "original_locale_gen": original_locale_gen,
        }

    def delta(self, context: dict[str, Any] = {}) -> Delta:
        errors = []
        locales = context.get("locales", [])
        keymap = context.get("keymap", "")
        timezone = context.get("timezone", "")
        ntp = context.get("ntp", False)
        original_locale_gen = context.get("original_locale_gen", "")

        if timezone and not self._is_valid_timezone(timezone):
            errors.append(f"Timezone '{timezone}' is invalid.")

        if keymap and not self._is_valid_for_conf(keymap):
            errors.append(f"Keymap '{keymap}' contains invalid characters.")

        valid_locales = []
        if locales:
            for locale in locales:
                if not self._is_valid_for_conf(locale):
                    errors.append(f"Locale '{locale}' contains invalid characters.")
                else:
                    valid_locales.append(locale)

        modified_content = original_locale_gen
        locale_gen_needs_update = False

        if valid_locales and modified_content:
            for locale in valid_locales:
                desired_line = f"{locale} UTF-8"
                regex = re.compile(
                    rf"^\s*#?\s*{re.escape(locale)}\s+UTF-8.*$", re.MULTILINE
                )
                if not re.search(
                    rf"^\s*{re.escape(desired_line)}.*$", modified_content, re.MULTILINE
                ):
                    new_content, num_subs = regex.subn(desired_line, modified_content)
                    if num_subs > 0:
                        modified_content = new_content
                    else:
                        modified_content += f"\n{desired_line}"

            if modified_content != original_locale_gen:
                locale_gen_needs_update = True

        if errors:
            return Delta(metadata={"errors": errors})

        return Delta(
            metadata={
                "locales": valid_locales,
                "keymap": keymap,
                "timezone": timezone,
                "ntp": ntp,
                "locale_gen_needs_update": locale_gen_needs_update,
                "locale_gen_content": modified_content
                if locale_gen_needs_update
                else None,
            }
        )

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        errors = delta.metadata.get("errors", [])
        if errors:
            return ResultPayload(success=False, message=[], error=errors, data={})

        timezone = delta.metadata.get("timezone")
        ntp = delta.metadata.get("ntp")
        locales = delta.metadata.get("locales")
        keymap = delta.metadata.get("keymap")
        locale_gen_needs_update = delta.metadata.get("locale_gen_needs_update")
        locale_gen_content = delta.metadata.get("locale_gen_content")

        try:
            if timezone:
                add_op(
                    state,
                    server.shell,
                    name=f"Set timezone to {timezone}",
                    commands=[["timedatectl", "set-timezone", timezone]],
                    _sudo=True,
                )
            if ntp:
                add_op(
                    state,
                    server.shell,
                    name="Enable NTP",
                    commands=[["timedatectl", "set-ntp", "true"]],
                    _sudo=True,
                )

            if locale_gen_needs_update and locale_gen_content:
                add_op(
                    state,
                    files.put,
                    name="Update /etc/locale.gen with desired locales",
                    src=StringIO(locale_gen_content),
                    dest="/etc/locale.gen",
                    _sudo=True,
                )
                add_op(
                    state,
                    server.shell,
                    name="Regenerate locales",
                    commands="locale-gen",
                    _sudo=True,
                )

            if locales:
                default_locale = locales[0]
                add_op(
                    state,
                    files.put,
                    name=f"Set default locale as {default_locale}",
                    src=StringIO(f"LANG={default_locale}\n"),
                    dest="/etc/locale.conf",
                    _sudo=True,
                    mode="0644",
                )
            if keymap:
                add_op(
                    state,
                    files.put,
                    name=f"Set default keymap as {keymap}",
                    src=StringIO(f"KEYMAP={keymap}\n"),
                    dest="/etc/vconsole.conf",
                    _sudo=True,
                    mode="0644",
                )

            return ResultPayload(success=True, message=[], error=[], data={})
        except Exception as e:
            return ResultPayload(
                success=False,
                message=[],
                error=[f"Error planning region role: {str(e)}"],
                data={},
            )
