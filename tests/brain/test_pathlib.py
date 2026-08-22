# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt


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


def test_inference_parents_subscript_index_assigned() -> None:
    """Test inference of ``pathlib.Path.parents``, accessed by index after
    the ``.parents`` result was first assigned to a variable.
    """
    path = astroid.extract_node(
        """
    from pathlib import Path

    current_path = Path().resolve()
    parents = current_path.parents
    parents[2]  #@
    """
    )

    inferred = path.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    if PY313_PLUS:
        assert inferred[0].qname() == "pathlib._local.Path"
    else:
        assert inferred[0].qname() == "pathlib.Path"


def test_inference_parents_subscript_slice_assigned() -> None:
    """Test inference of ``pathlib.Path.parents``, accessed by slice after
    the ``.parents`` result was first assigned to a variable.
    """
    name_node = astroid.extract_node(
        """
    from pathlib import Path

    current_path = Path().resolve()
    parents = current_path.parents
    parent_path = parents[:2]
    parent_path
    """
    )
    inferred = name_node.inferred()
    assert len(inferred) == 1
    if PY310_PLUS:
        assert isinstance(inferred[0], bases.Instance)
        assert inferred[0].qname() == "builtins.tuple"
    else:
        assert inferred[0] is Uninferable


def test_inference_parents_subscript_assigned_ambiguous() -> None:
    """Test a variable ambiguously assigned from ``.parents`` in one branch
    and a plain tuple in another is not incorrectly inferred as ``Path``.
    """
    name_node = astroid.extract_node(
        """
    from pathlib import Path

    current_path = Path().resolve()
    if current_path:
        parents = current_path.parents
    else:
        parents = (1, 2, 3)
    parents[0]  #@
    """
    )
    inferred = name_node.inferred()
    assert len(inferred) == 2
    qnames = {getattr(value, "qname", lambda: None)() for value in inferred}
    assert qnames == {"builtins.tuple", "builtins.int"}


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
