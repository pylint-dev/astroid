# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import extract_node, nodes
from astroid.brain.helpers import is_class_var


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            """
            from typing import ClassVar

            foo: ClassVar[int]
            """,
            id="from-import",
        ),
        pytest.param(
            """
            from typing import ClassVar

            foo: ClassVar
            """,
            id="bare-classvar",
        ),
        pytest.param(
            """
            import typing

            foo: typing.ClassVar[int]
            """,
            id="module-import",
        ),
    ],
)
def test_is_class_var_returns_true(code):
    node = extract_node(code)
    assert isinstance(node, nodes.AnnAssign)
    assert is_class_var(node.annotation)


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            """
            from typing import Final

            foo: Final[int]
            """,
            id="wrong-name",
        ),
        pytest.param(
            """
            from typing import ClassVar

            foo: list[ClassVar[int]]
            """,
            id="classvar-not-outermost",
        ),
        pytest.param(
            """
            from typing import ClassVar
            ClassVar = int

            foo: ClassVar
            """,
            id="shadowed-name",
        ),
        pytest.param(
            """
            foo: ClassVar[int]
            """,
            id="missing-import",
        ),
    ],
)
def test_is_class_var_returns_false(code):
    node = extract_node(code)
    assert isinstance(node, nodes.AnnAssign)
    assert not is_class_var(node.annotation)
