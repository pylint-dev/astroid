# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/graphs/contributors
import logging

import pytest
from bump_changelog import (
    VersionType,
    get_next_version,
    get_next_versions,
    transform_content,
)


@pytest.mark.parametrize(
    "version,version_type,expected_version,expected_versions",
    [
        ["2.6.1", VersionType.PATCH, "2.6.2", ["2.6.2"]],
        ["2.10.0", VersionType.MINOR, "2.11.0", ["2.11.0", "2.10.1"]],
        ["10.1.10", VersionType.PATCH, "10.1.11", ["10.1.11"]],
        [
            "2.6.0",
            VersionType.MINOR,
            "2.7.0",
            [
                "2.7.0",
                "2.6.1",
            ],
        ],
        ["2.6.1", VersionType.MAJOR, "3.0.0", ["3.1.0", "3.0.1"]],
        ["2.6.1-dev0", VersionType.PATCH, "2.6.2", ["2.6.2"]],
        [
            "2.6.1-dev0",
            VersionType.MINOR,
            "2.7.0",
            [
                "2.7.1",
                "2.7.0",
            ],
        ],
        ["2.6.1-dev0", VersionType.MAJOR, "3.0.0", ["3.1.0", "3.0.1"]],
        ["2.7.0", VersionType.PATCH, "2.7.1", ["2.7.1"]],
        ["2.7.0", VersionType.MINOR, "2.8.0", ["2.8.0", "2.7.1"]],
        ["2.7.0", VersionType.MAJOR, "3.0.0", ["3.1.0", "3.0.1"]],
        ["2.0.0", VersionType.PATCH, "2.0.1", ["2.0.1"]],
        ["2.0.0", VersionType.MINOR, "2.1.0", ["2.1.0", "2.0.1"]],
        ["2.0.0", VersionType.MAJOR, "3.0.0", ["3.1.0", "3.0.1"]],
    ],
)
def test_get_next_version(version, version_type, expected_version, expected_versions):
    assert get_next_version(version, version_type) == expected_version
    if (
        version_type == VersionType.PATCH
        or version_type == VersionType.MINOR
        and version.endswith(".0")
    ):
        assert get_next_versions(version, version_type) == expected_versions


@pytest.mark.parametrize(
    "old_content,version,expected_error",
    [
        [
            """
What's New in astroid 2.7.0?
============================
Release date: TBA

What's New in astroid 2.6.1?
============================
Release date: TBA

What's New in astroid 2.6.0?
============================
Release date: TBA
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
Release date: TBA
""",
            "2.6.1",
            "text for this version '2.6.1' did not exists",
        ],
        [
            """
What's New in astroid 2.6.2?
============================
Release date: TBA

What's New in astroid 2.6.1?
============================
Release date: TBA
""",
            "2.6.1",
            "The text for the next version '2.6.2' already exists",
        ],
        [
            """
What's New in astroid 3.0.0?
============================
Release date: TBA

What's New in astroid 2.6.10?
============================
Release date: TBA
""",
            "3.0.0",
            r"There should be only one release date 'TBA' \(3.0.0\)",
        ],
        [
            """
What's New in astroid 2.7.0?
============================
Release date: TBA

What's New in astroid 2.6.10?
============================
Release date: TBA
""",
            "2.7.0",
            r"There should be only one release date 'TBA' \(2.7.0\)",
        ],
    ],
)
def test_update_content_error(old_content, version, expected_error, caplog):
    caplog.set_level(logging.DEBUG)
    with pytest.raises(AssertionError, match=expected_error):
        transform_content(old_content, version)


def test_update_content(caplog):
    caplog.set_level(logging.DEBUG)
    old_content = """
===================
astroid's ChangeLog
===================

What's New in astroid 2.6.1?
============================
Release date: TBA
"""
    expected_beginning = """
===================
astroid's ChangeLog
===================

What's New in astroid 2.6.2?
============================
Release date: TBA



What's New in astroid 2.6.1?
============================
Release date: 20"""

    new_content = transform_content(old_content, "2.6.1")
    assert new_content[: len(expected_beginning)] == expected_beginning


def test_update_content_minor():
    old_content = """
===================
astroid's ChangeLog
===================

What's New in astroid 2.7.0?
============================
Release date: TBA
"""
    expected_beginning = """
===================
astroid's ChangeLog
===================

What's New in astroid 2.8.0?
============================
Release date: TBA



What's New in astroid 2.7.1?
============================
Release date: TBA



What's New in astroid 2.7.0?
============================
Release date: 20"""

    new_content = transform_content(old_content, "2.7.0")
    assert new_content[: len(expected_beginning)] == expected_beginning


def test_update_content_major(caplog):
    caplog.set_level(logging.DEBUG)
    old_content = """
===================
astroid's ChangeLog
===================

What's New in astroid 3.0.0?
============================
Release date: TBA

What's New in astroid 2.7.1?
============================
Release date: 2020-04-03

What's New in astroid 2.7.0?
============================
Release date: 2020-04-01
"""
    expected_beginning = """
===================
astroid's ChangeLog
===================

What's New in astroid 3.1.0?
============================
Release date: TBA



What's New in astroid 3.0.1?
============================
Release date: TBA



What's New in astroid 3.0.0?
============================
Release date: 20"""
    new_content = transform_content(old_content, "3.0.0")
    assert new_content[: len(expected_beginning)] == expected_beginning
