# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt


import astroid
from astroid import bases, nodes
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


def test_inference_parents_subscript_slice() -> None:
    """Test inference of ``pathlib.Path.parents``, accessed by slice."""
    name_node = astroid.extract_node("""
    from pathlib import Path

    current_path = Path().resolve()
    parent_path = current_path.parents[:2]
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


def test_inference_parents_subscript_not_path_tuple() -> None:
    """Test inference of a ``.parents`` tuple that is not a path is unaffected."""
    name_node = astroid.extract_node("""
    class A:
        parents = (1, 2)

    c = A()
    first = c.parents[0]
    first
    """)
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 1


def test_inference_parents_name_subscript_index() -> None:
    """Test inference of ``pathlib.Path.parents`` assigned to a name, by index."""
    path = astroid.extract_node("""
    from pathlib import Path

    current_path = Path().resolve()
    parents = current_path.parents
    parents[2]  #@
    """)

    inferred = path.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    if PY313:
        assert inferred[0].qname() == "pathlib._local.Path"
    else:
        assert inferred[0].qname() == "pathlib.Path"


def test_inference_parents_name_subscript_slice() -> None:
    """Test inference of ``pathlib.Path.parents`` assigned to a name, by slice."""
    name_node = astroid.extract_node("""
    from pathlib import Path

    current_path = Path().resolve()
    parents = current_path.parents
    parent_path = parents[:2]
    parent_path
    """)
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0].qname() == "builtins.tuple"


def test_inference_parents_name_subscript_not_path() -> None:
    """Test inference of other ``.parents`` names subscripted is unaffected."""
    name_node = astroid.extract_node("""
    class A:
        parents = 42

    parents = A().parents
    error = parents[:2]
    error
    """)
    inferred = name_node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable
