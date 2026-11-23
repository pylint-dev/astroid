# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt


import astroid
from astroid import bases
from astroid.const import PY313


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
