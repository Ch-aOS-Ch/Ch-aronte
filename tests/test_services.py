from unittest.mock import Mock
from omegaconf import OmegaConf
from charonte.roles.services.tasks.services import servicesDelta

def test_services_delta():
    chobolo_str = """
services:
  - name: "docker.service"
  - name: "bluetooth.service"
    on_boot: True
    running: True
  - name: "cups" # teste sem o sufixo .service
  - name: "libvirt" # teste de serviço "dense"
    dense_service: True
"""
    chobolo = OmegaConf.create(chobolo_str)
    
    mock_host = Mock()
    
    all_services = [
        "docker.service", "bluetooth.service", "nginx.service", "sshd.service",
        "systemd-logind.service", "libvirtd.service", "libvirt-guests.service",
        "cups.service"
    ]
    enabled_services = ["nginx.service", "systemd-logind.service"]

    # Mockar múltiplos retornos para chamadas consecutivas ao mesmo método
    mock_host.get_fact.side_effect = [
        "\n".join(all_services),
        "\n".join(enabled_services)
    ]

    to_add, to_remove, config_map = servicesDelta(mock_host, chobolo)
    
    assert "docker.service" in to_add
    assert "bluetooth.service" in to_add
    assert "cups.service" in to_add
    assert "libvirtd.service" in to_add # from dense
    assert "libvirt-guests.service" in to_add # from dense

    assert "nginx.service" in to_remove
    assert "systemd-logind.service" not in to_remove # Está na blacklist
    
    assert config_map["docker.service"].get('name') == "docker.service"
    assert config_map["libvirtd.service"].get('dense_service') is True

def test_services_delta_no_changes():
    chobolo_str = """
services:
  - name: "docker.service"
"""
    chobolo = OmegaConf.create(chobolo_str)
    mock_host = Mock()
    all_services = ["docker.service"]
    enabled_services = ["docker.service"]
    
    mock_host.get_fact.side_effect = [
        "\n".join(all_services),
        "\n".join(enabled_services)
    ]

    to_add, to_remove, _ = servicesDelta(mock_host, chobolo)
    
    assert not to_add
    assert not to_remove

def test_services_delta_missing_key():
    # Testa o comportamento quando a chave 'services' está ausente.
    # Espera-se que ele tente desativar os serviços habilitados que não estão na lista negra.
    chobolo = OmegaConf.create({}) # Chave 'services' ausente
    mock_host = Mock()
    
    all_services = ["nginx.service", "systemd-logind.service"]
    enabled_services = ["nginx.service", "systemd-logind.service"]
    
    mock_host.get_fact.side_effect = [
        "\n".join(all_services),
        "\n".join(enabled_services)
    ]

    to_add, to_remove, _ = servicesDelta(mock_host, chobolo)
    
    assert not to_add
    assert "nginx.service" in to_remove
    assert "systemd-logind.service" not in to_remove # Blacklisted

def test_services_delta_ignores_template_and_initrd_services():
    # Testa se os serviços de template (@.) e initrd são ignorados
    chobolo_str = """
services:
  - name: "a-dense-service"
    dense_service: True
"""
    chobolo = OmegaConf.create(chobolo_str)
    mock_host = Mock()
    
    all_services = [
        "a-dense-service-foo.service",
        "a-dense-service-template@.service", # Deve ser ignorado
        "another-initrd-service.service" # Deve ser ignorado
    ]
    enabled_services = [
        "user@.service", # Deve ser ignorado da lista de habilitados
        "some-initrd.service" # Deve ser ignorado da lista de habilitados
    ]
    
    mock_host.get_fact.side_effect = [
        "\n".join(all_services),
        "\n".join(enabled_services)
    ]

    to_add, to_remove, _ = servicesDelta(mock_host, chobolo)
    
    assert "a-dense-service-foo.service" in to_add
    assert "a-dense-service-template@.service" not in to_add
    assert "another-initrd-service.service" not in to_add
    
    assert not to_remove # A lista de remoção deve estar vazia pois os únicos habilitados são ignorados

