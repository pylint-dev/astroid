# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import textwrap

from astroid.brain.helpers import register_module_extender
from astroid.builder import AstroidBuilder
from astroid.const import PY312_PLUS
from astroid.manager import AstroidManager


def datetime_transform():
    """The datetime module was C-accelerated in Python 3.12, so we
    lack a Python source."""
    return AstroidBuilder(AstroidManager()).string_build(
        textwrap.dedent(
            """
    class date: ...
    class time: ...
    class datetime(date): ...
    class timedelta: ...
    class tzinfo: ...
    class timezone(tzinfo): ...
    """
        )
    )


if PY312_PLUS:
    register_module_extender(AstroidManager(), "datetime", datetime_transform)
