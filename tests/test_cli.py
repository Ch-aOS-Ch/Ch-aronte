from unittest.mock import patch, MagicMock

from charonte.cli import discover_roles

# Uma função de exemplo que nossos entry points falsos irão "carregar"
def fake_role_function_one():
    pass

def fake_role_function_two():
    pass

def test_discover_roles_no_plugins():
    """
    Testa se discover_roles retorna um dicionário vazio quando nenhum plugin é encontrado.
    """
    # Usamos 'patch' para substituir a função 'entry_points' real dentro do módulo 'charonte.cli'
    with patch('charonte.cli.entry_points') as mock_entry_points:
        # Configuramos o mock para retornar uma lista vazia
        mock_entry_points.return_value = []
        
        roles = discover_roles()
        
        # Verificamos se o resultado é um dicionário vazio
        assert roles == {}
        # Verificamos se a função 'entry_points' foi chamada com o grupo correto
        mock_entry_points.assert_called_once_with(group='charonte.roles')

def test_discover_roles_with_plugins():
    """
    Testa se discover_roles encontra e carrega os plugins corretamente.
    """
    # Criamos objetos falsos (MagicMock) para simular os EntryPoints
    # Cada mock precisa de um atributo 'name' e um método 'load'
    mock_ep1 = MagicMock()
    mock_ep1.name = 'plugin1'
    mock_ep1.load.return_value = fake_role_function_one

    mock_ep2 = MagicMock()
    mock_ep2.name = 'plugin2'
    mock_ep2.load.return_value = fake_role_function_two

    with patch('charonte.cli.entry_points') as mock_entry_points:
        # Configuramos o mock para retornar nossa lista de plugins falsos
        mock_entry_points.return_value = [mock_ep1, mock_ep2]
        
        roles = discover_roles()
        
        # Verificamos se o dicionário tem o número correto de itens
        assert len(roles) == 2
        
        # Verificamos se os nomes e as funções carregadas estão corretos
        assert 'plugin1' in roles
        assert roles['plugin1'] == fake_role_function_one
        
        assert 'plugin2' in roles
        assert roles['plugin2'] == fake_role_function_two

        # Verificamos se o método 'load' foi chamado para cada entry point
        mock_ep1.load.assert_called_once()
        mock_ep2.load.assert_called_once()
        
        mock_entry_points.assert_called_once_with(group='charonte.roles')
