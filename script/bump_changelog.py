"""
This script permits to upgrade the changelog in astroid or pylint when releasing a version.
"""
# pylint: disable=logging-fstring-interpolation
import argparse
import enum
import logging
from datetime import datetime
from pathlib import Path

DEFAULT_CHANGELOG_PATH = Path("ChangeLog")

RELEASE_DATE_TEXT = "Release Date: TBA"
WHATS_NEW_TEXT = "What's New in astroid"
TODAY = datetime.now()
FULL_WHATS_NEW_TEXT = WHATS_NEW_TEXT + " {version}?"
NEW_RELEASE_DATE_MESSAGE = "Release Date: {}".format(TODAY.strftime("%Y-%m-%d"))


def main() -> None:
    parser = argparse.ArgumentParser(add_help=__doc__)
    parser.add_argument("version", help="The version we want to release")
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Logging or not"
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    logging.debug(f"Launching bump_changelog with args: {args}")
    if "dev" in args.version:
        return
    with open(DEFAULT_CHANGELOG_PATH) as f:
        content = f.read()
    content = transform_content(content, args.version)
    with open(DEFAULT_CHANGELOG_PATH, "w") as f:
        f.write(content)


class VersionType(enum.Enum):
    MAJOR = 0
    MINOR = 1
    PATCH = 2


def get_next_version(version: str, version_type: VersionType) -> str:
    new_version = version.split(".")
    part_to_increase = new_version[version_type.value]
    if "-" in part_to_increase:
        part_to_increase = int(part_to_increase.split("-")[0])
    for i in range(version_type.value, 3):
        new_version[i] = "0"
    new_version[version_type.value] = str(int(part_to_increase) + 1)
    return ".".join(new_version)


def get_version_type(version: str) -> VersionType:
    if version.endswith("0.0"):
        version_type = VersionType.MAJOR
    elif version.endswith("0"):
        version_type = VersionType.MINOR
    else:
        version_type = VersionType.PATCH
    return version_type


def get_whats_new(
    version: str, add_date: bool = False, change_date: bool = False
) -> str:
    whats_new_text = FULL_WHATS_NEW_TEXT.format(version=version)
    result = [whats_new_text, "=" * len(whats_new_text)]
    if add_date and change_date:
        result += [NEW_RELEASE_DATE_MESSAGE]
    elif add_date:
        result += [RELEASE_DATE_TEXT]
    elif change_date:
        raise ValueError("Can't use change_date=True with add_date=False")
    logging.debug(
        f"version='{version}', add_date='{add_date}', change_date='{change_date}': {result}"
    )
    return "\n".join(result)


def transform_content(content: str, version: str) -> str:
    version_type = get_version_type(version)
    next_version = get_next_version(version, version_type)
    old_date = get_whats_new(version, add_date=True)
    new_date = get_whats_new(version, add_date=True, change_date=True)
    next_version_with_date = get_whats_new(next_version, add_date=True)
    do_checks(content, next_version, old_date, version, version_type)
    index = content.find(old_date)
    logging.debug(f"Replacing\n'{old_date}'\nby\n'{new_date}'\n")
    content = content.replace(old_date, new_date)
    end_content = content[index:]
    content = content[:index]
    logging.debug(f"Adding:\n'{next_version_with_date}'\n")
    content += next_version_with_date + "\n" * 4 + end_content
    return content


def do_checks(content, next_version, old_date, version, version_type):
    err = "in the changelog, fix that first!"
    NEW_VERSION_ERROR_MSG = (
        "The text for this version '{version}' did not exists %s" % err
    )
    NEXT_VERSION_ERROR_MSG = (
        "The text for the next version '{version}' already exists %s" % err
    )
    wn_next_version = get_whats_new(next_version)
    wn_this_version = get_whats_new(version)
    # There is only one field where the release date is TBA
    if version_type in [VersionType.MAJOR, VersionType.MINOR]:
        assert (
            content.count(RELEASE_DATE_TEXT) <= 1
        ), f"There should be only one release date 'TBA' ({version}) {err}"
    else:
        next_minor_version = get_next_version(version, VersionType.MINOR)
        assert (
            content.count(RELEASE_DATE_TEXT) <= 2
        ), f"There should be only two release dates 'TBA' ({version} and {next_minor_version}) {err}"
    # There is already a release note for the version we want to release
    assert content.count(wn_this_version) == 1, NEW_VERSION_ERROR_MSG.format(
        version=version
    )
    # There is no release notes for the next version
    assert content.count(wn_next_version) == 0, NEXT_VERSION_ERROR_MSG.format(
        version=next_version
    )


if __name__ == "__main__":
    main()
