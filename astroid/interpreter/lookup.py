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

import collections

import six

from astroid import exceptions
from astroid.util import _singledispatch
from astroid.tree import treeabc
from astroid.tree import base as treebase
from astroid.interpreter import util

try:
    from types import MappingProxyType
except ImportError:
    from dictproxyhack import dictproxy as MappingProxyType


class LocalsDictNode(treebase.LookupMixIn,
                     treebase.NodeNG):
    """Provides locals handling common to Module, FunctionDef
    and ClassDef nodes, including a dict like interface for direct access
    to locals information
    """

    # attributes below are set by the builder module or by raw factories

    # dictionary of locals with name as key and node defining the local as
    # value

    @property
    def locals(self):
        return MappingProxyType(get_locals(self))

    def frame(self):
        """return the first parent frame node (i.e. Module, FunctionDef or
        ClassDef)

        """
        return self

    def _scope_lookup(self, node, name, offset=0):
        """XXX method for interfacing the scope lookup"""
        try:
            stmts = node._filter_stmts(self.locals[name], self, offset)
        except KeyError:
            stmts = ()
        if stmts:
            return self, stmts
        if self.parent: # i.e. not Module
            # nested scope: if parent scope is a function, that's fine
            # else jump to the module
            pscope = self.parent.scope()
            if not pscope.is_function:
                pscope = pscope.root()
            return pscope.scope_lookup(node, name)
        return builtin_lookup(name) # Module

    def set_local(self, name, stmt):
        raise Exception('Attempted locals mutation.')

    # def set_local(self, name, stmt):
    #     """define <name> in locals (<stmt> is the node defining the name)
    #     if the node is a Module node (i.e. has globals), add the name to
    #     globals

    #     if the name is already defined, ignore it
    #     """
    #     #assert not stmt in self.locals.get(name, ()), (self, stmt)
    #     self.locals.setdefault(name, []).append(stmt)

    __setitem__ = set_local

    # def _append_node(self, child):
    #     """append a child, linking it in the tree"""
    #     self.body.append(child)
    #     child.parent = self

    # def add_local_node(self, child_node, name=None):
    #     """append a child which should alter locals to the given node"""
    #     if name != '__class__':
    #         # add __class__ node as a child will cause infinite recursion later!
    #         self._append_node(child_node)
    #     self.set_local(name or child_node.name, child_node)

    def __getitem__(self, item):
        """method from the `dict` interface returning the first node
        associated with the given name in the locals dictionary

        :type item: str
        :param item: the name of the locally defined object
        :raises KeyError: if the name is not defined
        """
        return self.locals[item][0]

    def __iter__(self):
        """method from the `dict` interface returning an iterator on
        `self.keys()`
        """
        return iter(self.locals)

    def keys(self):
        """method from the `dict` interface returning a tuple containing
        locally defined names
        """
        return self.locals.keys()

    def values(self):
        """method from the `dict` interface returning a tuple containing
        locally defined nodes which are instance of `FunctionDef` or `ClassDef`
        """
        return tuple(v[0] for v in self.locals.values())

    def items(self):
        """method from the `dict` interface returning a list of tuple
        containing each locally defined name with its associated node,
        which is an instance of `FunctionDef` or `ClassDef`
        """
        return tuple((k, v[0]) for k, v in self.locals.items())

    def __contains__(self, name):
        return name in self.locals


def builtin_lookup(name):
    """lookup a name into the builtin module
    return the list of matching statements and the astroid for the builtin
    module
    """
    from astroid import MANAGER # TODO(cpopa) needs to be removed.

    builtin_astroid = MANAGER.builtins()
    if name == '__dict__':
        return builtin_astroid, ()
    stmts = builtin_astroid.locals.get(name, ())
    # Use inference to find what AssignName nodes point to in builtins.
    stmts = [next(s.infer()) if isinstance(s, treeabc.AssignName) else s
             for s in stmts]
    return builtin_astroid, stmts


