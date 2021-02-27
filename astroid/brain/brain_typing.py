# Copyright (c) 2017-2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 David Euresti <github@euresti.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>

"""Astroid hooks for typing.py support."""
import typing

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


GET_ITEM_TEMPLATE = """
@classmethod
def __getitem__(cls, value):
    return cls
"""


def _looks_like_typing_alias(node: nodes.Call) -> bool:
    """
    Returns True if the node corresponds to a call to _alias function.
    For example :

    MutableSet = _alias(collections.abc.MutableSet, T)

    :param node: call node
    """
    if isinstance(node, nodes.Call) and isinstance(node.func, nodes.Name):
        if node.func.name == "_alias" and isinstance(node.args[0], nodes.Attribute):
            return True
    return False


def infer_typing_alias(
    node: nodes.Call, context: context.InferenceContext = None
) -> node_classes.NodeNG:
    """
    Infers the call to _alias function

    :param node: call node
    :param context: inference context
    """
    if not isinstance(node, nodes.Call):
        return
    res = next(node.args[0].infer(context=context))
    #  Needs to mock the __getitem__ class method so that
    #  MutableSet[T] is acceptable
    func_to_add = extract_node(GET_ITEM_TEMPLATE)
    if res.metaclass():
        res.metaclass().locals["__getitem__"] = [func_to_add]
    return res


MANAGER.register_transform(
    nodes.Call,
    inference_tip(infer_typing_typevar_or_newtype),
    looks_like_typing_typevar_or_newtype,
)
MANAGER.register_transform(
    nodes.Subscript, inference_tip(infer_typing_attr), _looks_like_typing_subscript
)
MANAGER.register_transform(nodes.Call, infer_typing_alias, _looks_like_typing_alias)
