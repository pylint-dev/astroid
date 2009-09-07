# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""
Module containing the node classes; it is only used for avoiding circular imports
"""

from __future__ import generators

__docformat__ = "restructuredtext en"

from itertools import imap

try:
    from logilab.astng._nodes_ast import *
    from logilab.astng._nodes_ast import _const_factory
    AST_MODE = '_ast'
except ImportError:
    from logilab.astng._nodes_compiler import *
    from logilab.astng._nodes_compiler import _const_factory
    AST_MODE = 'compiler'
from logilab.astng.utils import REDIRECT

INFER_NEED_NAME_STMTS = (From, Import, Global, TryExcept)
LOOP_SCOPES = (Comprehension, For,)


STMT_NODES = (
    Assert, Assign, AugAssign, Break, Class, Continue, Delete, Discard,
    ExceptHandler, Exec, For, From, Function, Global, If, Import, Pass, Print,
    Raise, Return, TryExcept, TryFinally, While, With
    )

ALL_NODES = STMT_NODES + (
    Arguments, AssAttr, AssName, BinOp, BoolOp, Backquote,  CallFunc, Compare,
    Comprehension, Const, Decorators, DelAttr, DelName, Dict, Ellipsis,
    EmptyNode,  ExtSlice, Getattr,  GenExpr, IfExp, Index, Keyword, Lambda,
    List,  ListComp, Module, Name, Slice, Subscript, UnaryOp, Tuple, Yield
    )


# Node  ######################################################################

class NodeNG:
    """/!\ this class should not be used directly /!\
    It is used as method and attribute container, and updates the
    original class from the compiler.ast / _ast module using its dictionary
    (see below the class definition)
    """
    is_statement = False
    # attributes below are set by the builder module or by raw factories
    lineno = None
    fromlineno = None
    tolineno = None
    # parent node in the tree
    parent = None

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, getattr(self, 'name', ''))

    def accept(self, visitor):
        klass = self.__class__.__name__
        func = getattr(visitor, "visit_" + REDIRECT.get(klass, klass).lower())
        return func(self)

    def get_children(self):
        d = self.__dict__
        for f in self._astng_fields:
            attr = d[f]
            if attr is None:
                continue
            if isinstance(attr, (list, tuple)):
                for elt in attr:
                    yield elt
            else:
                yield attr

    def parent_of(self, node):
        """return true if i'm a parent of the given node"""
        parent = node.parent
        while parent is not None:
            if self is parent:
                return True
            parent = parent.parent
        return False

    def statement(self):
        """return the first parent node marked as statement node"""
        if self.is_statement:
            return self
        return self.parent.statement()

    def frame(self):
        """return the first parent frame node (i.e. Module, Function or Class)
        """
        return self.parent.frame()

    def scope(self):
        """return the first node defining a new scope (i.e. Module, Function,
        Class, Lambda but also GenExpr)
        """
        return self.parent.scope()

    def root(self):
        """return the root node of the tree, (i.e. a Module)"""
        if self.parent:
            return self.parent.root()
        return self

    def child_sequence(self, child):
        """search for the right sequence where the child lies in"""
        for field in self._astng_fields:
            node_or_sequence = getattr(self, field)
            if node_or_sequence is child:
                return [node_or_sequence]
            # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
            if isinstance(node_or_sequence, (tuple, list)) and child in node_or_sequence:
                return node_or_sequence
        else:
            msg = 'Could not found %s in %s\'s children'
            raise ASTNGError(msg % (repr(child), repr(self)))

    def locate_child(self, child):
        """return a 2-uple (child attribute name, sequence or node)"""
        for field in self._astng_fields:
            node_or_sequence = getattr(self, field)
            # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
            if child is node_or_sequence:
                return field, child
            if isinstance(node_or_sequence, (tuple, list)) and child in node_or_sequence:
                return field, node_or_sequence
        msg = 'Could not found %s in %s\'s children'
        raise ASTNGError(msg % (repr(child), repr(self)))

    def next_sibling(self):
        """return the next sibling statement"""
        return self.parent.next_sibling()

    def previous_sibling(self):
        """return the previous sibling statement"""
        return self.parent.previous_sibling()

    def nearest(self, nodes):
        """return the node which is the nearest before this one in the
        given list of nodes
        """
        myroot = self.root()
        mylineno = self.fromlineno
        nearest = None, 0
        for node in nodes:
            assert node.root() is myroot, \
                   'not from the same module %s' % (self, node)
            lineno = node.fromlineno
            if node.fromlineno > mylineno:
                break
            if lineno > nearest[1]:
                nearest = node, lineno
        # FIXME: raise an exception if nearest is None ?
        return nearest[0]

    def set_line_info(self, lastchild):
        if self.lineno is None:
            self.fromlineno = self._fixed_source_line()
        else:
            self.fromlineno = self.lineno
        if lastchild is None:
            self.tolineno = self.fromlineno
        else:
            self.tolineno = lastchild.tolineno
        assert self.fromlineno is not None, self
        assert self.tolineno is not None, self

    def _fixed_source_line(self):
        """return the line number where the given node appears

        we need this method since not all nodes have the lineno attribute
        correctly set...
        """
        line = self.lineno
        _node = self
        try:
            while line is None:
                _node = _node.get_children().next()
                line = _node.lineno
        except StopIteration:
            _node = self.parent
            while _node and line is None:
                line = _node.lineno
                _node = _node.parent
        return line

    def block_range(self, lineno):
        """handle block line numbers range for non block opening statements
        """
        return lineno, self.tolineno

    def set_local(self, name, stmt):
        """delegate to a scoped parent handling a locals dictionary"""
        self.parent.set_local(name, stmt)

    def nodes_of_class(self, klass, skip_klass=None):
        """return an iterator on nodes which are instance of the given class(es)

        klass may be a class object or a tuple of class objects
        """
        if isinstance(self, klass):
            yield self
        for child_node in self.get_children():
            if skip_klass is not None and isinstance(child_node, skip_klass):
                continue
            for matching in child_node.nodes_of_class(klass, skip_klass):
                yield matching

    def _infer_name(self, frame, name):
        if isinstance(self, INFER_NEED_NAME_STMTS) or (
                 isinstance(self, Arguments) and self.parent is frame):
            return name
        return None

    def callable(self):
        return False

    def eq(self, value):
        return False

    def as_string(self):
        from logilab.astng.nodes_as_string import as_string
        return as_string(self)

    def repr_tree(self):
        """print a nice astng tree representation"""
        result = []
        _repr_tree(self, result)
        print "\n".join(result)


