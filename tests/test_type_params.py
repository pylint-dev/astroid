# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import extract_node
from astroid.const import PY312_PLUS
from astroid.nodes import Subscript, TypeAlias, TypeVar


@pytest.mark.skipif(not PY312_PLUS, reason="Requires Python 3.12 or higher")
def test_type_alias() -> None:
    node = extract_node("type Point[T] = list[float, float]")
    assert isinstance(node, TypeAlias)
    assert isinstance(node.type_params[0], TypeVar)
    assert node.type_params[0].name == "T"
    assert node.type_params[0].bound is None

    assert isinstance(node.value, Subscript)
    assert node.value.value.name == "list"
    assert node.value.slice.name == "tuple"
    assert all(elt.name == "float" for elt in node.value.slice.elts)


@pytest.mark.skipif(not PY312_PLUS, reason="Requires Python 3.12 or higher")
def test_type_param() -> None:
    func_node = extract_node("def func[T]() -> T: ...")
    assert isinstance(func_node.type_params[0], TypeVar)
    assert func_node.type_params[0].name == "T"
    assert func_node.type_params[0].bound is None

    class_node = extract_node("class MyClass[T]: ...")
    assert isinstance(class_node.type_params[0], TypeVar)
    assert class_node.type_params[0].name == "T"
    assert class_node.type_params[0].bound is None
