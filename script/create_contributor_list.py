# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from pathlib import Path

from contributors_txt import create_contributors_txt

CWD = Path(".").absolute()
ASTROID_BASE_DIRECTORY = Path(__file__).parent.parent.absolute()
ALIASES_FILE = (
    ASTROID_BASE_DIRECTORY / "script/.contributors_aliases.json"
).relative_to(CWD)
DEFAULT_CONTRIBUTOR_PATH = (ASTROID_BASE_DIRECTORY / "CONTRIBUTORS.txt").relative_to(
    CWD
)


def main():
    create_contributors_txt(
        aliases_file=ALIASES_FILE, output=DEFAULT_CONTRIBUTOR_PATH, verbose=True
    )


if __name__ == "__main__":
    main()
