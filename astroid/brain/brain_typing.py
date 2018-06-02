# Copyright (c) 2016 David Euresti <david@dropbox.com>

"""Astroid hooks for typing.py support."""
import textwrap

from astroid import (
    MANAGER, UseInferenceDefault, extract_node, inference_tip,
    nodes, InferenceError)
from astroid.nodes import List, Tuple


TYPING_NAMEDTUPLE_BASENAMES = {
    'NamedTuple',
    'typing.NamedTuple'
}
TYPING_TYPEVARS = {'TypeVar', 'NewType'}
TYPING_TYPEVARS_QUALIFIED = {'typing.TypeVar', 'typing.NewType'}






def has_namedtuple_base(node):
    """Predicate for class inference tip

    :type node: ClassDef
    :rtype: bool
    """
    return set(node.basenames) & TYPING_NAMEDTUPLE_BASENAMES



def looks_like_typing_typevar_or_newtype(node):
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname in TYPING_TYPEVARS
    if isinstance(func, nodes.Name):
        return func.name in TYPING_TYPEVARS
    return False


TYPING_TYPE_TEMPLATE = """
class Meta(type):
    def __getitem__(self, item):
        return self

class {0}(metaclass=Meta):
    pass
"""


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


def infer_typing_attr(node, context=None):
    """Infer a typing.X[...] subscript"""
    try:
        value = next(node.value.infer())
    except InferenceError as exc:
        raise UseInferenceDefault from exc

    if not value.qname().startswith('typing.'):
        raise UseInferenceDefault

    node = extract_node(TYPING_TYPE_TEMPLATE.format(value.qname().split('.')[-1]))
    return node.infer(context=context)


MANAGER.register_transform(
    nodes.Call,
    inference_tip(infer_typing_typevar_or_newtype),
    looks_like_typing_typevar_or_newtype
)
MANAGER.register_transform(
    nodes.Subscript,
    inference_tip(infer_typing_attr),
)
