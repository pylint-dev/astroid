# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import extract_node, parse
from astroid.const import PY312_PLUS, PY313_PLUS
from astroid.nodes import (
    AssignName,
    List,
    Name,
    ParamSpec,
    Subscript,
    Tuple,
    TypeAlias,
    TypeParamScope,
    TypeVar,
    TypeVarTuple,
)

if not PY312_PLUS:
    pytest.skip("Requires Python 3.12 or higher", allow_module_level=True)


def test_type_alias() -> None:
    node = extract_node("type Point[T] = list[float, float]")
    assert isinstance(node, TypeAlias)
    assert isinstance(node.type_params[0], TypeVar)
    assert isinstance(node.type_params[0].name, AssignName)
    assert node.type_params[0].name.name == "T"
    assert node.type_params[0].bound is None
    assert node.type_params[0].default_value is None

    assert isinstance(node.value, Subscript)
    assert node.value.value.name == "list"
    assert node.value.slice.name == "tuple"
    assert all(elt.name == "float" for elt in node.value.slice.elts)

    assert node.inferred()[0] is node
    assert node.type_params[0].inferred()[0] is node.type_params[0]

    assert node.statement() is node

    assigned = next(node.assigned_stmts())
    assert assigned is node.value


def test_type_var() -> None:
    node = extract_node("type Point[T: int] = T")
    param = node.type_params[0]
    assert isinstance(param, TypeVar)
    assert isinstance(param.bound, Name)
    assert param.bound.name == "int"
    assert param.default_value is None


@pytest.mark.skipif(not PY313_PLUS, reason="Type parameter defaults were added in 313")
def test_type_var_defaults() -> None:
    node = extract_node("type Point[T: int = int] = T")
    param = node.type_params[0]
    assert isinstance(param, TypeVar)
    assert isinstance(param.bound, Name)
    assert param.bound.name == "int"
    assert isinstance(param.default_value, Name)
    assert param.default_value.name == "int"


def test_type_param_spec() -> None:
    node = extract_node("type Alias[**P] = Callable[P, int]")
    params = node.type_params[0]
    assert isinstance(params, ParamSpec)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "P"
    assert params.default_value is None

    assert node.inferred()[0] is node


@pytest.mark.skipif(not PY313_PLUS, reason="Type parameter defaults were added in 313")
def test_type_param_spec_defaults() -> None:
    node = extract_node("type Alias[**P = [int, str]] = Callable[P, int]")
    params = node.type_params[0]
    assert isinstance(params, ParamSpec)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "P"
    assert isinstance(params.default_value, List)
    assert len(params.default_value.elts) == 2

    assert node.inferred()[0] is node


def test_type_var_tuple() -> None:
    node = extract_node("type Alias[*Ts] = tuple[*Ts]")
    params = node.type_params[0]
    assert isinstance(params, TypeVarTuple)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "Ts"
    assert params.default_value is None

    assert node.inferred()[0] is node


@pytest.mark.skipif(not PY313_PLUS, reason="Type parameter defaults were added in 313")
def test_type_var_tuple_defaults() -> None:
    node = extract_node("type Alias[*Ts = tuple[int, str]] = tuple[*Ts]")
    params = node.type_params[0]
    assert isinstance(params, TypeVarTuple)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "Ts"
    assert isinstance(params.default_value, Subscript)
    assert isinstance(params.default_value.value, Name)
    assert params.default_value.value.name == "tuple"
    assert isinstance(params.default_value.slice, Tuple)
    assert len(params.default_value.slice.elts) == 2

    assert node.inferred()[0] is node


def test_type_param() -> None:
    func_node = extract_node("def func[T]() -> T: ...")
    assert isinstance(func_node.type_params[0], TypeVar)
    assert func_node.type_params[0].name.name == "T"
    assert func_node.type_params[0].bound is None

    class_node = extract_node("class MyClass[T]: ...")
    assert isinstance(class_node.type_params[0], TypeVar)
    assert class_node.type_params[0].name.name == "T"
    assert class_node.type_params[0].bound is None


