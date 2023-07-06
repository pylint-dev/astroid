import pytest

from astroid import builder, nodes


def test_infer_typevar() -> None:
    """
    Regression test for: https://github.com/pylint-dev/pylint/issues/8802

    Test that an inferred `typing.TypeVar()` call produces a `nodes.ClassDef`
    node.
    """
    assign_node = builder.extract_node(
        """
    from typing import TypeVar
    MyType = TypeVar('My.Type')
    """
    )
    call = assign_node.value
    inferred = next(call.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert inferred.name == "My.Type"
