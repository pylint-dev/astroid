# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

import astroid
from astroid import bases, nodes
from astroid.const import PY310_PLUS
from astroid.exceptions import InferenceError
from astroid.util import Uninferable

parametrize_module = pytest.mark.parametrize(
    ("module",), (["dataclasses"], ["pydantic.dataclasses"], ["marshmallow_dataclass"])
)


@parametrize_module
def test_inference_attribute_no_default(module: str):
    """Test inference of dataclass attribute with no default.

    Note that the argument to the constructor is ignored by the inference.
    """
    klass, instance = astroid.extract_node(
        f"""
    from {module} import dataclass

    @dataclass
    class A:
        name: str

    A.name  #@
    A('hi').name  #@
    """
    )
    with pytest.raises(InferenceError):
        klass.inferred()

    inferred = instance.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0].name == "str"


@parametrize_module
def test_inference_non_field_default(module: str):
    """Test inference of dataclass attribute with a non-field default."""
    klass, instance = astroid.extract_node(
        f"""
    from {module} import dataclass

    @dataclass
    class A:
        name: str = 'hi'

    A.name  #@
    A().name  #@
    """
    )
    inferred = klass.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hi"

    inferred = instance.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hi"

    assert isinstance(inferred[1], bases.Instance)
    assert inferred[1].name == "str"


@parametrize_module
def test_inference_field_default(module: str):
    """Test inference of dataclass attribute with a field call default
    (default keyword argument given).
    """
    klass, instance = astroid.extract_node(
        f"""
    from {module} import dataclass
    from dataclasses import field

    @dataclass
    class A:
        name: str = field(default='hi')

    A.name  #@
    A().name  #@
    """
    )
    inferred = klass.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hi"

    inferred = instance.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hi"

    assert isinstance(inferred[1], bases.Instance)
    assert inferred[1].name == "str"


@parametrize_module
def test_inference_field_default_factory(module: str):
    """Test inference of dataclass attribute with a field call default
    (default_factory keyword argument given).
    """
    klass, instance = astroid.extract_node(
        f"""
    from {module} import dataclass
    from dataclasses import field

    @dataclass
    class A:
        name: list = field(default_factory=list)

    A.name  #@
    A().name  #@
    """
    )
    inferred = klass.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.List)
    assert inferred[0].elts == []

    inferred = instance.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.List)
    assert inferred[0].elts == []

    assert isinstance(inferred[1], bases.Instance)
    assert inferred[1].name == "list"


@parametrize_module
def test_inference_method(module: str):
    """Test inference of dataclass attribute within a method,
    with a default_factory field.

    Based on https://github.com/pylint-dev/pylint/issues/2600
    """
    node = astroid.extract_node(
        f"""
    from typing import Dict
    from {module} import dataclass
    from dataclasses import field

    @dataclass
    class TestClass:
        foo: str
        bar: str
        baz_dict: Dict[str, str] = field(default_factory=dict)

        def some_func(self) -> None:
            f = self.baz_dict.items  #@
            for key, value in f():
                print(key)
                print(value)
    """
    )
    inferred = next(node.value.infer())
    assert isinstance(inferred, bases.BoundMethod)


