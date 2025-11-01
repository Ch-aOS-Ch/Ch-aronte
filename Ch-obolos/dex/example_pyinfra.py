#!/usr/bin/env python3

from pyinfra.api import State, Config, Inventory, connect
from pyinfra.connectors.local import LocalConnector
from pyinfra.facts.server import Command
from pyinfra.api.exceptions import PyinfraError


def fetch_local_packages():
    """
    Usa o pyinfra como biblioteca para coletar o Fact PacmanPackages localmente.
    """

    print("Iniciando coleta do Fact PacmanPackages via pyinfra...")

    state = None  # garante que existe para o finally

    try:
        # 1. Criar Inventário com suporte à API nova do pyinfra
        # Necessary step, creates the inventory with the IPs
        inventory = Inventory(
            names_data=(["@local"], {}),
        )

        # 2. Criar configuração e o estado, incluindo o conector local
        # Necessary steps, makes config an alias+allows to use connectors as an localhost
        # then, on the state, it passas the connections and the connectors
        config = Config()
        config.connectors = {"@local": (LocalConnector, {})}
        state = State(
            inventory,
            config,
        )

        # 3. Conectar ao host
        print("Conectando ao host local...")
        # Necessary step, connects with the config in state
        connect.connect_all(state)

        # 4. Obter o host do inventário
        # Necessary step, uses the localhost as an host
        host = state.inventory.get_host("@local")

        # 5. Coletar dados via 'pacman -Qqen'
        print("Coletando pacotes instalados (via pacman -Qqen)...")

        # This allows for quick command inputs
        raw_output_string = host.get_fact(Command, "pacman -Qqen")
        raw_output_string_aur = host.get_fact(Command, "pacman -Qqem")


        if not raw_output_string:
            print("Nenhum pacote encontrado.")
            return

        # 6. Exibir resultado
        print(f"\n--- Pacotes Nativos e Explícitos (-Qqen) ---")

        # creates the parsed list
        package_list = raw_output_string.strip().splitlines()
        list_aur= raw_output_string_aur.strip().splitlines()

        # sorts list
        package_list.sort()
        list_aur.sort()

        print(f"Total: {len(package_list)}\n")
        # prints list
        for pkg_name in package_list:
            print(pkg_name)

        print(f"Total aur: {len(list_aur)}\n")
        for pkg_name in list_aur:
            print(pkg_name)

    except PyinfraError as e:
        print(f"[ERRO pyinfra] {e}")
    except Exception as e:
        print(f"[ERRO inesperado] {e}")
    finally:
        if state:
            print("\nDesconectando...")
            # Necessary step, disconnection
            connect.disconnect_all(state)
            print("Conexão finalizada.")


if __name__ == "__main__":
    fetch_local_packages()
