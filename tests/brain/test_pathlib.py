# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt


import pytest

import astroid
from astroid import bases
from astroid.const import PY313
from astroid.util import Uninferable


def test_inference_parents() -> None:
    """Test inference of ``pathlib.Path.parents``."""
    name_node = astroid.extract_node("""
    from pathlib import Path

    current_path = Path().resolve()
    path_parents = current_path.parents
    path_parents
    """)
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    if PY313:
        assert inferred[0].qname() == "builtins.tuple"
    else:
        assert inferred[0].qname() == "pathlib._PathParents"


def test_inference_parents_subscript_index() -> None:
    """Test inference of ``pathlib.Path.parents``, accessed by index."""
    path = astroid.extract_node("""
    from pathlib import Path

    current_path = Path().resolve()
    current_path.parents[2]  #@
    """)

    inferred = path.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    if PY313:
        assert inferred[0].qname() == "pathlib._local.Path"
    else:
        assert inferred[0].qname() == "pathlib.Path"


@pytest.mark.parametrize(
    "index", [":2", ":", "1:5:2", "::-1", "slice(None, 2)", "selection"]
)
def test_inference_parents_subscript_slice(index: str) -> None:
    """Test inference of ``pathlib.Path.parents``, accessed by slice."""
    name_node = astroid.extract_node(f"""
    from pathlib import Path

    current_path = Path().resolve()
    selection = slice(None, 2)
    parent_path = current_path.parents[{index}]
    parent_path
    """)
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0].qname() == "builtins.tuple"


def test_inference_parents_subscript_not_path() -> None:
    """Test inference of other ``.parents`` subscripts is unaffected."""
    name_node = astroid.extract_node("""
    class A:
        parents = 42

    c = A()
    error = c.parents[:2]
    error
    """)
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_inference_parents_subscript_other_instance() -> None:
    """A custom parents attribute still infers every possible return value."""
    node = astroid.extract_node("""
    class Parents:
        def __getitem__(self, index):
            if index:
                return 42
            return None

    class CustomPath:
        parents = Parents()

    CustomPath().parents[:2]
    """)
    assert [value.value for value in node.inferred()] == [42, None]
