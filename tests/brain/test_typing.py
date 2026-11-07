# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import bases, builder, nodes
from astroid.context import InferenceContext


def test_infer_typevar() -> None:
    """
    Regression test for: https://github.com/pylint-dev/pylint/issues/8802

    Test that an inferred `typing.TypeVar()` call produces a `nodes.ClassDef`
    node.
    """
    call_node = builder.extract_node("""
    from typing import TypeVar
    TypeVar('My.Type')
    """)
    inferred = next(call_node.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert inferred.name == "My.Type"


def test_infer_typevar_name_injection() -> None:
    """A crafted TypeVar name must not be spliced into the synthesized class."""
    call_node = builder.extract_node("""
    from typing import TypeVar
    TypeVar('T(EvilBase): #')
    """)
    inferred = next(call_node.infer())
    assert isinstance(inferred, nodes.ClassDef)
    # The name is kept verbatim instead of parsed, so no base is injected.
    assert inferred.name == "T(EvilBase): #"
    assert inferred.bases == []


class TestTypingAlias:
    def test_infer_typing_alias(self) -> None:
        """
        Test that _alias() calls can be inferred.
        """
        node = builder.extract_node("""
            from typing import _alias
            x = _alias(int, float)
            """)
        assert isinstance(node, nodes.Assign)
        assert isinstance(node.value, nodes.Call)
        inferred = next(node.value.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert len(inferred.bases) == 1
        assert inferred.bases[0].name == "int"

    @pytest.mark.parametrize(
        "alias_args",
        [
            "",  # two missing arguments
            "int",  # one missing argument
            "int, float, tuple",  # one additional argument
        ],
    )
    def test_infer_typing_alias_incorrect_number_of_arguments(
        self, alias_args: str
    ) -> None:
        """
        Regression test for: https://github.com/pylint-dev/astroid/issues/2513

        Test that _alias() calls with the incorrect number of arguments can be inferred.
        """
        node = builder.extract_node(f"""
            from typing import _alias
            x = _alias({alias_args})
            """)
        assert isinstance(node, nodes.Assign)
        assert isinstance(node.value, nodes.Call)
        inferred = next(node.value.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.name == "_SpecialGenericAlias"


class TestSpecialAlias:
    @pytest.mark.parametrize(
        "code",
        [
            "_CallableType()",
            "_TupleType()",
        ],
    )
    def test_special_alias_no_crash_on_empty_args(self, code: str) -> None:
        """
        Regression test for: https://github.com/pylint-dev/astroid/issues/2772

        Test that _CallableType() and _TupleType() calls with no arguments
        do not cause an IndexError.
        """
        # Should not raise IndexError
        module = builder.parse(code)
        assert isinstance(module, nodes.Module)

    @pytest.mark.parametrize(
        "code",
        [
            "import collections.abc\nCallable = _CallableType(collections.abc.Callable, 2)",
            "Tuple = _TupleType(tuple, -1)",
        ],
    )
    def test_special_alias_uninferable_aliased_class(self, code: str) -> None:
        """
        Regression test for: https://github.com/pylint-dev/astroid/issues/3366

        If the aliased class is uninferable, e.g. because the inference budget
        of the context is exhausted, it must not end up in the bases of the
        new class.
        """
        assign = builder.extract_node(code)
        ctx = InferenceContext()
        ctx.nodes_inferred = ctx.max_inferred + 1
        inferred = next(assign.value.infer(context=ctx))
        assert isinstance(inferred, nodes.ClassDef)
        assert not inferred.bases
        assert [anc.qname() for anc in inferred.ancestors()] == ["builtins.object"]
