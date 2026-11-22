# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Test finalization of suspended attribute inference iterators."""

import sys
from unittest.mock import Mock

import pytest

from astroid import Uninferable, bases, extract_node
from astroid.exceptions import AttributeInferenceError
from astroid.nodes.node_classes import _infer_attribute


@pytest.mark.parametrize("layer", ["attribute", "instance", "descriptor"])
def test_attribute_inference_finalized_during_inner_cleanup(layer, monkeypatch):
    owner = bases.Instance(extract_node("class Owner: pass"))
    retained = []
    errors = []

    def attributes():
        try:
            yield Uninferable
        finally:
            retained.clear()

    inner = attributes()
    if layer == "attribute":
        node = extract_node("instance.value")
        monkeypatch.setattr(node.expr, "infer", Mock(return_value=iter([owner])))
        monkeypatch.setattr(owner, "igetattr", Mock(return_value=inner))
        outer = _infer_attribute(node)
    elif layer == "instance":
        monkeypatch.setattr(owner, "getattr", Mock(return_value=[]))
        monkeypatch.setattr(bases, "_infer_stmts", Mock(return_value=inner))
        outer = owner.igetattr("value")
    else:
        monkeypatch.setattr(
            owner, "getattr", Mock(side_effect=AttributeInferenceError())
        )
        monkeypatch.setattr(owner._proxied, "igetattr", Mock(return_value=[]))
        monkeypatch.setattr(owner, "_wrap_attr", Mock(return_value=inner))
        outer = owner.igetattr("value")

    assert next(outer) is Uninferable
    retained.append(outer)
    del outer
    monkeypatch.setattr(sys, "unraisablehook", errors.append)
    inner.close()

    assert not errors
    assert not retained
