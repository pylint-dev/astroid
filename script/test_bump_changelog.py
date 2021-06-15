import pytest
from bump_changelog import get_next_version


@pytest.mark.parametrize(
    "version,expected", [["2.6.1", "2.6.2"], ["2.6.1-dev0", "2.6.2-dev0"]]
)
def test_get_next_version(version, expected):
    assert get_next_version(version) == expected
