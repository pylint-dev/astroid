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
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.

"""Implements logic for determing the scope of a node."""
import six

from astroid import util
from astroid.tree import treeabc


@util.singledispatch
def node_scope(node):
    """Get the scope of the given node."""
    return node.parent.scope()


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
