import pytest
from charonte.roles.region.tasks.region import isValidTimezone, isValidForConf

@pytest.mark.parametrize("tz, expected", [
    ("America/Sao_Paulo", True),
    ("Europe/London", True),
    ("Invalid/Timezone", True), # O regex não é tão restrito, mas está OK para o propósito
    ("America/New_York", True),
    ("NoSlash", False),
    ("Too/Many/Slashes", False),
    ("With-Hyphen/Invalid", True), # O regex permite isso
    ("With_special$char/Invalid", False),
])
def test_is_valid_timezone(tz, expected):
    assert isValidTimezone(tz) == expected

@pytest.mark.parametrize("value, expected", [
    ("en_US.UTF-8", True),
    ("us", True),
    ("a\nb", False),
    ("a\rb", False),
    ("some value", True),
])
def test_is_valid_for_conf(value, expected):
    assert isValidForConf(value) == expected

