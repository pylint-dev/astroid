import pytest

import astroid
from astroid import bases
from astroid.const import PY310_PLUS


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
    inferred = next(name_node.infer())
    assert isinstance(inferred, bases.Instance)
    assert inferred.qname() == "pathlib.Path"


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
    inferred = next(name_node.infer())
    assert isinstance(inferred, bases.Instance)
    assert inferred.qname() == "builtins.tuple"
