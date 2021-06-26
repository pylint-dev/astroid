import pytest
from bump_changelog import VersionType, get_next_version, transform_content


@pytest.mark.parametrize(
    "version,version_type,expected",
    [
        ["2.6.1", VersionType.PATCH, "2.6.2"],
        ["2.6.1", VersionType.MINOR, "2.7.0"],
        ["2.6.1", VersionType.MAJOR, "3.0.0"],
        ["2.6.1-dev0", VersionType.PATCH, "2.6.2"],
        ["2.6.1-dev0", VersionType.MINOR, "2.7.0"],
        ["2.6.1-dev0", VersionType.MAJOR, "3.0.0"],
        ["2.7.0", VersionType.PATCH, "2.7.1"],
        ["2.7.0", VersionType.MINOR, "2.8.0"],
        ["2.7.0", VersionType.MAJOR, "3.0.0"],
        ["2.0.0", VersionType.PATCH, "2.0.1"],
        ["2.0.0", VersionType.MINOR, "2.1.0"],
        ["2.0.0", VersionType.MAJOR, "3.0.0"],
    ],
)
def test_get_next_version(version, version_type, expected):
    assert get_next_version(version, version_type) == expected


@pytest.mark.parametrize(
    "old_content,version,expected_error",
    [
        [
            """
What's New in astroid 2.7.0?
============================
Release Date: TBA

What's New in astroid 2.6.1?
============================
Release Date: TBA

What's New in astroid 2.6.0?
============================
Release Date: TBA
""",
            "2.6.1",
            r"There should be only two release dates 'TBA' \(2.6.1 and 2.7.0\)",
        ],
        [
            """===================
astroid's ChangeLog
===================

What's New in astroid 2.6.0?
============================
Release Date: TBA
""",
            "2.6.1",
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
            "2.6.1",
            "the next version '2.6.2' already exists",
        ],
        [
            """
What's New in astroid 3.0.0?
============================
Release Date: TBA

What's New in astroid 2.6.10?
============================
Release Date: TBA
""",
            "3.0.0",
            r"There should be only one release date 'TBA' \(3.0.0\)",
        ],
        [
            """
What's New in astroid 2.7.0?
============================
Release Date: TBA

What's New in astroid 2.6.10?
============================
Release Date: TBA
""",
            "2.7.0",
            r"There should be only one release date 'TBA' \(2.7.0\)",
        ],
    ],
)
def test_update_content_error(old_content, version, expected_error):
    with pytest.raises(AssertionError, match=expected_error):
        transform_content(old_content, version)


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

    new_content = transform_content(old_content, "2.6.1")
    assert new_content.startswith(expected_beginning)
