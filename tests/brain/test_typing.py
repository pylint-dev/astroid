# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import bases, builder, nodes, util
from astroid.const import PY312_PLUS
from astroid.context import InferenceContext
from astroid.exceptions import AttributeInferenceError


@pytest.mark.skipif(not PY312_PLUS, reason="The type statement was added in 3.12")
def test_type_alias_name_is_typealiastype() -> None:
    """The name bound by a ``type`` statement is a ``TypeAliasType``, not the value.

    Regression test for: https://github.com/pylint-dev/pylint/issues/10091
    """
    nodes_ = builder.extract_node("""
    type Alias = str
    type Pair[T] = tuple[T, T]
    Alias #@
    Pair[int] #@
    Alias | None #@
    None | Alias #@
    """)
    for node in nodes_:
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], bases.Instance)
        assert inferred[0].qname() == "typing.TypeAliasType"

    instance = nodes_[0].inferred()[0]
    for attr in ("__value__", "__type_params__", "__name__", "__module__"):
        assert instance.getattr(attr)
    with pytest.raises(AttributeInferenceError):
        instance.getattr("upper")


@pytest.mark.skipif(not PY312_PLUS, reason="The type statement was added in 3.12")
@pytest.mark.parametrize(
    "subscript, expected_name",
    [
        ("Container[Alias]", "Container"),
        ("list[Alias]", "list"),
        ("dict[str, Alias]", "dict"),
    ],
)
def test_class_subscripted_with_type_alias(subscript: str, expected_name: str) -> None:
    node = builder.extract_node(f"""
    from typing import Generic, TypeVar
    T = TypeVar("T")
    class Container(Generic[T]): ...
    type Alias = str
    {subscript} #@
    """)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.ClassDef)
    assert inferred[0].name == expected_name


class TestTypingAlias:

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

    @pytest.mark.parametrize("type_var_arg", ["1", "True"])
    def test_infer_typing_alias_subscriptable(self, type_var_arg: str) -> None:
        """Test that _alias() with a positive integer adds __class_getitem__.

        ``True`` counts as ``1`` at runtime, so ``_alias(list, True)[int]`` works.
        """
        node = builder.extract_node(f"""
            from typing import _alias
            x = _alias(int, {type_var_arg})
            """)
        assert isinstance(node, nodes.Assign)
        assert isinstance(node.value, nodes.Call)
        inferred = next(node.value.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert "__class_getitem__" in inferred.locals

    @pytest.mark.parametrize(
        "type_var_arg",
        [
            '"foo"',
            "None",
            'b"bar"',
            "False",
            "-1",
            "0",
        ],
    )
    def test_infer_typing_alias_non_subscriptable_argument(
        self, type_var_arg: str
    ) -> None:
        """Regression test for: https://github.com/pylint-dev/astroid/issues/3389

        Test that _alias() with a non-integer or non-positive second argument
        does not crash with TypeError during inference.
        """
        node = builder.extract_node(f"""
            from typing import _alias
            x = _alias(int, {type_var_arg})
            """)
        assert isinstance(node, nodes.Assign)
        assert isinstance(node.value, nodes.Call)
        inferred = next(node.value.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert inferred.name == "x"
        assert len(inferred.bases) == 1
        assert inferred.bases[0].name == "int"
        assert "__class_getitem__" not in inferred.locals


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
        "code,base",
        [
            (
                "import collections.abc\n"
                "class _CallableType: ...\n"
                "Callable = _CallableType(collections.abc.Callable, 2)",
                "_collections_abc.Callable",
            ),
            ("class _TupleType: ...\nTuple = _TupleType(tuple, -1)", "builtins.tuple"),
        ],
    )
    def test_special_alias_uninferable_aliased_class(
        self, code: str, base: str
    ) -> None:
        """
        Regression test for: https://github.com/pylint-dev/astroid/issues/3366

        If the aliased class is uninferable because the inference budget of the
        context is exhausted, no class must be built: a later inference with a
        fresh context must still get the aliased class as a base.
        """
        assign = builder.extract_node(code)
        ctx = InferenceContext()
        ctx.nodes_inferred = ctx.max_inferred + 1
        assert next(assign.value.infer(context=ctx)) is util.Uninferable

        inferred = next(assign.value.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert [ancestor.qname() for ancestor in inferred.ancestors()] == [
            base,
            "builtins.object",
        ]
