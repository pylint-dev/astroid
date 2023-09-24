# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import enum
import sys

PY38 = sys.version_info[:2] == (3, 8)
PY39_PLUS = sys.version_info >= (3, 9)
PY310_PLUS = sys.version_info >= (3, 10)
PY311_PLUS = sys.version_info >= (3, 11)
PY312_PLUS = sys.version_info >= (3, 12)

WIN32 = sys.platform == "win32"

IS_PYPY = sys.implementation.name == "pypy"
IS_JYTHON = sys.implementation.name == "jython"

# pylint: disable-next=no-member
PYPY_7_3_11_PLUS = IS_PYPY and sys.pypy_version_info >= (7, 3, 11)  # type: ignore[attr-defined]


class Context(enum.Enum):
    Load = 1
    Store = 2
    Del = 3


_EMPTY_OBJECT_MARKER = object()
