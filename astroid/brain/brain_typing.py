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


def infer_typing_namedtuple(node, context=None):
    """Infer a typing.NamedTuple(...) call."""
    # This is essentially a namedtuple with different arguments
    # so we extract the args and infer a named tuple.
    try:
        func = next(node.func.infer())
    except InferenceError:
        raise UseInferenceDefault

    if func.qname() != 'typing.NamedTuple':
        raise UseInferenceDefault

    if len(node.args) != 2:
        raise UseInferenceDefault

    if not isinstance(node.args[1], (List, Tuple)):
        raise UseInferenceDefault

    names = []
    for elt in node.args[1].elts:
        if not isinstance(elt, (List, Tuple)):
            raise UseInferenceDefault
        if len(elt.elts) != 2:
            raise UseInferenceDefault
        names.append(elt.elts[0].as_string())

    typename = node.args[0].as_string()
    node = extract_node('namedtuple(%(typename)s, (%(fields)s,)) ' %
        {'typename': typename, 'fields': ",".join(names)})
    return node.infer(context=context)


def infer_typing_namedtuple_class(node, context=None):
    """Infer a subclass of typing.NamedTuple"""

    # Check if it has the corresponding bases
    annassigns_fields = [
        annassign.target.name for annassign in node.body
        if isinstance(annassign, nodes.AnnAssign)
    ]
    code = textwrap.dedent('''
    from collections import namedtuple
    namedtuple({typename!r}, {fields!r})
    ''').format(
        typename=node.name,
        fields=",".join(annassigns_fields)
    )
    node = extract_node(code)
    return node.infer(context=context)


def has_namedtuple_base(node):
    """Predicate for class inference tip

    :type node: ClassDef
    :rtype: bool
    """
    return set(node.basenames) & TYPING_NAMEDTUPLE_BASENAMES


def looks_like_typing_namedtuple(node):
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname == 'NamedTuple'
    if isinstance(func, nodes.Name):
        return func.name == 'NamedTuple'
    return False


def looks_like_typing_typevar_or_newtype(node):
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname in {'TypeVar', 'NewType'}
    if isinstance(func, nodes.Name):
        return func.name in {'TypeVar', 'NewType'}
    return False


TYPING_TYPE_TEMPLATE = """
class Meta:
    def __getitem__(self, item):
        return self

class {0}(metaclass=Meta):
    pass
"""


def infer_typing_typevar_or_newtype(node, context=None):
    """Infer a typing.TypeVar(...) or typing.NewType(...) call"""
    try:
        func = next(node.func.infer())
    except InferenceError:
        raise UseInferenceDefault

    if func.qname() not in {'typing.TypeVar',  'typing.NewType'}:
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
    except InferenceError:
        raise UseInferenceDefault

    if not value.qname().startswith('typing.'):
        raise UseInferenceDefault

    node = extract_node(TYPING_TYPE_TEMPLATE.format(value.qname().split('.')[-1]))
    return node.infer(context=context)


MANAGER.register_transform(
    nodes.Call,
    inference_tip(infer_typing_namedtuple),
    looks_like_typing_namedtuple
)

MANAGER.register_transform(
    nodes.ClassDef,
    inference_tip(infer_typing_namedtuple_class),
    has_namedtuple_base
)
MANAGER.register_transform(
    nodes.Call,
    inference_tip(infer_typing_typevar_or_newtype),
    looks_like_typing_typevar_or_newtype
)
MANAGER.register_transform(
    nodes.Subscript,
    inference_tip(infer_typing_attr)
)
