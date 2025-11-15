# translating this code to python with pyinfra for charonte
from omegaconf import OmegaConf

from pyinfra.api.operation import add_op
from pyinfra.operations import server

def reflectorLogic(state, host, chobolo_path, skip):
    ChObolo = OmegaConf.load(chobolo_path)
    mirrors = ChObolo.get('mirrors', {'count': 25, 'countries': ['US', 'BR']})
    count = mirrors.get('count', 25)
    countries = mirrors.get('countries')
    country_args = ' '.join(f'-c {country}' for country in countries)
    command = f'reflector --verbose --latest {count} --sort rate --save /etc/pacman.d/mirrorlist {country_args}'
    add_op(
        state,
        server.shell,
        name=f"Running reflector to update mirrorlist",
        commands=command,
        _sudo=True
    )
