# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
"""
Astroid hook for the dataclasses library
"""
from typing import Generator, Tuple, Union

from astroid import context, inference_tip
from astroid.builder import parse
from astroid.const import PY37_PLUS, PY39_PLUS
from astroid.exceptions import InferenceError
from astroid.manager import AstroidManager
from astroid.nodes.node_classes import (
    AnnAssign,
    AssignName,
    Attribute,
    Call,
    Name,
    NodeNG,
    Subscript,
    Unknown,
)
from astroid.nodes.scoped_nodes import ClassDef, FunctionDef
from astroid.util import Uninferable

DATACLASSES_DECORATORS = frozenset(("dataclass",))
FIELD_NAME = "field"
DATACLASS_MODULE = "dataclasses"


def is_decorated_with_dataclass(node, decorator_names=DATACLASSES_DECORATORS):
    """Return True if a decorated node has a `dataclass` decorator applied."""
    if not isinstance(node, ClassDef) or not node.decorators:
        return False

    for decorator_attribute in node.decorators.nodes:
        if isinstance(decorator_attribute, Call):  # decorator with arguments
            decorator_attribute = decorator_attribute.func

        try:
            inferred = next(decorator_attribute.infer())
        except (InferenceError, StopIteration):
            continue

        if not isinstance(inferred, FunctionDef):
            continue

        if (
            inferred.name in decorator_names
            and inferred.root().name == DATACLASS_MODULE
        ):
            return True

    return False


def dataclass_transform(node: ClassDef) -> None:
    """Rewrite a dataclass to be easily understood by pylint"""

    for assign_node in node.body:
        if not isinstance(assign_node, AnnAssign) or not isinstance(
            assign_node.target, AssignName
        ):
            continue

        if _is_class_var(assign_node.annotation) or _is_init_var(
            assign_node.annotation
        ):
            continue

        name = assign_node.target.name

        rhs_node = Unknown(
            lineno=assign_node.lineno,
            col_offset=assign_node.col_offset,
            parent=assign_node,
        )
        rhs_node = AstroidManager().visit_transforms(rhs_node)
        node.instance_attrs[name] = [rhs_node]


def infer_dataclass_attribute(
    node: Unknown, ctx: context.InferenceContext = None
) -> Generator:
    """Inference tip for an Unknown node that was dynamically generated to
    represent a dataclass attribute.

    In the case that a default value is provided, that is inferred first.
    Then, an Instance of the annotated class is yielded.
    """
    assign = node.parent
    if not isinstance(assign, AnnAssign):
        yield Uninferable
        return

    annotation, value = assign.annotation, assign.value
    if value is not None:
        yield from value.infer(context=ctx)
    if annotation is not None:
        klass = None
        try:
            klass = next(annotation.infer())
        except (InferenceError, StopIteration):
            yield Uninferable

        if not isinstance(klass, ClassDef):
            yield Uninferable
        else:
            yield klass.instantiate_class()
    else:
        yield Uninferable


def infer_dataclass_field_call(
    node: AssignName, ctx: context.InferenceContext = None
) -> Generator:
    """Inference tip for dataclass field calls."""
    field_call = node.parent.value
    result = _get_field_default(field_call)
    if result is None:
        yield Uninferable
    else:
        default_type, default = result
        if default_type == "default":
            yield from default.infer(context=ctx)
        else:
            new_call = parse(default.as_string()).body[0].value
            new_call.parent = field_call.parent
            yield from new_call.infer(context=ctx)


def _looks_like_dataclass_attribute(node: Unknown) -> bool:
    """Return True if node was dynamically generated as the child of an AnnAssign
    statement.
    """
    parent = node.parent
    scope = parent.scope()
    return (
        isinstance(parent, AnnAssign)
        and isinstance(scope, ClassDef)
        and is_decorated_with_dataclass(scope)
    )


def _looks_like_dataclass_field_call(node: Call, check_scope: bool = True) -> bool:
    """Return True if node is calling dataclasses field or Field
    from an AnnAssign statement directly in the body of a ClassDef.

    If check_scope is False, skips checking the statement and body.
    """
    if check_scope:
        stmt = node.statement()
        scope = stmt.scope()
        if not (
            isinstance(stmt, AnnAssign)
            and isinstance(scope, ClassDef)
            and is_decorated_with_dataclass(scope)
        ):
            return False

    try:
        inferred = next(node.func.infer())
    except (InferenceError, StopIteration):
        return False

    if not isinstance(inferred, FunctionDef):
        return False

    return inferred.name == FIELD_NAME and inferred.root().name == DATACLASS_MODULE


def _get_field_default(field_call: Call) -> Union[Tuple[str, NodeNG], None]:
    """Return a the default value of a field call, and the corresponding keyword argument name.

    field(default=...) results in the ... node
    field(default_factory=...) results in a Call node with func ... and no arguments

    If neither or both arguments are present, return None instead.
    """
    default, default_factory = None, None
    for keyword in field_call.keywords:
        if keyword.arg == "default":
            default = keyword.value
        elif keyword.arg == "default_factory":
            default_factory = keyword.value

    if default is not None and default_factory is None:
        return "default", default

    if default is None and default_factory is not None:
        new_call = Call(
            lineno=field_call.lineno,
            col_offset=field_call.col_offset,
            parent=field_call.parent,
        )
        new_call.postinit(func=default_factory)
        return "default_factory", new_call

    return None


def _is_class_var(node: NodeNG) -> bool:
    """Return True if node is a ClassVar, with or without subscripting."""
    if PY39_PLUS:
        try:
            inferred = next(node.infer())
        except (InferenceError, StopIteration):
            return False

        return getattr(inferred, "name", "") == "ClassVar"

    # Before Python 3.9, inference returns typing._SpecialForm instead of ClassVar.
    # Our backup is to inspect the node's structure.
    return isinstance(node, Subscript) and (
        isinstance(node.value, Name)
        and node.value.name == "ClassVar"
        or isinstance(node.value, Attribute)
        and node.value.attrname == "ClassVar"
    )


def _is_init_var(node: NodeNG) -> bool:
    """Return True if node is an InitVar, with or without subscripting."""
    try:
        inferred = next(node.infer())
    except (InferenceError, StopIteration):
        return False

    return getattr(inferred, "name", "") == "InitVar"


if PY37_PLUS:
    AstroidManager().register_transform(
        ClassDef, dataclass_transform, is_decorated_with_dataclass
    )

    AstroidManager().register_transform(
        Call,
        inference_tip(infer_dataclass_field_call, raise_on_overwrite=True),
        _looks_like_dataclass_field_call,
    )

    AstroidManager().register_transform(
        Unknown,
        inference_tip(infer_dataclass_attribute, raise_on_overwrite=True),
        _looks_like_dataclass_attribute,
    )
