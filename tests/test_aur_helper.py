from unittest.mock import Mock
from omegaconf import OmegaConf
from charonte.roles.aurHelper.tasks.helper import helperDelta

def test_add_helper():
    """Test adding a new AUR helper when none are installed."""
    chobolo_str = """
aurHelpers:
  - yay
"""
    chobolo = OmegaConf.create(chobolo_str)
    mock_host = Mock()

    # Simulate that no helpers are installed.
    mock_host.get_fact.return_value = None

    to_add, to_remove = helperDelta(mock_host, chobolo)

    assert "yay" in to_add
    assert not to_remove

def test_remove_helper():
    """Test removing an obsolete AUR helper."""
    chobolo_str = """
aurHelpers: []
"""
    chobolo = OmegaConf.create(chobolo_str)
    mock_host = Mock()

    # Simulate that 'paru' is installed, but 'yay' is not.
    def side_effect(fact, path):
        if 'paru' in path:
            return {'path': '/usr/bin/paru'}
        return None
    mock_host.get_fact.side_effect = side_effect

    to_add, to_remove = helperDelta(mock_host, chobolo)

    assert not to_add
    assert "paru" in to_remove
    assert "yay" not in to_remove

def test_switch_helpers():
    """Test switching from one helper to another."""
    chobolo_str = """
aurHelpers:
  - paru
"""
    chobolo = OmegaConf.create(chobolo_str)
    mock_host = Mock()

    # Simulate 'yay' is installed, but 'paru' is not.
    def side_effect(fact, path):
        if 'yay' in path:
            return {'path': '/usr/bin/yay'}
        if 'paru' in path:
            return None
    mock_host.get_fact.side_effect = side_effect

    to_add, to_remove = helperDelta(mock_host, chobolo)

    assert "paru" in to_add
    assert "yay" in to_remove

def test_no_changes_needed():
    """Test scenario where the state is already as desired."""
    chobolo_str = """
aurHelpers:
  - yay
"""
    chobolo = OmegaConf.create(chobolo_str)
    mock_host = Mock()

    # Simulate that 'yay' is installed, but 'paru' is not.
    def side_effect(fact, path):
        if 'yay' in path:
            return {'path': '/usr/bin/yay'}
        if 'paru' in path:
            return None
    mock_host.get_fact.side_effect = side_effect

    to_add, to_remove = helperDelta(mock_host, chobolo)

    assert not to_add
    assert not to_remove
