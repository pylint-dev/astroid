# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt
"""Regression test for AttributeError in namedtuple brain with dotted annotation target.

See https://github.com/pylint-dev/astroid/issues/3257
"""

import astroid
from astroid import extract_node


def test_namedtuple_dotted_annotation_target_no_crash() -> None:
    """Inferring a NamedTuple subclass with a dotted annotation target should not crash."""
    code = """
    from typing import NamedTuple

    class C(NamedTuple):
        a.b: str

    C()
    """
    node = extract_node(code)
    # The last expression is ``C()`` — inferring it triggers the namedtuple brain.
    call_node = node if not isinstance(node, list) else node[-1]
    # Should not raise AttributeError: 'AssignAttr' object has no attribute 'name'
    results = list(call_node.infer())
    assert results is not None