@_singledispatch
def get_locals(node):
    '''Return the local variables for an appropriate node.

    For function nodes, this will be the local variables defined in
    their scope, what would be returned by a locals() call in the
    function body.  For Modules, this will be all the global names
    defined in the module, what would be returned by a locals() or
    globals() call at the module level.  For classes, this will be
    class attributes defined in the class body, also what a locals()
    call in the body would return.

    This function starts by recursing over its argument's children to
    avoid incorrectly adding a class's, function's, or module's name
    to its own local variables.

    Args:
        node (LocalsDictNode): A node defining a scope to return locals for.

    Returns:
        A defaultdict(list) mapping names (strings) to lists of nodes.

    Raises:
        TypeError: When called on a node that doesn't represent a scope or a 
            non-node object.
    '''
    raise TypeError("This isn't an astroid node: %s" % type(node))


# pylint: disable=unused-variable; doesn't understand singledispatch
@get_locals.register(treeabc.NodeNG)
def not_scoped_node(node):
    raise TypeError("This node doesn't have local variables: %s" % type(node))


# pylint: disable=unused-variable; doesn't understand singledispatch
@get_locals.register(LocalsDictNode)
def scoped_node(node):
    locals_ = collections.defaultdict(list)
    for n in node.get_children():
        _get_locals(n, locals_)
    return locals_


@_singledispatch
def _get_locals(node, locals_):
    '''Return the local variables for a node.

    This is the internal recursive generic function for gathering
    nodes into a local variables mapping.  The locals mapping is
    passed down and mutated by each function.

    Args:
        node (NodeNG): The node to inspect for assignments to locals.
        locals_ (defaultdict(list)): A mapping of (strings) to lists of nodes.

    Raises:
        TypeError: When called on a non-node object.

    '''

    raise TypeError('Non-astroid object in an astroid AST: %s' % type(node))


# pylint: disable=unused-variable; doesn't understand singledispatch
@_get_locals.register(treeabc.NodeNG)
def locals_generic(node, locals_):
    '''Generic nodes don't create name bindings or scopes.'''
    for n in node.get_children():
        _get_locals(n, locals_)


# # pylint: disable=unused-variable; doesn't understand singledispatch
@_get_locals.register(LocalsDictNode)
def locals_new_scope(node, locals_):
    '''These nodes start a new scope, so terminate recursion here.'''


# pylint: disable=unused-variable; doesn't understand singledispatch
@_get_locals.register(treeabc.AssignName)
@_get_locals.register(treeabc.DelName)
@_get_locals.register(treeabc.FunctionDef)
@_get_locals.register(treeabc.ClassDef)
@_get_locals.register(treeabc.Parameter)
def locals_name(node, locals_):
    '''These nodes add a name to the local variables.  AssignName and
    DelName have no children while FunctionDef and ClassDef start a
    new scope so shouldn't be recursed into.'''
    locals_[node.name].append(node)


@_get_locals.register(treeabc.InterpreterObject)
def locals_interpreter_object(node, locals_):
    '''InterpreterObjects add an object to the local variables under a specified
    name.'''
    if node.name:
        locals_[node.name].append(node)


@_get_locals.register(treeabc.ReservedName)
def locals_reserved_name(node, locals_):
    '''InterpreterObjects add an object to the local variables under a specified
    name.'''
    locals_[node.name].append(node.value)


# pylint: disable=unused-variable; doesn't understand singledispatch
@_get_locals.register(treeabc.Arguments)
def locals_arguments(node, locals_):
    '''Other names assigned by functions have AssignName nodes that are
    children of an Arguments node.'''
    if node.vararg:
        locals_[node.vararg].append(node)
    if node.kwarg:
        locals_[node.kwarg].append(node)
    for n in node.get_children():
        _get_locals(n, locals_)


# pylint: disable=unused-variable; doesn't understand singledispatch
@_get_locals.register(treeabc.Import)
def locals_import(node, locals_):
    for name, asname in node.names:
        name = asname or name
        locals_[name.split('.')[0]].append(node)


# pylint: disable=unused-variable; doesn't understand singledispatch
@_get_locals.register(treeabc.ImportFrom)
def locals_import_from(node, locals_):
    # Don't add future imports to locals.
    if node.modname == '__future__':
        return

    # Sort the list for having the locals ordered by their first
    # appearance.
    def sort_locals(my_list):
        my_list.sort(key=lambda node: node.fromlineno or 0)

    for name, asname in node.names:
        if name == '*':
            try:
                imported = util.do_import_module(node, node.modname)
            except exceptions.AstroidBuildingError:
                continue
            for name in imported.public_names():
                locals_[name].append(node)
                sort_locals(locals_[name])
        else:
            locals_[asname or name].append(node)
            sort_locals(locals_[asname or name])
