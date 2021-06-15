import pytest
from bump_changelog import get_next_version, transform_content


@pytest.mark.parametrize(
    "version,expected", [["2.6.1", "2.6.2"], ["2.6.1-dev0", "2.6.2-dev0"]]
)
def test_get_next_version(version, expected):
    assert get_next_version(version) == expected


@pytest.mark.parametrize(
    "old_content,expected_error",
    [
        [
            """
What's New in astroid 2.6.1?
============================
Release Date: TBA

What's New in astroid 2.6.0?
============================
Release Date: TBA
""",
            "More than one release date 'TBA'",
        ],
        [
            """===================
astroid's ChangeLog
===================

What's New in astroid 2.6.0?
============================
Release Date: TBA
""",
            "text for this version '2.6.1' did not exists",
        ],
        [
            """
What's New in astroid 2.6.2?
============================
Release Date: TBA

What's New in astroid 2.6.1?
============================
Release Date: 2012-02-05
""",
            "the next version '2.6.2' already exists",
        ],
    ],
)
def test_update_content_error(old_content, expected_error):
    with pytest.raises(AssertionError, match=expected_error):
        transform_content(old_content, "2.6.1", "2.6.2")


def test_update_content():
    old_content = """
===================
astroid's ChangeLog
===================

What's New in astroid 2.6.1?
============================
Release Date: TBA
"""
    expected_beginning = """
===================
astroid's ChangeLog
===================

What's New in astroid 2.6.2?
============================
Release Date: TBA



What's New in astroid 2.6.1?
============================
Release Date: 20"""

    new_content = transform_content(old_content, "2.6.1", "2.6.2")
    assert new_content.startswith(expected_beginning)