def test_get_children() -> None:
    func_node = extract_node("def func[T]() -> T: ...")
    func_children = tuple(func_node.get_children())
    assert isinstance(func_children[2], TypeVar)

    class_node = extract_node("class MyClass[T]: ...")
    class_children = tuple(class_node.get_children())
    assert isinstance(class_children[0], TypeVar)


def test_type_param_bound_forward_reference_class() -> None:
    """A type parameter bound may forward-reference a later class.

    Regression test for the pylint false ``used-before-assignment``.
    """
    module = parse("""
        class Basket[T: Fruit]:
            value: T

        class Fruit:
            pass
        """)
    bound = module.body[0].type_params[0].bound
    assert bound.lookup("Fruit")[1] == [module.body[1]]


def test_type_param_bound_forward_reference_is_inferable() -> None:
    """Inferring a forward-referencing bound raised NameInferenceError."""
    module = parse("""
        class Basket[T: Fruit]:
            value: T

        class Fruit:
            pass
        """)
    bound = module.body[0].type_params[0].bound
    assert list(bound.infer()) == [module.body[1]]


def test_type_param_bound_forward_reference_function() -> None:
    module = parse("""
        def func[T: Fruit](x: T) -> T:
            return x

        class Fruit:
            pass
        """)
    bound = module.body[0].type_params[0].bound
    assert bound.lookup("Fruit")[1] == [module.body[1]]


def test_type_param_bound_sibling_reference() -> None:
    for code in ("class C[T, U: T]: ...", "def f[T, U: T](): ..."):
        node = extract_node(code)
        assert node.type_params[1].bound.lookup("T")[1] == [node.type_params[0].name]


def test_type_param_still_registered_in_owner_locals() -> None:
    """Type parameter names stay in the locals they were in before the scope.

    ``TypeParamScope`` is what lookups go through, but the names are still
    registered in the owner's ``locals`` (and in the enclosing scope's
    ``locals`` for a type alias) for backwards compatibility: tools that build
    their own scope model out of ``locals`` -- pylint's variables checker does
    -- only learn about type parameters that way.
    """
    class_node = extract_node("class C[T]: ...")
    assert class_node.locals["T"] == [class_node.type_params[0].name]

    func_node = extract_node("def f[T](): ...")
    assert func_node.locals["T"] == [func_node.type_params[0].name]

    module = parse("type Alias[T] = list[T]")
    alias = module.body[0]
    assert module.locals["T"] == [alias.type_params[0].name]


def test_type_param_is_not_made_global_by_a_global_statement() -> None:
    """``global T`` in the body does not make the type parameter a global.

    It declares the module's ``T`` for the body only, so the type parameter is
    still bound in its own scope and not in the module's locals.
    """
    for code in ("def f[T]():\n    global T", "class C[T]:\n    global T"):
        module = parse(code)
        owner = module.body[0]
        assert owner.type_param_scope.locals["T"] == [owner.type_params[0].name]
        assert "T" not in module.locals


def test_type_param_bound_resolves_enclosing_class_type_param() -> None:
    """A bound may reference the type parameter of an enclosing generic class.

    The enclosing class body is skipped when walking out of the scope, but its
    own type parameters stay visible.
    """
    module = parse("""
        class Outer[T]:
            class Inner[U: T]: ...
            def meth[V: T](self) -> None: ...
        """)
    outer = module.body[0]
    outer_t = outer.type_params[0].name
    assert outer.body[0].type_params[0].bound.lookup("T")[1] == [outer_t]
    assert outer.body[1].type_params[0].bound.lookup("T")[1] == [outer_t]


def test_type_param_bound_resolves_past_non_generic_class() -> None:
    """Enclosing classes without type parameters are walked past."""
    module = parse("""
        class Plain:
            class Basket[T: Fruit]: ...

        class Fruit: ...
        """)
    bound = module.body[0].body[0].type_params[0].bound
    assert bound.lookup("Fruit")[1] == [module.body[1]]


