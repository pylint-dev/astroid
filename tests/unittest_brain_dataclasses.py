import pytest

import astroid
from astroid import bases, nodes
from astroid.const import PY37_PLUS
from astroid.exceptions import InferenceError

if not PY37_PLUS:
    pytest.skip("Dataclasses were added in 3.7", allow_module_level=True)


def test_inference_attribute_no_default():
    """Test inference of dataclass attribute with no default.

    Note that the argument to the constructor is ignored by the inference.
    """
    klass, instance = astroid.extract_node(
        """
    from dataclasses import dataclass

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


def test_inference_non_field_default():
    """Test inference of dataclass attribute with a non-field default."""
    klass, instance = astroid.extract_node(
        """
    from dataclasses import dataclass

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


def test_inference_field_default():
    """Test inference of dataclass attribute with a field call default
    (default keyword argument given)."""
    klass, instance = astroid.extract_node(
        """
    from dataclasses import dataclass, field

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


def test_inference_field_default_factory():
    """Test inference of dataclass attribute with a field call default
    (default_factory keyword argument given)."""
    klass, instance = astroid.extract_node(
        """
    from dataclasses import dataclass, field

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


def test_inference_method():
    """Test inference of dataclass attribute within a method,
    with a default_factory field.

    Based on https://github.com/PyCQA/pylint/issues/2600
    """
    node = astroid.extract_node(
        """
    from typing import Dict
    from dataclasses import dataclass, field

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


def test_inference_no_annotation():
    """Test that class variables without type annotations are not
    turned into instance attributes.
    """
    class_def, klass, instance = astroid.extract_node(
        """
    from dataclasses import dataclass

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

    # Both the class and instance can still access the attribute
    for node in [klass, instance]:
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == "hi"


def test_inference_class_var():
    """Test that class variables with a ClassVar type annotations are not
    turned into instance attributes.
    """
    class_def, klass, instance = astroid.extract_node(
        """
    from dataclasses import dataclass
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

    # Both the class and instance can still access the attribute
    for node in [klass, instance]:
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == "hi"


def test_inference_init_var():
    """Test that class variables with InitVar type annotations are not
    turned into instance attributes.
    """
    class_def, klass, instance = astroid.extract_node(
        """
    from dataclasses import dataclass, InitVar

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

    # Both the class and instance can still access the attribute
    for node in [klass, instance]:
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == "hi"
