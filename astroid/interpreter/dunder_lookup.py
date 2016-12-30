# Copyright (c) 2016 Claudiu Popa <pcmanticore@gmail.com>
# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""Contains logic for retrieving special methods.

This implementation does not rely on the dot attribute access
logic, found in ``.getattr()``. The difference between these two
is that the dunder methods are looked with the type slots
(you can find more about these here
http://lucumr.pocoo.org/2014/8/16/the-python-i-would-like-to-see/)
As such, the lookup for the special methods is actually simpler than
the dot attribute access.
"""
import itertools

import astroid
from astroid import exceptions
from astroid import util
from astroid.interpreter import runtimeabc
from astroid.tree import treeabc


def _lookup_in_mro(node, name):
    local_attrs = node.locals.get(name, [])
    external_attrs = node.external_attrs.get(name, [])
    attrs = itertools.chain(local_attrs, external_attrs)

    nodes = itertools.chain.from_iterable(
        itertools.chain(
            ancestor.locals.get(name, []),
            ancestor.external_attrs.get(name, [])
        )
        for ancestor in node.ancestors(recurs=True)
    )
    values = list(itertools.chain(attrs, nodes))
    if not values:
        raise exceptions.NotSupportedError

    return values


@util.singledispatch
def lookup(node, name):
    """Lookup the given special method name in the given *node*

    If the special method was found, then a list of attributes
    will be returned. Otherwise, `astroid.NotSupportedError`
    is going to be raised.
    """
    raise exceptions.NotSupportedError


@lookup.register(treeabc.ClassDef)
def _(node, name):
    metaclass = node.metaclass()
    if metaclass is None:
        raise exceptions.NotSupportedError

    return _lookup_in_mro(metaclass, name)


@lookup.register(runtimeabc.Instance)
def _(node, name):
    return _lookup_in_mro(node, name)


@lookup.register(runtimeabc.BuiltinInstance)
def _(node, name):
    values = node.locals.get(name, [])
    if not values:
        raise exceptions.NotSupportedError

    return values
