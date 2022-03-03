# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/graphs/contributors
import pytest

import astroid
from astroid import bases, nodes
from astroid.const import PY37_PLUS
from astroid.exceptions import InferenceError
from astroid.util import Uninferable

if not PY37_PLUS:
    pytest.skip("Dataclasses were added in 3.7", allow_module_level=True)


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
    (default keyword argument given)."""
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
    (default_factory keyword argument given)."""
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

    Based on https://github.com/PyCQA/pylint/issues/2600
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

    See issue #1129 and PyCQA/pylint#4895
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
    """Test init for a dataclass with no attributes"""
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
    """Test init for a dataclass with attributes and no defaults"""
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
    """Test init for a dataclass with attributes and some defaults"""
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
    """Test init for a dataclass with attributes and an InitVar"""
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

    Based on https://github.com/PyCQA/pylint/issues/3201
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
    """Test init for a dataclass that inherits and overrides attributes from superclasses.

    Based on https://github.com/PyCQA/pylint/issues/3201
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
    """Test that astroid doesn't generate an initializer when attribute order is invalid."""
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
    """Test inference of dataclass attribute with a field call in another function call"""
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
