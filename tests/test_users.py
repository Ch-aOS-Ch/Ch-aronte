from unittest.mock import Mock
from omegaconf import OmegaConf
from charonte.roles.users.tasks.users import userDelta

def test_user_delta():
    chobolo_str = """
users:
  - name: "dex"
  - name: "machina"
"""
    chobolo = OmegaConf.create(chobolo_str)
    
    # Mock o objeto host e seu método get_fact
    mock_host = Mock()
    
    # Simula a saída do comando awk
    mock_host.get_fact.side_effect = [
        "dex\nuser_to_remove\nnobody", # primeira chamada para usuários não-sistema
        "root\nbin\ndaemon" # segunda chamada para usuários de sistema
    ]

    to_remove, sys_users = userDelta(mock_host, chobolo)

    assert "user_to_remove" in to_remove
    assert "dex" not in to_remove
    assert "machina" not in to_remove # usuário a ser adicionado, não removido
    assert "nobody" not in to_remove # 'nobody' é explicitamente ignorado
    
    assert "root" in sys_users
    assert "bin" in sys_users

    # Teste sem usuários na config
    chobolo_no_users = OmegaConf.create({})
    mock_host.get_fact.side_effect = [
        "dex\nuser_to_remove\nnobody",
        "root\nbin\ndaemon"
    ]
    to_remove_2, _ = userDelta(mock_host, chobolo_no_users)
    assert not to_remove_2 # Se a chave 'users' não está no chobolo, não deve remover nenhum usuário.

    # Teste com lista de usuários vazia
    chobolo_empty_users = OmegaConf.create("users: []")
    mock_host.get_fact.side_effect = [
        "dex\nuser_to_remove\nnobody",
        "root\nbin\ndaemon"
    ]
    to_remove_3, _ = userDelta(mock_host, chobolo_empty_users)
    assert "dex" in to_remove_3
    assert "user_to_remove" in to_remove_3
