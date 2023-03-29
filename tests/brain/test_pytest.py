# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from astroid import builder


def test_pytest() -> None:
    ast_node = builder.extract_node(
        """
    import pytest
    pytest #@
    """
    )
    module = next(ast_node.infer())
    attrs = [
        "deprecated_call",
        "warns",
        "exit",
        "fail",
        "skip",
        "importorskip",
        "xfail",
        "mark",
        "raises",
        "freeze_includes",
        "set_trace",
        "fixture",
        "yield_fixture",
    ]
    for attr in attrs:
        assert attr in module