INDENT = "    "

def _repr_tree(node, result, indent='', _done=None):
    """built a tree representation of a node as a list of lines"""
    if _done is None:
        _done = set()
    if not hasattr(node, '_astng_fields'): # not a astng node
        return
    if node in _done:
        result.append( indent + 'loop in tree: %s' % node )
        return
    _done.add(node)
    result.append( indent + str(node))
    indent += INDENT
    for field in node._astng_fields:
        value = getattr(node, field)
        if isinstance(value, (list, tuple) ):
            result.append(  indent + field + " = [" )
            for child in value:
                if isinstance(child, (list, tuple) ):
                    # special case for Dict # FIXME
                     _repr_tree(child[0], result, indent, _done)
                     _repr_tree(child[1], result, indent, _done)
                     result.append(indent + ',')
                else:
                    _repr_tree(child, result, indent, _done)
            result.append(  indent + "]" )
        else:
            result.append(  indent + field + " = " )
            _repr_tree(value, result, indent, _done)




# some small MixIns for extending the node classes #######################

class StmtMixIn(object):
    """StmtMixIn used only for a adding a few attributes"""
    is_statement = True

    def replace(self, child, newchild):
        sequence = self.child_sequence(child)
        newchild.parent = self
        child.parent = None
        sequence[sequence.index(child)] = newchild

    def next_sibling(self):
        """return the next sibling statement"""
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        try:
            return stmts[index +1]
        except IndexError:
            pass

    def previous_sibling(self):
        """return the previous sibling statement"""
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        if index >= 1:
            return stmts[index -1]


class BlockRangeMixIn(object):
    """override block range """
    def set_line_info(self, lastchild):
        self.fromlineno = self.lineno
        self.tolineno = lastchild.tolineno
        self.blockstart_tolineno = self._blockstart_toline()

    def _elsed_block_range(self, lineno, orelse, last=None):
        """handle block line numbers range for try/finally, for, if and while
        statements
        """
        if lineno == self.fromlineno:
            return lineno, lineno
        if orelse:
            if lineno >= orelse[0].fromlineno:
                return lineno, orelse[-1].tolineno
            return lineno, orelse[0].fromlineno - 1
        return lineno, last or self.tolineno


# constants ... ##############################################################

CONST_CLS = {
    list: List,
    tuple: Tuple,
    dict: Dict,
    }

def const_factory(value):
    """return an astng node for a python value"""
    try:
        # if value is of class list, tuple, dict use specific class, not Const
        cls = CONST_CLS[value.__class__]
        node = cls()
        if isinstance(node, Dict):
            node.items = ()
        else:
            node.elts = ()
    except KeyError:
        try:
            node = Const(value)
        except KeyError:
            node = _const_factory(value)
    return node

