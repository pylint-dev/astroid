# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import pytest

import astroid
from astroid import bases
from astroid.const import PY310_PLUS
from astroid.util import Uninferable

if not PY310_PLUS:
    pytest.skip(
        "The parents sequence supports slices since 3.10", allow_module_level=True
    )


def test_inference_parents_subscript_index():
    """Test inference of ``pathlib.Path.parents``, accessed by index."""
    name_node = astroid.extract_node(
        """
    from pathlib import Path

    current_path = Path().resolve()
    parent_path = current_path.parents[2]
    parent_path
    """
    )
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0].qname() == "pathlib.Path"


def test_inference_parents_subscript_slice():
    """Test inference of ``pathlib.Path.parents``, accessed by slice."""
    name_node = astroid.extract_node(
        """
    from pathlib import Path

    current_path = Path().resolve()
    parent_path = current_path.parents[:2]
    parent_path
    """
    )
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0].qname() == "builtins.tuple"


def test_inference_parents_subscript_not_path():
    """Test inference of other ``.parents`` subscripts is unaffected."""
    name_node = astroid.extract_node(
        """
    class A:
        parents = 42

    c = A()
    error = c.parents[2]
    error
    """
    )
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable
