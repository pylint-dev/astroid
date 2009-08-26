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
on all nodes :
 .is_statement, returning true if the node should be considered as a
  statement node
 .root(), returning the root node of the tree (i.e. a Module)
 .previous_sibling(), returning previous sibling statement node
 .next_sibling(), returning next sibling statement node
 .statement(), returning the first parent node marked as statement node
 .frame(), returning the first node defining a new local scope (i.e.
  Module, Function or Class)
 .set_local(name, node), define an identifier <name> on the first parent frame,
  with the node defining it. This is used by the astng builder and should not
  be used from out there.

on From and Import :
 .real_name(name),

:author:    Sylvain Thenault
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com

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

from logilab.astng._exceptions import UnresolvableName, NotFoundError, \
                                        InferenceError, ASTNGError
from logilab.astng.utils import extend_class, REDIRECT

INFER_NEED_NAME_STMTS = (From, Import, Global, TryExcept)
LOOP_SCOPES = (Comprehension, For,)

import re
ID_RGX = re.compile('^[a-zA-Z_][a-zA-Z_0-9]*$')
del re

# astng fields definition ####################################################
Arguments._astng_fields = ('args', 'defaults')
AssAttr._astng_fields = ('expr',)
Assert._astng_fields = ('test', 'fail',)
Assign._astng_fields = ('targets', 'value',)
AssName._astng_fields = ()

AugAssign._astng_fields = ('target', 'value',)
BinOp._astng_fields = ('left', 'right',)
BoolOp._astng_fields = ('values',)
UnaryOp._astng_fields = ('operand',)

Backquote._astng_fields = ('value',)
Break._astng_fields = ()
CallFunc._astng_fields = ('func', 'args', 'starargs', 'kwargs')
Class._astng_fields = ('bases', 'body',) # name
Compare._astng_fields = ('left', 'ops',)
Comprehension._astng_fields = ('target', 'iter' ,'ifs')
Const._astng_fields = ()
Continue._astng_fields = ()
Decorators._astng_fields = ('nodes',)
Delete._astng_fields = ('targets', )
DelAttr._astng_fields = ('expr',)
DelName._astng_fields = ()
Dict._astng_fields = ('items',)
Discard._astng_fields = ('value',)
From._astng_fields = ()
Ellipsis._astng_fields = ()
EmptyNode._astng_fields = ()
ExceptHandler._astng_fields = ('type', 'name', 'body',)
Exec._astng_fields = ('expr', 'globals', 'locals',)
ExtSlice._astng_fields =('dims',)
Function._astng_fields = ('decorators', 'args', 'body')
For._astng_fields = ('target', 'iter', 'body', 'orelse',)
Getattr._astng_fields = ('expr',) # (former value), attr (now attrname), ctx
GenExpr._astng_fields = ('elt', 'generators')
Global._astng_fields = ()
If._astng_fields = ('test', 'body', 'orelse')
IfExp._astng_fields = ('test', 'body', 'orelse')
Import._astng_fields = ()
Index._astng_fields = ('value',)
Keyword._astng_fields = ('value',)
Lambda._astng_fields = ('args', 'body',)
List._astng_fields = ('elts',)  # ctx
ListComp._astng_fields = ('elt', 'generators')
Module._astng_fields = ('body',)
Name._astng_fields = () # id, ctx
Pass._astng_fields = ()
Print._astng_fields = ('dest', 'values',) # nl
Raise._astng_fields = ('type', 'inst', 'tback')
Return._astng_fields = ('value',)
Slice._astng_fields = ('lower', 'upper', 'step')
Subscript._astng_fields = ('value', 'slice')
TryExcept._astng_fields = ('body', 'handlers', 'orelse',)
TryFinally._astng_fields = ('body', 'finalbody',)
Tuple._astng_fields = ('elts',)  # ctx
With._astng_fields = ('expr', 'vars', 'body')
While._astng_fields = ('test', 'body', 'orelse',)
Yield._astng_fields = ('value',)

