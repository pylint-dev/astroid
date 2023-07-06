# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

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
