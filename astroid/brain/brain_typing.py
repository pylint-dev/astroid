# Copyright (c) 2017-2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 David Euresti <github@euresti.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>

"""Astroid hooks for typing.py support."""
import sys
import typing

from astroid import (
    MANAGER,
    UseInferenceDefault,
    extract_node,
    inference_tip,
    nodes,
    context,
    InferenceError,
)

PY39 = sys.version_info[:2] >= (3, 9)

TYPING_NAMEDTUPLE_BASENAMES = {"NamedTuple", "typing.NamedTuple"}
TYPING_TYPEVARS = {"TypeVar", "NewType"}
TYPING_TYPEVARS_QUALIFIED = {"typing.TypeVar", "typing.NewType"}
TYPING_TYPE_TEMPLATE = """
class Meta(type):
    def __getitem__(self, item):
        return self

    @property
    def __args__(self):
        return ()

class {0}(metaclass=Meta):
    pass
"""
TYPING_MEMBERS = set(typing.__all__)


def looks_like_typing_typevar_or_newtype(node):
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname in TYPING_TYPEVARS
    if isinstance(func, nodes.Name):
        return func.name in TYPING_TYPEVARS
    return False


def infer_typing_typevar_or_newtype(node, context=None):
    """Infer a typing.TypeVar(...) or typing.NewType(...) call"""
    try:
        func = next(node.func.infer(context=context))
    except InferenceError as exc:
        raise UseInferenceDefault from exc

    if func.qname() not in TYPING_TYPEVARS_QUALIFIED:
        raise UseInferenceDefault
    if not node.args:
        raise UseInferenceDefault

    typename = node.args[0].as_string().strip("'")
    node = extract_node(TYPING_TYPE_TEMPLATE.format(typename))
    return node.infer(context=context)


def _looks_like_typing_subscript(node):
    """Try to figure out if a Subscript node *might* be a typing-related subscript"""
    if isinstance(node, nodes.Name):
        return node.name in TYPING_MEMBERS
    elif isinstance(node, nodes.Attribute):
        return node.attrname in TYPING_MEMBERS
    elif isinstance(node, nodes.Subscript):
        return _looks_like_typing_subscript(node.value)
    return False


def infer_typing_attr(node, context=None):
    """Infer a typing.X[...] subscript"""
    try:
        value = next(node.value.infer())
    except InferenceError as exc:
        raise UseInferenceDefault from exc

    if not value.qname().startswith("typing."):
        raise UseInferenceDefault

    node = extract_node(TYPING_TYPE_TEMPLATE.format(value.qname().split(".")[-1]))
    return node.infer(context=context)


def _looks_like_typedDict(  # pylint: disable=invalid-name
    node: nodes.FunctionDef,
) -> bool:
    """Check if node is TypedDict FunctionDef."""
    return isinstance(node, nodes.FunctionDef) and node.name == "TypedDict"


def infer_typedDict(  # pylint: disable=invalid-name
    node: nodes.FunctionDef, ctx: context.InferenceContext = None
) -> None:
    """Replace TypedDict FunctionDef with ClassDef."""
    class_def = nodes.ClassDef(
        name="TypedDict",
        doc=node.doc,
        lineno=node.lineno,
        col_offset=node.col_offset,
        parent=node.parent,
    )
    class_def.postinit(bases=[], body=[], decorators=None)
    node.root().locals["TypedDict"] = [class_def]


MANAGER.register_transform(
    nodes.Call,
    inference_tip(infer_typing_typevar_or_newtype),
    looks_like_typing_typevar_or_newtype,
)
MANAGER.register_transform(
    nodes.Subscript, inference_tip(infer_typing_attr), _looks_like_typing_subscript
)

if PY39:
    MANAGER.register_transform(
        nodes.FunctionDef, infer_typedDict, _looks_like_typedDict
    )
