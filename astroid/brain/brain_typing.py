# Copyright (c) 2017-2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 David Euresti <github@euresti.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>

"""Astroid hooks for typing.py support."""
import sys
import typing
from functools import lru_cache

from astroid import (
    MANAGER,
    UseInferenceDefault,
    extract_node,
    inference_tip,
    node_classes,
    nodes,
    context,
    InferenceError,
)
import astroid

PY37 = sys.version_info[:2] >= (3, 7)
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


GET_ITEM_TEMPLATE = """
@classmethod
def __getitem__(cls, value):
    return cls
"""

ABC_METACLASS_TEMPLATE = """
from abc import ABCMeta
ABCMeta
"""


@lru_cache()
def create_typing_metaclass():
    #  Needs to mock the __getitem__ class method so that
    #  MutableSet[T] is acceptable
    func_to_add = extract_node(GET_ITEM_TEMPLATE)

    abc_meta = next(extract_node(ABC_METACLASS_TEMPLATE).infer())
    typing_meta = nodes.ClassDef(
        name="ABCMeta_typing",
        lineno=abc_meta.lineno,
        col_offset=abc_meta.col_offset,
        parent=abc_meta.parent,
    )
    typing_meta.postinit(
        bases=[extract_node(ABC_METACLASS_TEMPLATE)], body=[], decorators=None
    )
    typing_meta.locals["__getitem__"] = [func_to_add]
    return typing_meta


def _looks_like_typing_alias(node: nodes.Call) -> bool:
    """
    Returns True if the node corresponds to a call to _alias function.
    For example :

    MutableSet = _alias(collections.abc.MutableSet, T)

    :param node: call node
    """
    return (
        isinstance(node, nodes.Call)
        and isinstance(node.func, nodes.Name)
        and node.func.name == "_alias"
        and isinstance(node.args[0], nodes.Attribute)
    )


def infer_typing_alias(
    node: nodes.Call, ctx: context.InferenceContext = None
) -> typing.Optional[node_classes.NodeNG]:
    """
    Infers the call to _alias function

    :param node: call node
    :param context: inference context
    """
    if not isinstance(node, nodes.Call):
        return None
    res = next(node.args[0].infer(context=ctx))

    if res != astroid.Uninferable and isinstance(res, nodes.ClassDef):
        class_def = nodes.ClassDef(
            name=f"{res.name}_typing",
            lineno=0,
            col_offset=0,
            parent=res.parent,
        )
        class_def.postinit(
            bases=[res],
            body=res.body,
            decorators=res.decorators,
            metaclass=create_typing_metaclass(),
        )
        return class_def

    if len(node.args) == 2 and isinstance(node.args[0], nodes.Attribute):
        class_def = nodes.ClassDef(
            name=node.args[0].attrname,
            lineno=0,
            col_offset=0,
            parent=node.parent,
        )
        class_def.postinit(
            bases=[], body=[], decorators=None, metaclass=create_typing_metaclass()
        )
        return class_def

    return None


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

if PY37:
    MANAGER.register_transform(nodes.Call, infer_typing_alias, _looks_like_typing_alias)
