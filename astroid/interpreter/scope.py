# copyright 2003-2015 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with astroid. If not, see <http://www.gnu.org/licenses/>.

"""Implements logic for determing the scope of a node."""

import itertools

import six

from astroid.tree import treeabc
from astroid import util


# import pdb; pdb.set_trace()

@util.singledispatch
def _scope_by_parent(parent, node):
    """Detect the scope of the *node* by parent's rules.

    The scope for certain kind of nodes depends on the
    parent, as it is the case for default values of arguments
    and function annotation, where the scope is not the scope of
    the parent, but the parent scope of the parent.
    """
    # This is separated in multiple dispatch methods on parents,
    # in order to decouple the implementation for the normal cases.


@_scope_by_parent.register(treeabc.Arguments)
def _scope_by_argument_parent(parent, node):
    args = parent
    if node in itertools.chain(args.defaults, args.kw_defaults):
        return args.parent.parent.scope()
    if six.PY3:
        look_for = itertools.chain(
            (args.kwargannotation, ),
            (args.varargannotation, ),
            args.annotations)
        if node in look_for:
            return args.parent.parent.scope()


@_scope_by_parent.register(treeabc.FunctionDef)
def _scope_by_function_parent(parent, node):
    # Verify if the node is the return annotation of a function,
    # in which case the scope is the parent scope of the function.
    if six.PY3 and node is parent.returns:
        return parent.parent.scope()


@_scope_by_parent.register(treeabc.Comprehension)
def _scope_by_comprehension_parent(parent, node):
    # Get the scope of a node which has a comprehension
    # as a parent. The rules are a bit hairy, but in essence
    # it is simple enough: list comprehensions leaks variables
    # on Python 2, so they have the parent scope of the list comprehension
    # itself. The iter part of the comprehension has almost always
    # another scope than the comprehension itself, but only for the
    # first generator (the outer one). Other comprehensions don't leak
    # variables on Python 2 and 3.

    comprehension = parent_scope = parent.parent
    generators = comprehension.generators

    # The first outer generator always has a different scope
    first_iter = generators[0].iter
    if node is first_iter:
        return parent_scope.parent.scope()

    # This might not be correct for all the cases, but it
    # should be enough for most of them.
    if six.PY2 and isinstance(parent_scope, treeabc.ListComp):
        return parent_scope.parent.scope()
    return parent.scope()


@util.singledispatch
def node_scope(node):
    """Get the scope of the given node."""
    scope = _scope_by_parent(node.parent, node)
    return scope or node.parent.scope()


@node_scope.register(treeabc.Decorators)
def _decorators_scope(node):
    return node.parent.parent.scope()


@node_scope.register(treeabc.Module)
@node_scope.register(treeabc.GeneratorExp)
@node_scope.register(treeabc.DictComp)
@node_scope.register(treeabc.SetComp)
@node_scope.register(treeabc.Lambda)
@node_scope.register(treeabc.FunctionDef)
@node_scope.register(treeabc.ClassDef)
def _scoped_nodes(node):
    return node

if six.PY3:
    node_scope.register(treeabc.ListComp, _scoped_nodes)