@parametrize_module
def test_inference_no_annotation(module: str):
    """Test that class variables without type annotations are not
    turned into instance attributes.
    """
    class_def, klass, instance = astroid.extract_node(
        f"""
    from {module} import dataclass

    @dataclass
    class A:
        name = 'hi'

    A  #@
    A.name  #@
    A().name #@
    """
    )
    inferred = next(class_def.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert inferred.instance_attrs == {}
    assert inferred.is_dataclass

    # Both the class and instance can still access the attribute
    for node in (klass, instance):
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == "hi"


@parametrize_module
def test_inference_class_var(module: str):
    """Test that class variables with a ClassVar type annotations are not
    turned into instance attributes.
    """
    class_def, klass, instance = astroid.extract_node(
        f"""
    from {module} import dataclass
    from typing import ClassVar

    @dataclass
    class A:
        name: ClassVar[str] = 'hi'

    A #@
    A.name  #@
    A().name #@
    """
    )
    inferred = next(class_def.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert inferred.instance_attrs == {}
    assert inferred.is_dataclass

    # Both the class and instance can still access the attribute
    for node in (klass, instance):
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == "hi"


@parametrize_module
def test_inference_init_var(module: str):
    """Test that class variables with InitVar type annotations are not
    turned into instance attributes.
    """
    class_def, klass, instance = astroid.extract_node(
        f"""
    from {module} import dataclass
    from dataclasses import InitVar

    @dataclass
    class A:
        name: InitVar[str] = 'hi'

    A  #@
    A.name  #@
    A().name #@
    """
    )
    inferred = next(class_def.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert inferred.instance_attrs == {}
    assert inferred.is_dataclass

    # Both the class and instance can still access the attribute
    for node in (klass, instance):
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == "hi"


@parametrize_module
def test_inference_generic_collection_attribute(module: str):
    """Test that an attribute with a generic collection type from the
    typing module is inferred correctly.
    """
    attr_nodes = astroid.extract_node(
        f"""
    from {module} import dataclass
    from dataclasses import field
    import typing

    @dataclass
    class A:
        dict_prop: typing.Dict[str, str]
        frozenset_prop: typing.FrozenSet[str]
        list_prop: typing.List[str]
        set_prop: typing.Set[str]
        tuple_prop: typing.Tuple[int, str]

    a = A({{}}, frozenset(), [], set(), (1, 'hi'))
    a.dict_prop       #@
    a.frozenset_prop  #@
    a.list_prop       #@
    a.set_prop        #@
    a.tuple_prop      #@
    """
    )
    names = (
        "Dict",
        "FrozenSet",
        "List",
        "Set",
        "Tuple",
    )
    for node, name in zip(attr_nodes, names):
        inferred = next(node.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.name == name


@pytest.mark.parametrize(
    ("module", "typing_module"),
    [
        ("dataclasses", "typing"),
        ("pydantic.dataclasses", "typing"),
        ("pydantic.dataclasses", "collections.abc"),
        ("marshmallow_dataclass", "typing"),
        ("marshmallow_dataclass", "collections.abc"),
    ],
)
def test_inference_callable_attribute(module: str, typing_module: str):
    """Test that an attribute with a Callable annotation is inferred as Uninferable.

    See issue #1129 and pylint-dev/pylint#4895
    """
    instance = astroid.extract_node(
        f"""
    from {module} import dataclass
    from {typing_module} import Any, Callable

    @dataclass
    class A:
        enabled: Callable[[Any], bool]

    A(lambda x: x == 42).enabled  #@
    """
    )
    inferred = next(instance.infer())
    assert inferred is Uninferable


@parametrize_module
def test_inference_inherited(module: str):
    """Test that an attribute is inherited from a superclass dataclass."""
    klass1, instance1, klass2, instance2 = astroid.extract_node(
        f"""
    from {module} import dataclass

    @dataclass
    class A:
        value: int
        name: str = "hi"

    @dataclass
    class B(A):
        new_attr: bool = True

    B.value  #@
    B(1).value  #@
    B.name  #@
    B(1).name  #@
    """
    )
    with pytest.raises(InferenceError):  # B.value is not defined
        klass1.inferred()

    inferred = instance1.inferred()
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0].name == "int"

    inferred = klass2.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hi"

    inferred = instance2.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hi"
    assert isinstance(inferred[1], bases.Instance)
    assert inferred[1].name == "str"


def test_dataclass_order_of_inherited_attributes():
    """Test that an attribute in a child does not get put at the end of the init."""
    child, normal, keyword_only = astroid.extract_node(
        """
    from dataclass import dataclass


    @dataclass
    class Parent:
        a: str
        b: str


    @dataclass
    class Child(Parent):
        c: str
        a: str


    @dataclass(kw_only=True)
    class KeywordOnlyParent:
        a: int
        b: str


    @dataclass
    class NormalChild(KeywordOnlyParent):
        c: str
        a: str


    @dataclass(kw_only=True)
    class KeywordOnlyChild(KeywordOnlyParent):
        c: str
        a: str


    Child.__init__  #@
    NormalChild.__init__  #@
    KeywordOnlyChild.__init__  #@
    """
    )
    child_init: bases.UnboundMethod = next(child.infer())
    assert [a.name for a in child_init.args.args] == ["self", "a", "b", "c"]

    normal_init: bases.UnboundMethod = next(normal.infer())
    if PY310_PLUS:
        assert [a.name for a in normal_init.args.args] == ["self", "a", "c"]
        assert [a.name for a in normal_init.args.kwonlyargs] == ["b"]
    else:
        assert [a.name for a in normal_init.args.args] == ["self", "a", "b", "c"]
        assert [a.name for a in normal_init.args.kwonlyargs] == []

    keyword_only_init: bases.UnboundMethod = next(keyword_only.infer())
    if PY310_PLUS:
        assert [a.name for a in keyword_only_init.args.args] == ["self"]
        assert [a.name for a in keyword_only_init.args.kwonlyargs] == ["a", "b", "c"]
    else:
        assert [a.name for a in keyword_only_init.args.args] == ["self", "a", "b", "c"]


def test_pydantic_field() -> None:
    """Test that pydantic.Field attributes are currently Uninferable.

    (Eventually, we can extend the brain to support pydantic.Field)
    """
    klass, instance = astroid.extract_node(
        """
    from pydantic import Field
    from pydantic.dataclasses import dataclass

    @dataclass
    class A:
        name: str = Field("hi")

    A.name  #@
    A().name #@
    """
    )

    inferred = klass.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = instance.inferred()
    assert len(inferred) == 2
    assert inferred[0] is Uninferable
    assert isinstance(inferred[1], bases.Instance)
    assert inferred[1].name == "str"


@parametrize_module
def test_init_empty(module: str):
    """Test init for a dataclass with no attributes."""
    node = astroid.extract_node(
        f"""
    from {module} import dataclass

    @dataclass
    class A:
        pass

    A.__init__  #@
    """
    )
    init = next(node.infer())
    assert [a.name for a in init.args.args] == ["self"]


@parametrize_module
def test_init_no_defaults(module: str):
    """Test init for a dataclass with attributes and no defaults."""
    node = astroid.extract_node(
        f"""
    from {module} import dataclass
    from typing import List

    @dataclass
    class A:
        x: int
        y: str
        z: List[bool]

    A.__init__  #@
    """
    )
    init = next(node.infer())
    assert [a.name for a in init.args.args] == ["self", "x", "y", "z"]
    assert [a.as_string() if a else None for a in init.args.annotations] == [
        None,
        "int",
        "str",
        "List[bool]",
    ]


@parametrize_module
def test_init_defaults(module: str):
    """Test init for a dataclass with attributes and some defaults."""
    node = astroid.extract_node(
        f"""
    from {module} import dataclass
    from dataclasses import field
    from typing import List

    @dataclass
    class A:
        w: int
        x: int = 10
        y: str = field(default="hi")
        z: List[bool] = field(default_factory=list)

    A.__init__  #@
    """
    )
    init = next(node.infer())
    assert [a.name for a in init.args.args] == ["self", "w", "x", "y", "z"]
    assert [a.as_string() if a else None for a in init.args.annotations] == [
        None,
        "int",
        "int",
        "str",
        "List[bool]",
    ]
    assert [a.as_string() if a else None for a in init.args.defaults] == [
        "10",
        "'hi'",
        "_HAS_DEFAULT_FACTORY",
    ]


@parametrize_module
def test_init_initvar(module: str):
    """Test init for a dataclass with attributes and an InitVar."""
    node = astroid.extract_node(
        f"""
    from {module} import dataclass
    from dataclasses import InitVar
    from typing import List

    @dataclass
    class A:
        x: int
        y: str
        init_var: InitVar[int]
        z: List[bool]

    A.__init__  #@
    """
    )
    init = next(node.infer())
    assert [a.name for a in init.args.args] == ["self", "x", "y", "init_var", "z"]
    assert [a.as_string() if a else None for a in init.args.annotations] == [
        None,
        "int",
        "str",
        "int",
        "List[bool]",
    ]


@parametrize_module
def test_init_decorator_init_false(module: str):
    """Test that no init is generated when init=False is passed to
    dataclass decorator.
    """
    node = astroid.extract_node(
        f"""
    from {module} import dataclass
    from typing import List

    @dataclass(init=False)
    class A:
        x: int
        y: str
        z: List[bool]

    A.__init__ #@
    """
    )
    init = next(node.infer())
    assert init._proxied.parent.name == "object"


@parametrize_module
def test_init_field_init_false(module: str):
    """Test init for a dataclass with attributes with a field value where init=False
    (these attributes should not be included in the initializer).
    """
    node = astroid.extract_node(
        f"""
    from {module} import dataclass
    from dataclasses import field
    from typing import List

    @dataclass
    class A:
        x: int
        y: str
        z: List[bool] = field(init=False)

    A.__init__  #@
    """
    )
    init = next(node.infer())
    assert [a.name for a in init.args.args] == ["self", "x", "y"]
    assert [a.as_string() if a else None for a in init.args.annotations] == [
        None,
        "int",
        "str",
    ]


@parametrize_module
def test_init_override(module: str):
    """Test init for a dataclass overrides a superclass initializer.

    Based on https://github.com/pylint-dev/pylint/issues/3201
    """
    node = astroid.extract_node(
        f"""
    from {module} import dataclass
    from typing import List

    class A:
        arg0: str = None

        def __init__(self, arg0):
            raise NotImplementedError

    @dataclass
    class B(A):
        arg1: int = None
        arg2: str = None

    B.__init__  #@
    """
    )
    init = next(node.infer())
    assert [a.name for a in init.args.args] == ["self", "arg1", "arg2"]
    assert [a.as_string() if a else None for a in init.args.annotations] == [
        None,
        "int",
        "str",
    ]


@parametrize_module
def test_init_attributes_from_superclasses(module: str):
    """Test init for a dataclass that inherits and overrides attributes from
    superclasses.

    Based on https://github.com/pylint-dev/pylint/issues/3201
    """
    node = astroid.extract_node(
        f"""
    from {module} import dataclass
    from typing import List

    @dataclass
    class A:
        arg0: float
        arg2: str

    @dataclass
    class B(A):
        arg1: int
        arg2: list  # Overrides arg2 from A

    B.__init__  #@
    """
    )
    init = next(node.infer())
    assert [a.name for a in init.args.args] == ["self", "arg0", "arg2", "arg1"]
    assert [a.as_string() if a else None for a in init.args.annotations] == [
        None,
        "float",
        "list",  # not str
        "int",
    ]


@parametrize_module
def test_invalid_init(module: str):
    """Test that astroid doesn't generate an initializer when attribute order is
    invalid.
    """
    node = astroid.extract_node(
        f"""
    from {module} import dataclass

    @dataclass
    class A:
        arg1: float = 0.0
        arg2: str

    A.__init__  #@
    """
    )
    init = next(node.infer())
    assert init._proxied.parent.name == "object"


@parametrize_module
def test_annotated_enclosed_field_call(module: str):
    """Test inference of dataclass attribute with a field call in another function
    call.
    """
    node = astroid.extract_node(
        f"""
    from {module} import dataclass, field
    from typing import cast

    @dataclass
    class A:
        attribute: int = cast(int, field(default_factory=dict))
    """
    )
    inferred = node.inferred()
    assert len(inferred) == 1 and isinstance(inferred[0], nodes.ClassDef)
    assert "attribute" in inferred[0].instance_attrs
    assert inferred[0].is_dataclass


@parametrize_module
def test_invalid_field_call(module: str) -> None:
    """Test inference of invalid field call doesn't crash."""
    code = astroid.extract_node(
        f"""
    from {module} import dataclass, field

    @dataclass
    class A:
        val: field()
    """
    )
    inferred = code.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.ClassDef)
    assert inferred[0].is_dataclass


def test_non_dataclass_is_not_dataclass() -> None:
    """Test that something that isn't a dataclass has the correct attribute."""
    module = astroid.parse(
        """
    class A:
        val: field()

    def dataclass():
        return

    @dataclass
    class B:
        val: field()
    """
    )
    class_a = module.body[0].inferred()
    assert len(class_a) == 1
    assert isinstance(class_a[0], nodes.ClassDef)
    assert not class_a[0].is_dataclass

    class_b = module.body[2].inferred()
    assert len(class_b) == 1
    assert isinstance(class_b[0], nodes.ClassDef)
    assert not class_b[0].is_dataclass


def test_kw_only_sentinel() -> None:
    """Test that the KW_ONLY sentinel doesn't get added to the fields."""
    node_one, node_two = astroid.extract_node(
        """
    from dataclasses import dataclass, KW_ONLY
    from dataclasses import KW_ONLY as keyword_only

    @dataclass
    class A:
        _: KW_ONLY
        y: str

    A.__init__  #@

    @dataclass
    class B:
        _: keyword_only
        y: str

    B.__init__  #@
    """
    )
    if PY310_PLUS:
        expected = ["self", "y"]
    else:
        expected = ["self", "_", "y"]
    init = next(node_one.infer())
    assert [a.name for a in init.args.args] == expected

    init = next(node_two.infer())
    assert [a.name for a in init.args.args] == expected


def test_kw_only_decorator() -> None:
    """Test that we update the signature correctly based on the keyword.

    kw_only was introduced in PY310.
    """
    foodef, bardef, cee, dee = astroid.extract_node(
        """
    from dataclasses import dataclass

    @dataclass(kw_only=True)
    class Foo:
        a: int
        e: str


    @dataclass(kw_only=False)
    class Bar(Foo):
        c: int


    @dataclass(kw_only=False)
    class Cee(Bar):
        d: int


    @dataclass(kw_only=True)
    class Dee(Cee):
        ee: int


    Foo.__init__  #@
    Bar.__init__  #@
    Cee.__init__  #@
    Dee.__init__  #@
    """
    )

    foo_init: bases.UnboundMethod = next(foodef.infer())
    if PY310_PLUS:
        assert [a.name for a in foo_init.args.args] == ["self"]
        assert [a.name for a in foo_init.args.kwonlyargs] == ["a", "e"]
    else:
        assert [a.name for a in foo_init.args.args] == ["self", "a", "e"]
        assert [a.name for a in foo_init.args.kwonlyargs] == []

    bar_init: bases.UnboundMethod = next(bardef.infer())
    if PY310_PLUS:
        assert [a.name for a in bar_init.args.args] == ["self", "c"]
        assert [a.name for a in bar_init.args.kwonlyargs] == ["a", "e"]
    else:
        assert [a.name for a in bar_init.args.args] == ["self", "a", "e", "c"]
        assert [a.name for a in bar_init.args.kwonlyargs] == []

    cee_init: bases.UnboundMethod = next(cee.infer())
    if PY310_PLUS:
        assert [a.name for a in cee_init.args.args] == ["self", "c", "d"]
        assert [a.name for a in cee_init.args.kwonlyargs] == ["a", "e"]
    else:
        assert [a.name for a in cee_init.args.args] == ["self", "a", "e", "c", "d"]
        assert [a.name for a in cee_init.args.kwonlyargs] == []

    dee_init: bases.UnboundMethod = next(dee.infer())
    if PY310_PLUS:
        assert [a.name for a in dee_init.args.args] == ["self", "c", "d"]
        assert [a.name for a in dee_init.args.kwonlyargs] == ["a", "e", "ee"]
    else:
        assert [a.name for a in dee_init.args.args] == [
            "self",
            "a",
            "e",
            "c",
            "d",
            "ee",
        ]
        assert [a.name for a in dee_init.args.kwonlyargs] == []


def test_kw_only_in_field_call() -> None:
    """Test that keyword only fields get correctly put at the end of the __init__."""

    first, second, third = astroid.extract_node(
        """
    from dataclasses import dataclass, field

    @dataclass
    class Parent:
        p1: int = field(kw_only=True, default=0)

    @dataclass
    class Child(Parent):
        c1: str

    @dataclass(kw_only=True)
    class GrandChild(Child):
        p2: int = field(kw_only=False, default=1)
        p3: int = field(kw_only=True, default=2)

    Parent.__init__  #@
    Child.__init__ #@
    GrandChild.__init__ #@
    """
    )

    first_init: bases.UnboundMethod = next(first.infer())
    assert [a.name for a in first_init.args.args] == ["self"]
    assert [a.name for a in first_init.args.kwonlyargs] == ["p1"]
    assert [d.value for d in first_init.args.kw_defaults] == [0]

    second_init: bases.UnboundMethod = next(second.infer())
    assert [a.name for a in second_init.args.args] == ["self", "c1"]
    assert [a.name for a in second_init.args.kwonlyargs] == ["p1"]
    assert [d.value for d in second_init.args.kw_defaults] == [0]

    third_init: bases.UnboundMethod = next(third.infer())
    assert [a.name for a in third_init.args.args] == ["self", "c1", "p2"]
    assert [a.name for a in third_init.args.kwonlyargs] == ["p1", "p3"]
    assert [d.value for d in third_init.args.defaults] == [1]
    assert [d.value for d in third_init.args.kw_defaults] == [0, 2]


def test_dataclass_with_unknown_base() -> None:
    """Regression test for dataclasses with unknown base classes.

    Reported in https://github.com/pylint-dev/pylint/issues/7418
    """
    node = astroid.extract_node(
        """
    import dataclasses

    from unknown import Unknown


    @dataclasses.dataclass
    class MyDataclass(Unknown):
        pass

    MyDataclass()
    """
    )

    assert next(node.infer())


def test_dataclass_with_unknown_typing() -> None:
    """Regression test for dataclasses with unknown base classes.

    Reported in https://github.com/pylint-dev/pylint/issues/7422
    """
    node = astroid.extract_node(
        """
    from dataclasses import dataclass, InitVar


    @dataclass
    class TestClass:
        '''Test Class'''

        config: InitVar = None

    TestClass.__init__  #@
    """
    )

    init_def: bases.UnboundMethod = next(node.infer())
    assert [a.name for a in init_def.args.args] == ["self", "config"]


def test_dataclass_with_default_factory() -> None:
    """Regression test for dataclasses with default values.

    Reported in https://github.com/pylint-dev/pylint/issues/7425
    """
    bad_node, good_node = astroid.extract_node(
        """
    from dataclasses import dataclass
    from typing import Union

    @dataclass
    class BadExampleParentClass:
        xyz: Union[str, int]

    @dataclass
    class BadExampleClass(BadExampleParentClass):
        xyz: str = ""

    BadExampleClass.__init__  #@

    @dataclass
    class GoodExampleParentClass:
        xyz: str

    @dataclass
    class GoodExampleClass(GoodExampleParentClass):
        xyz: str = ""

    GoodExampleClass.__init__  #@
    """
    )

    bad_init: bases.UnboundMethod = next(bad_node.infer())
    assert bad_init.args.defaults
    assert [a.name for a in bad_init.args.args] == ["self", "xyz"]

    good_init: bases.UnboundMethod = next(good_node.infer())
    assert bad_init.args.defaults
    assert [a.name for a in good_init.args.args] == ["self", "xyz"]


def test_dataclass_with_multiple_inheritance() -> None:
    """Regression test for dataclasses with multiple inheritance.

    Reported in https://github.com/pylint-dev/pylint/issues/7427
    Reported in https://github.com/pylint-dev/pylint/issues/7434
    """
    first, second, overwritten, overwriting, mixed = astroid.extract_node(
        """
    from dataclasses import dataclass

    @dataclass
    class BaseParent:
        _abc: int = 1

    @dataclass
    class AnotherParent:
        ef: int = 2

    @dataclass
    class FirstChild(BaseParent, AnotherParent):
        ghi: int = 3

    @dataclass
    class ConvolutedParent(AnotherParent):
        '''Convoluted Parent'''

    @dataclass
    class SecondChild(BaseParent, ConvolutedParent):
        jkl: int = 4

    @dataclass
    class OverwritingParent:
        ef: str = "2"

    @dataclass
    class OverwrittenChild(OverwritingParent, AnotherParent):
        '''Overwritten Child'''

    @dataclass
    class OverwritingChild(BaseParent, AnotherParent):
        _abc: float = 1.0
        ef: float = 2.0

    class NotADataclassParent:
        ef: int = 2

    @dataclass
    class ChildWithMixedParents(BaseParent, NotADataclassParent):
        ghi: int = 3

    FirstChild.__init__  #@
    SecondChild.__init__  #@
    OverwrittenChild.__init__  #@
    OverwritingChild.__init__  #@
    ChildWithMixedParents.__init__  #@
    """
    )

    first_init: bases.UnboundMethod = next(first.infer())
    assert [a.name for a in first_init.args.args] == ["self", "ef", "_abc", "ghi"]
    assert [a.value for a in first_init.args.defaults] == [2, 1, 3]

    second_init: bases.UnboundMethod = next(second.infer())
    assert [a.name for a in second_init.args.args] == ["self", "ef", "_abc", "jkl"]
    assert [a.value for a in second_init.args.defaults] == [2, 1, 4]

    overwritten_init: bases.UnboundMethod = next(overwritten.infer())
    assert [a.name for a in overwritten_init.args.args] == ["self", "ef"]
    assert [a.value for a in overwritten_init.args.defaults] == ["2"]

    overwriting_init: bases.UnboundMethod = next(overwriting.infer())
    assert [a.name for a in overwriting_init.args.args] == ["self", "ef", "_abc"]
    assert [a.value for a in overwriting_init.args.defaults] == [2.0, 1.0]

    mixed_init: bases.UnboundMethod = next(mixed.infer())
    assert [a.name for a in mixed_init.args.args] == ["self", "_abc", "ghi"]
    assert [a.value for a in mixed_init.args.defaults] == [1, 3]

    first = astroid.extract_node(
        """
    from dataclasses import dataclass

    @dataclass
    class BaseParent:
        required: bool

    @dataclass
    class FirstChild(BaseParent):
        ...

    @dataclass
    class SecondChild(BaseParent):
        optional: bool = False

    @dataclass
    class GrandChild(FirstChild, SecondChild):
        ...

    GrandChild.__init__  #@
    """
    )

    first_init: bases.UnboundMethod = next(first.infer())
    assert [a.name for a in first_init.args.args] == ["self", "required", "optional"]
    assert [a.value for a in first_init.args.defaults] == [False]


@pytest.mark.xfail(reason="Transforms returning Uninferable isn't supported.")
def test_dataclass_non_default_argument_after_default() -> None:
    """Test that a non-default argument after a default argument is not allowed.

    This should succeed, but the dataclass brain is a transform
    which currently can't return an Uninferable correctly. Therefore, we can't
    set the dataclass ClassDef node to be Uninferable currently.
    Eventually it can be merged into test_dataclass_with_multiple_inheritance.
    """

    impossible = astroid.extract_node(
        """
    from dataclasses import dataclass

    @dataclass
    class BaseParent:
        required: bool

    @dataclass
    class FirstChild(BaseParent):
        ...

    @dataclass
    class SecondChild(BaseParent):
        optional: bool = False

    @dataclass
    class ThirdChild:
        other: bool = False

    @dataclass
    class ImpossibleGrandChild(FirstChild, SecondChild, ThirdChild):
        ...

    ImpossibleGrandChild() #@
    """
    )

    assert next(impossible.infer()) is Uninferable


def test_dataclass_with_field_init_is_false() -> None:
    """When init=False it shouldn't end up in the __init__."""
    first, second, second_child, third_child, third = astroid.extract_node(
        """
    from dataclasses import dataclass, field


    @dataclass
    class First:
        a: int

    @dataclass
    class Second(First):
        a: int = field(init=False, default=1)

    @dataclass
    class SecondChild(Second):
        a: float

    @dataclass
    class ThirdChild(SecondChild):
        a: str

    @dataclass
    class Third(First):
        a: str

    First.__init__  #@
    Second.__init__  #@
    SecondChild.__init__  #@
    ThirdChild.__init__  #@
    Third.__init__  #@
    """
    )

    first_init: bases.UnboundMethod = next(first.infer())
    assert [a.name for a in first_init.args.args] == ["self", "a"]
    assert [a.value for a in first_init.args.defaults] == []

    second_init: bases.UnboundMethod = next(second.infer())
    assert [a.name for a in second_init.args.args] == ["self"]
    assert [a.value for a in second_init.args.defaults] == []

    second_child_init: bases.UnboundMethod = next(second_child.infer())
    assert [a.name for a in second_child_init.args.args] == ["self", "a"]
    assert [a.value for a in second_child_init.args.defaults] == [1]

    third_child_init: bases.UnboundMethod = next(third_child.infer())
    assert [a.name for a in third_child_init.args.args] == ["self", "a"]
    assert [a.value for a in third_child_init.args.defaults] == [1]

    third_init: bases.UnboundMethod = next(third.infer())
    assert [a.name for a in third_init.args.args] == ["self", "a"]
    assert [a.value for a in third_init.args.defaults] == []


def test_dataclass_inits_of_non_dataclasses() -> None:
    """Regression test for __init__ mangling for non dataclasses.

    Regression test against changes tested in test_dataclass_with_multiple_inheritance
    """
    first, second, third = astroid.extract_node(
        """
    from dataclasses import dataclass

    @dataclass
    class DataclassParent:
        _abc: int = 1


    class NotADataclassParent:
        ef: int = 2


    class FirstChild(DataclassParent, NotADataclassParent):
        ghi: int = 3


    class SecondChild(DataclassParent, NotADataclassParent):
        ghi: int = 3

        def __init__(self, ef: int = 3):
            self.ef = ef


    class ThirdChild(NotADataclassParent, DataclassParent):
        ghi: int = 3

        def __init__(self, ef: int = 3):
            self.ef = ef

    FirstChild.__init__  #@
    SecondChild.__init__  #@
    ThirdChild.__init__  #@
    """
    )

    first_init: bases.UnboundMethod = next(first.infer())
    assert [a.name for a in first_init.args.args] == ["self", "_abc"]
    assert [a.value for a in first_init.args.defaults] == [1]

    second_init: bases.UnboundMethod = next(second.infer())
    assert [a.name for a in second_init.args.args] == ["self", "ef"]
    assert [a.value for a in second_init.args.defaults] == [3]

    third_init: bases.UnboundMethod = next(third.infer())
    assert [a.name for a in third_init.args.args] == ["self", "ef"]
    assert [a.value for a in third_init.args.defaults] == [3]


def test_dataclass_with_properties() -> None:
    """Tests for __init__ creation for dataclasses that use properties."""
    first, second, third = astroid.extract_node(
        """
    from dataclasses import dataclass

    @dataclass
    class Dataclass:
        attr: int

        @property
        def attr(self) -> int:
            return 1

        @attr.setter
        def attr(self, value: int) -> None:
            pass

    class ParentOne(Dataclass):
        '''Docstring'''

    @dataclass
    class ParentTwo(Dataclass):
        '''Docstring'''

    Dataclass.__init__  #@
    ParentOne.__init__  #@
    ParentTwo.__init__  #@
    """
    )

    first_init: bases.UnboundMethod = next(first.infer())
    assert [a.name for a in first_init.args.args] == ["self", "attr"]
    assert [a.value for a in first_init.args.defaults] == [1]

    second_init: bases.UnboundMethod = next(second.infer())
    assert [a.name for a in second_init.args.args] == ["self", "attr"]
    assert [a.value for a in second_init.args.defaults] == [1]

    third_init: bases.UnboundMethod = next(third.infer())
    assert [a.name for a in third_init.args.args] == ["self", "attr"]
    assert [a.value for a in third_init.args.defaults] == [1]

    fourth = astroid.extract_node(
        """
    from dataclasses import dataclass

    @dataclass
    class Dataclass:
        other_attr: str
        attr: str

        @property
        def attr(self) -> str:
            return self.other_attr[-1]

        @attr.setter
        def attr(self, value: int) -> None:
            pass

    Dataclass.__init__  #@
    """
    )

    fourth_init: bases.UnboundMethod = next(fourth.infer())
    assert [a.name for a in fourth_init.args.args] == ["self", "other_attr", "attr"]
    assert [a.name for a in fourth_init.args.defaults] == ["Uninferable"]