STMT_NODES = (
    Assign, AugAssign, Assert, Break, Class, Continue, Delete, Discard,
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
    original class from the compiler.ast / _ast module using its dictionnary
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
        if not self.is_statement:
            return self.parent.next_sibling()
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        try:
            return stmts[index +1]
        except IndexError:
            pass

    def previous_sibling(self):
        """return the previous sibling statement"""
        if not self.is_statement:
            return self.parent.previous_sibling()
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        if index >= 1:
            return stmts[index -1]
        return

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

# extend all classes instead of base Node class which is an unextendable type
# in 2.6
for cls in ALL_NODES:
    extend_class(cls, NodeNG)

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


def replace_child(self, child, newchild):
    sequence = self.child_sequence(child)
    newchild.parent = self
    child.parent = None
    sequence[sequence.index(child)] = newchild

for klass in STMT_NODES:
    klass.is_statement = True
    klass.replace = replace_child
Module.replace = replace_child

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

def _get_children_nochildren(self):
    return ()

#  get_children overrides  ####################################################

def _dict_get_children(node): # XXX : distinguish key and value ?
    """override get_children for Dict"""
    for key, value in node.items:
        yield key
        yield value
Dict.get_children = _dict_get_children


def _compare_get_children(node):
    """override get_children for tuple fields"""
    yield node.left
    for _, comparator in node.ops:
        yield comparator # we don't want the 'op'
Compare.get_children = _compare_get_children

# block range overrides #######################################################

def for_set_line_info(self, lastchild):
    self.fromlineno = self.lineno
    self.tolineno = lastchild.tolineno
    self.blockstart_tolineno = self.iter.tolineno
For.set_line_info = for_set_line_info

def if_set_line_info(self, lastchild):
    self.fromlineno = self.lineno
    self.tolineno = lastchild.tolineno
    self.blockstart_tolineno = self.test.tolineno
If.set_line_info = if_set_line_info
While.set_line_info = if_set_line_info

def try_set_line_info(self, lastchild):
    self.fromlineno = self.blockstart_tolineno = self.lineno
    self.tolineno = lastchild.tolineno
TryExcept.set_line_info = try_set_line_info
TryFinally.set_line_info = try_set_line_info

def excepthandler_set_line_info(self, lastchild):
    self.fromlineno = self.lineno
    if self.name:
        self.blockstart_tolineno= self.name.tolineno
    elif self.type:
        self.blockstart_tolineno= self.type.tolineno
    else:
        self.blockstart_tolineno= self.lineno
    self.tolineno = lastchild.tolineno
ExceptHandler.set_line_info = excepthandler_set_line_info

def excepthandler_catch(self, exceptions):
    if self.type is None or exceptions is None:
        return True
    for node in self.type.nodes_of_class(Name):
        if node.name in exceptions:
            return True
ExceptHandler.catch = excepthandler_catch

def with_set_line_info(self, lastchild):
    self.fromlineno = self.blockstart_tolineno = self.lineno
    self.tolineno = lastchild.tolineno
    if self.vars:
        self.blockstart_tolineno = self.vars.tolineno
    else:
        self.blockstart_tolineno = self.expr.tolineno
With.set_line_info = with_set_line_info


def object_block_range(node, lineno):
    """handle block line numbers range for function/class statements:

    start from the "def" or "class" position whatever the given lineno
    """
    return node.fromlineno, node.tolineno
Function.block_range = object_block_range
Class.block_range = object_block_range
Module.block_range = object_block_range


def _elsed_block_range(node, lineno, orelse, last=None):
    """handle block line numbers range for try/finally, for and while
    statements
    """
    if lineno == node.fromlineno:
        return lineno, lineno
    if orelse:
        if lineno >= orelse[0].fromlineno:
            return lineno, orelse[-1].tolineno
        return lineno, orelse[0].fromlineno - 1
    return lineno, last or node.tolineno


def if_block_range(node, lineno):
    """handle block line numbers range for if/elif statements"""
    if lineno == node.body[0].fromlineno:
        return lineno, lineno
    if lineno <= node.body[-1].tolineno:
        return lineno, node.body[-1].tolineno
    return _elsed_block_range(node, lineno, node.orelse, node.body[0].fromlineno - 1)
If.block_range = if_block_range


def try_except_block_range(node, lineno):
    """handle block line numbers range for try/except statements"""
    last = None
    for exhandler in node.handlers:
        if exhandler.type and lineno == exhandler.type.fromlineno:
            return lineno, lineno
        if exhandler.body[0].fromlineno <= lineno <= exhandler.body[-1].tolineno:
            return lineno, exhandler.body[-1].tolineno
        if last is None:
            last = exhandler.body[0].fromlineno - 1
    return _elsed_block_range(node, lineno, node.orelse, last)
TryExcept.block_range = try_except_block_range


def elsed_block_range(node, lineno):
    """handle block line numbers range for for and while statements"""
    return _elsed_block_range(node, lineno, node.orelse)
While.block_range = elsed_block_range
For.block_range = elsed_block_range


def try_finalbody_block_range(node, lineno):
    """handle block line numbers range for try/finally statements"""
    child = node.body[0]
    # py2.5 try: except: finally:
    if (isinstance(child, TryExcept) and child.fromlineno == node.fromlineno
        and lineno > node.fromlineno and lineno <= child.tolineno):
        return child.block_range(lineno)
    return _elsed_block_range(node, lineno, node.finalbody)
TryFinally.block_range = try_finalbody_block_range


# From and Import #############################################################

def real_name(node, asname):
    """get name from 'as' name"""
    for index in range(len(node.names)):
        name, _asname = node.names[index]
        if name == '*':
            return asname
        if not _asname:
            name = name.split('.', 1)[0]
            _asname = name
        if asname == _asname:
            return name
    raise NotFoundError(asname)
From.real_name = real_name
Import.real_name = real_name


