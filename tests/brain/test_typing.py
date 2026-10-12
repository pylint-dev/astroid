# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import bases, builder, nodes
from astroid.const import PY312_PLUS, PY314_PLUS
from astroid.exceptions import AttributeInferenceError


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


@pytest.mark.skipif(not PY312_PLUS, reason="The type statement was added in 3.12")
def test_instantiate_class_subscripted_with_type_alias() -> None:
    node = builder.extract_node("""
    from typing import Generic, TypeVar
    T = TypeVar("T")
    class Container(Generic[T]): ...
    type Alias = str
    Container[Alias]() #@
    """)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0].qname() == ".Container"


@pytest.mark.skipif(not PY312_PLUS, reason="The type statement was added in 3.12")
def test_type_alias_parameters() -> None:
    node = builder.extract_node("""
    type Pair[T] = tuple[T, T]
    Pair #@
    """)
    assert node.inferred()[0].getattr("__parameters__")


@pytest.mark.skipif(not PY312_PLUS, reason="The type statement was added in 3.12")
def test_type_alias_evaluate_value() -> None:
    node = builder.extract_node("""
    type Alias = str
    Alias #@
    """)
    instance = node.inferred()[0]
    if PY314_PLUS:
        assert instance.getattr("evaluate_value")
    else:
        with pytest.raises(AttributeInferenceError):
            instance.getattr("evaluate_value")


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
