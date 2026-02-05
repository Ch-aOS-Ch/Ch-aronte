from omegaconf import OmegaConf

from charonte.roles.repos.tasks.repos import PACMAN_OPTIONS_BLOCK, buildPacmanConfSecure


def test_build_default_conf():
    """Test building pacman.conf with default settings."""
    chobolo_str = """
repos:
  managed:
    core: True
"""
    chobolo = OmegaConf.create(chobolo_str)

    result = buildPacmanConfSecure(chobolo)

    assert PACMAN_OPTIONS_BLOCK in result
    assert "[core]" in result
    assert "[extra]" not in result


def test_build_with_third_party():
    """Test adding a third-party repository."""
    chobolo_str = """
repos:
  third_party:
    - name: "my-custom-repo"
      url: "https://my.repo.com/$arch"
"""
    chobolo = OmegaConf.create(chobolo_str)

    result = buildPacmanConfSecure(chobolo)

    assert "[my-custom-repo]" in result
    assert "Server = https://my.repo.com/$arch" in result
    assert PACMAN_OPTIONS_BLOCK in result


def test_build_with_all_managed():
    """Test enabling all managed repositories."""
    chobolo_str = """
repos:
  managed:
    core: True
    extras: True
    unstable: True
"""
    chobolo = OmegaConf.create(chobolo_str)

    result = buildPacmanConfSecure(chobolo)

    assert "[core]" in result
    assert "[extra]" in result
    assert "[multilib]" in result
    assert "[core-testing]" in result
    assert "[extra-testing]" in result
    assert "[multilib-testing]" in result


def test_build_override_option():
    """Test the 'i_know_exactly_what_im_doing' override."""
    chobolo_str = """
repos:
  i_know_exactly_what_im_doing: |
    [options]
    MyCustomOptions = True
"""
    chobolo = OmegaConf.create(chobolo_str)

    result = buildPacmanConfSecure(chobolo)

    assert result.startswith("[options]\nMyCustomOptions = True")
    assert PACMAN_OPTIONS_BLOCK not in result


def test_invalid_repo_field_is_skipped():
    """Test that repos with invalid fields are skipped."""
    chobolo_str = """
repos:
  third_party:
    - name: "invalid[repo]"
      url: "https://valid.url"
    - name: "valid-repo"
      url: "https://invalid.url/[arch]"
"""
    chobolo = OmegaConf.create(chobolo_str)

    result = buildPacmanConfSecure(chobolo)

    assert "[invalid[repo]]" not in result
    assert "valid-repo" not in result
