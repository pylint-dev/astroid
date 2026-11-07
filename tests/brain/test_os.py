# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import inspect
import os

import pytest

from astroid import MANAGER, extract_node, nodes


@pytest.mark.parametrize(
    "import_statement, walk",
    [("import os", "os.walk"), ("from os import walk", "walk")],
)
def test_os_walk(import_statement: str, walk: str) -> None:
    """``os.walk()`` yields a str and two lists."""
    dirpath, dirnames, filenames = extract_node(f"""
    {import_statement}
    for dirpath, dirnames, filenames in {walk}(".", topdown=True):
        dirpath  #@
        dirnames  #@
        filenames  #@
    """)
    inferred = dirpath.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].pytype() == "builtins.str"
    for node in (dirnames, filenames):
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.List)


@pytest.mark.parametrize(
    "top, pytypes",
    [
        pytest.param('b"."', {"builtins.bytes"}, id="bytes"),
        pytest.param('pathlib.Path(".")', {"builtins.str"}, id="path"),
        pytest.param("top", {"builtins.str", "builtins.bytes"}, id="unknown"),
    ],
)
def test_os_walk_path_type(top: str, pytypes: set[str]) -> None:
    """Like in ``os.walk()``, the path is bytes if ``top`` is bytes."""
    dirpath = extract_node(f"""
    import os
    import pathlib

    def walk(top):
        for dirpath, dirnames, filenames in os.walk({top}):
            dirpath  #@
    """)
    assert {inferred.pytype() for inferred in dirpath.inferred()} == pytypes


def test_os_walk_same_list() -> None:
    """All uses of ``dirnames`` infer to the same list.

    pylint relies on this to report ``modified-iterating-list`` when a loop over
    ``dirnames`` removes from it.
    """
    modified, iterated = extract_node("""
    import os
    for dirpath, dirnames, filenames in os.walk("."):
        for dirname in __(dirnames):
            dirnames.remove(dirname)  #@
    """)
    inferred = iterated.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.List)
    assert modified.func.expr.inferred()[0] is inferred[0]


def test_os_walk_inference_order() -> None:
    """Inferring ``dirpath`` first does not make ``dirnames`` uninferable.

    ``dirpath`` depends on ``top``, which can be expensive to infer.
    """
    dirpath, dirnames = extract_node("""
    import os

    def walk(base):
        for dirpath, dirnames, filenames in os.walk(os.path.join(base, "locale")):
            dirpath  #@
            dirnames  #@
    """)
    dirpath.inferred()
    inferred = dirnames.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.List)


def test_os_walk_signature() -> None:
    walk = MANAGER.ast_from_module_name("os")["walk"]
    assert f"({walk.args.as_string()})" == str(inspect.signature(os.walk))
