from typing import Any

from chaos.lib.args.dataclasses import Delta, ResultPayload
from chaos.lib.roles.role import Role
from pyinfra.api.operation import add_op
from pyinfra.operations import server


class ReflectorRole(Role):
    def __init__(self):
        super().__init__(
            name="Configure Pacman Mirrors With Reflector",
            needs_secrets=False,
            necessary_chobolo_keys=["mirrors"],
        )

    def get_context(
        self, state, host, chobolo: dict = {}, secrets: dict[str, Any] = {}
    ) -> dict[str, Any]:
        mirrors = chobolo.get("mirrors", {})
        if not mirrors:
            mirrors = {"count": 25, "countries": ["US", "BR"]}

        count = mirrors.get("count", 25)
        countries = mirrors.get("countries", [])

        return {
            "count": count,
            "countries": countries,
        }

    def delta(self, context: dict[str, Any] = {}) -> Delta:
        errors = []
        count = context.get("count", 25)
        countries = context.get("countries", [])

        try:
            count = int(count)
            if count <= 0:
                errors.append("Mirror count must be a positive integer.")
        except (ValueError, TypeError):
            errors.append("Mirror count must be an integer.")

        if not isinstance(countries, list):
            errors.append("Countries must be a list of strings.")
        else:
            for c in countries:
                if not isinstance(c, str):
                    errors.append("Countries must be a list of strings.")
                    break

        if errors:
            return Delta(metadata={"errors": errors})

        return Delta(
            metadata={
                "count": count,
                "countries": countries,
            }
        )

    def plan(self, state, host, delta: Delta = Delta()) -> ResultPayload:
        errors = delta.metadata.get("errors", [])
        if errors:
            return ResultPayload(success=False, message=[], error=errors, data={})

        count = delta.metadata.get("count")
        countries = delta.metadata.get("countries", [])

        command_list = [
            "reflector",
            "--verbose",
            "--latest",
            str(count),
            "--sort",
            "rate",
            "--save",
            "/etc/pacman.d/mirrorlist",
        ]

        if countries:
            for country in countries:
                command_list.extend(["-c", str(country)])

        try:
            add_op(
                state,
                server.shell,
                name="Running reflector to update mirrorlist",
                commands=[" ".join(command_list)],
                _sudo=True,
            )
            return ResultPayload(success=True, message=[], error=[], data={})
        except Exception as e:
            return ResultPayload(
                success=False,
                message=[],
                error=[f"Error planning reflector role: {str(e)}"],
                data={},
            )