def test_type_param_bound_resolves_through_enclosing_function() -> None:
    """A bound not defined in the nearest scope is resolved by that scope."""
    module = parse("""
        Fruit = object

        def outer():
            class Basket[T: Fruit]: ...
            return Basket
        """)
    bound = module.body[1].body[0].type_params[0].bound
    assert bound.lookup("Fruit")[1] == [module.body[0].targets[0]]


def test_type_param_visible_in_method_body() -> None:
    module = parse("""
        class C[T]:
            def meth(self) -> T:
                ...
        """)
    returns = module.body[0].body[0].returns
    assert returns.lookup("T")[1] == [module.body[0].type_params[0].name]


def test_type_param_bound_resolves_outer_name() -> None:
    module = parse("""
        X = int
        class C[T: X]: ...
        """)
    bound = module.body[1].type_params[0].bound
    assert bound.lookup("X")[1] == [module.body[0].targets[0]]


def test_type_alias_forward_reference_and_value() -> None:
    module = parse("""
        type Alias[T: Fruit] = list[T]

        class Fruit:
            pass
        """)
    alias = module.body[0]
    assert alias.type_params[0].bound.lookup("Fruit")[1] == [module.body[1]]
    # The value is evaluated in the type parameter scope, so ``T`` resolves.
    assert alias.value.slice.lookup("T")[1] == [alias.type_params[0].name]
    assert isinstance(alias.type_params[0].scope(), TypeParamScope)


def test_type_param_scope_and_frame() -> None:
    cls = extract_node("class C[T]: ...")
    type_var = cls.type_params[0]
    assert isinstance(cls.type_param_scope, TypeParamScope)
    assert type_var.scope() is cls.type_param_scope
    # The scope is not a frame; it is transparent for frames and qnames.
    assert type_var.frame() is cls
    assert cls.type_param_scope.qname() == cls.qname()


def test_type_param_scope_qname_of_type_alias() -> None:
    """A type alias is not a scope, so the enclosing scope answers for it.

    ``TypeAlias.qname()`` reports the runtime type (``typing.TypeAliasType``),
    which is not a scope path, so it cannot be delegated to.
    """
    module = parse(
        """
        type Alias[T] = list[T]
        class C[U]:
            type Nested[V] = list[V]
        """,
        "mymod",
    )
    assert module.body[0].type_param_scope.qname() == "mymod"
    cls = module.body[1]
    assert cls.body[0].type_param_scope.qname() == "mymod.C"
    # The alias value's scope is the type parameter scope; its qname is
    # unchanged from when the value was parented to the enclosing scope.
    assert module.body[0].value.scope().qname() == "mymod"


def test_type_param_scope_as_string() -> None:
    """The scope prints as the bracketed type parameter list it spans."""
    cls = extract_node("class C[T: int, *Ts, **P]: ...")
    assert cls.type_param_scope.as_string() == "[T: int, *Ts, **P]"


def test_type_param_scope_is_not_in_the_visitable_tree() -> None:
    """The scope is reachable as a parent, but nothing yields it as a child."""
    module = parse("class C[T]: ...")
    cls = module.body[0]
    assert cls.type_params[0].parent is cls.type_param_scope
    assert not list(module.nodes_of_class(TypeParamScope))
    assert list(cls.type_param_scope.get_children()) == cls.type_params
    # ``type_params`` is in ``_astroid_fields``, so it must be assignable.
    cls.type_param_scope.type_params = []
    assert cls.type_params == []


@pytest.mark.skipif(not PY313_PLUS, reason="Requires Python 3.13 or higher")
def test_type_param_default_forward_reference() -> None:
    module = parse("""
        class C[T = Fruit]: ...

        class Fruit:
            pass
        """)
    default = module.body[0].type_params[0].default_value
    assert default.lookup("Fruit")[1] == [module.body[1]]
