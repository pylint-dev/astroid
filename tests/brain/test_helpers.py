# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from unittest import mock

import pytest

from astroid import extract_node, nodes
from astroid.brain import helpers as brain_helpers
from astroid.brain.helpers import is_class_var
from astroid.manager import AstroidManager


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


def test_load_brain_skips_already_registered_brain() -> None:
    """``_load_brain`` is a no-op for a brain that is already registered.

    This guard keeps a brain reachable through several module triggers
    (e.g. ``brain_namedtuple_enum`` via ``collections``/``enum``/``typing``)
    from registering its transforms more than once.
    """
    manager = AstroidManager()
    brain_helpers._load_brain(manager, "brain_argparse")
    assert "brain_argparse" in brain_helpers._loaded_brain_names

    # A second load must early-return without re-importing or re-registering.
    with mock.patch("astroid.brain.brain_argparse.register") as register:
        brain_helpers._load_brain(manager, "brain_argparse")
    register.assert_not_called()
