# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the orjson module extender without importing its native extension."""

from __future__ import annotations

import pytest

from astroid import MANAGER, extract_node, nodes, parse, util
from astroid.exceptions import AttributeInferenceError


@pytest.fixture(name="orjson_module")
def _orjson_module(monkeypatch: pytest.MonkeyPatch) -> nodes.Module:
    module = nodes.Module("orjson")
    module.postinit(body=[], doc_node=None)
    MANAGER.visit_transforms(module)
    monkeypatch.setitem(MANAGER.astroid_cache, "orjson", module)
    return module


@pytest.mark.usefixtures("orjson_module")
@pytest.mark.parametrize(
    "imports, name",
    [
        ("import orjson", "orjson.dumps"),
        ("import orjson as json", "json.dumps"),
        ("from orjson import dumps", "dumps"),
        ("from orjson import dumps as encode", "encode"),
    ],
)
@pytest.mark.parametrize(
    "arguments", ["[2]", "[2], None, 0", "[2], default=str, option=0"]
)
def test_dumps_returns_bytes(imports: str, name: str, arguments: str) -> None:
    node = extract_node(f"{imports}\n{name}({arguments})")
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.pytype() == "builtins.bytes"


@pytest.mark.usefixtures("orjson_module")
@pytest.mark.parametrize(
    "imports, name",
    [
        ("import orjson", "orjson.loads"),
        ("import orjson as json", "json.loads"),
        ("from orjson import loads", "loads"),
        ("from orjson import loads as decode", "decode"),
    ],
)
@pytest.mark.parametrize("argument", ['b"[2]"', '"{}"', '"null"'])
def test_loads_result_is_unknown(imports: str, name: str, argument: str) -> None:
    node = extract_node(f"{imports}\n{name}({argument})")
    assert isinstance(next(node.func.infer()), nodes.FunctionDef)
    assert list(node.infer()) == [util.Uninferable]


@pytest.mark.parametrize(
    "name, signature",
    [("dumps", "obj, /, default=None, option=None"), ("loads", "obj, /")],
)
def test_function_signatures(
    orjson_module: nodes.Module, name: str, signature: str
) -> None:
    function = orjson_module[name]
    assert isinstance(function, nodes.FunctionDef)
    assert function.args.format_args() == signature
    assert function.parent is orjson_module


def test_missing_attribute(orjson_module: nodes.Module) -> None:
    with pytest.raises(AttributeInferenceError):
        orjson_module.getattr("not_a_real_member")


def test_other_modules_are_unchanged() -> None:
    module = parse("", module_name="unrelated_module")
    assert "dumps" not in module
    assert "loads" not in module
