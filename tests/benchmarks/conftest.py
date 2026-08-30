# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Skip the benchmark suite when ``pytest-codspeed`` is not installed.

The ``benchmark`` fixture used by every test in this directory is provided
by the ``pytest-codspeed`` plugin. CI installs it explicitly in the
CodSpeed workflow, but contributors running ``pytest tests/`` locally will
not have it. Without this guard pytest would error out with
``fixture 'benchmark' not found`` (and, because ``filterwarnings = "error"``
is set in ``pyproject.toml``, even a warning would abort collection).
"""

try:
    import pytest_codspeed  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    collect_ignore_glob = ["test_bench_*.py"]
