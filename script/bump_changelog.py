"""
This script permits to upgrade the changelog in astroid or pylint when releasing a version.
"""
import argparse
import enum
from datetime import datetime
from pathlib import Path

DEFAULT_CHANGELOG_PATH = Path("ChangeLog")
err = "in the changelog, fix that first!"
NEW_VERSION_ERROR_MSG = "The text for this version '{version}' did not exists %s" % err
NEXT_VERSION_ERROR_MSG = (
    "The text for the next version '{version}' already exists %s" % err
)

TODAY = datetime.now()
WHATS_NEW_TEXT = "What's New in astroid"
FULL_WHATS_NEW_TEXT = WHATS_NEW_TEXT + " {version}?"
RELEASE_DATE_TEXT = "Release Date: TBA"
NEW_RELEASE_DATE_MESSAGE = "Release Date: {}".format(TODAY.strftime("%Y-%m-%d"))


def main() -> None:
    parser = argparse.ArgumentParser(add_help=__doc__)
    parser.add_argument("version", help="The version we want to release")
    args = parser.parse_args()
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


def transform_content(content: str, version: str) -> str:
    version_type = get_version_type(version)
    next_version = get_next_version(version, version_type)
    wn_next_version = FULL_WHATS_NEW_TEXT.format(version=next_version)
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
    assert (
        content.count(FULL_WHATS_NEW_TEXT.format(version=version)) == 1
    ), NEW_VERSION_ERROR_MSG.format(version=version)
    # There is no release notes for the next version
    assert content.count(wn_next_version) == 0, NEXT_VERSION_ERROR_MSG.format(
        version=next_version
    )
    index = content.find(WHATS_NEW_TEXT)
    content = content.replace(RELEASE_DATE_TEXT, NEW_RELEASE_DATE_MESSAGE)
    end_content = content[index:]
    content = content[:index]
    content += wn_next_version + "\n"
    content += "=" * len(wn_next_version) + "\n"
    content += RELEASE_DATE_TEXT + "\n" * 4
    content += end_content
    return content


if __name__ == "__main__":
    main()
