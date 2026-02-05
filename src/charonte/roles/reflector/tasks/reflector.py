from omegaconf import OmegaConf
from pyinfra.api.operation import add_op
from pyinfra.operations import server


def reflectorLogic(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)
    mirrors = ChObolo.get("mirrors", {"count": 25, "countries": ["US", "BR"]})
    count = mirrors.get("count", 25)
    countries = mirrors.get("countries", [])

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
            command_list.extend(["-c", country])

    add_op(
        state,
        server.shell,
        name="Running reflector to update mirrorlist",
        commands=[command_list],
        _sudo=True,
    )
