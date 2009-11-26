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
"""python < 2.5 compiler package compatibility module [1]


 [1] http://docs.python.org/lib/module-compiler.ast.html

:author:    Sylvain Thenault
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

__docformat__ = "restructuredtext en"

import sys
from compiler import ast
from compiler.ast import AssAttr, AssList, AssName, \
     AssTuple, Assert, Assign, AugAssign, \
     Backquote, Break, CallFunc, Class, \
     Compare, Const, Continue, Dict, Discard, \
     Ellipsis, EmptyNode, Exec, \
     For, From, Function, Getattr, Global, \
     If, Import, Keyword, Lambda, \
     List, ListComp, ListCompFor as Comprehension, ListCompIf, Module, Name, Node, \
     Pass, Print, Raise, Return, \
     Sliceobj, Stmt, Subscript, TryExcept, TryFinally, Tuple, \
     While, Yield

# nodes which are not part of astng
from compiler.ast import AssList as _AssList, AssTuple as _AssTuple,\
     Printnl as _Printnl, And as _And, Or as _Or,\
     UnaryAdd as _UnaryAdd, UnarySub as _UnarySub, Not as _Not,\
     Invert as _Invert, Add as _Add, Div as _Div, FloorDiv as _FloorDiv,\
     Mod as _Mod, Mul as _Mul, Power as _Power, Sub as _Sub, Bitand as _Bitand,\
     Bitor as _Bitor, Bitxor as _Bitxor, LeftShift as _LeftShift,\
     RightShift as _RightShift, \
     Slice as _Slice, GenExprFor as _GenExprFor

from logilab.astng.utils import ASTVisitor
from logilab.astng._exceptions import NodeRemoved, ASTNGError


# set missing accept methods
_AssList.accept = lambda self, visitor: visitor.visit_asslist(self)
_AssTuple.accept = lambda self, visitor: visitor.visit_asstuple(self)
_Printnl.accept = lambda self, visitor: visitor.visit_printnl(self)
_Slice.accept = lambda self, visitor: visitor.visit_slice(self)
_GenExprFor.accept = lambda self, visitor: visitor.visit_comprehension(self)
for boolopcls in (_And, _Or):
    boolopcls.accept = lambda self, visitor: visitor.visit_boolop(self)
for unaryopcls in (_UnaryAdd, _UnarySub, _Not,_Invert):
    unaryopcls.accept = lambda self, visitor: visitor.visit_unaryop(self)
for binopcls in (_Add, _Div, _FloorDiv, _Mod, _Mul, _Power, _Sub, _Bitand,
                 _Bitor, _Bitxor, _LeftShift, _RightShift):
    binopcls.accept = lambda self, visitor: visitor.visit_binop(self)

class BaseClass: pass

import logilab.astng.nodes as new


# introduced in python 2.5
From.level = 0 # will be overridden by instance attribute with py>=2.5

def native_repr_tree(node, indent='', _done=None):
    """enhanced compiler.ast tree representation"""
    if _done is None:
        _done = set()
    if node in _done:
        print ('loop in tree: %r (%s)' % (node, getattr(node, 'lineno', None)))
        return
    _done.add(node)
    print indent + "<%s>" % node.__class__
    indent += '    '
    if not hasattr(node, "__dict__"): # XXX
        return
    for field, attr in node.__dict__.items():
        if attr is None or field == "_proxied":
            continue
        if type(attr) is list:
            if not attr: continue
            print indent + field + ' ['
            for elt in attr:
                if type(elt) is tuple:
                    for val in elt:
                        native_repr_tree(val, indent, _done)
                else:
                    native_repr_tree(elt, indent, _done)
            print indent + ']'
            continue
        if isinstance(attr, Node):
            print indent + field
            native_repr_tree(attr, indent, _done)
        else:
            print indent + field,  repr(attr)


# some astng nodes unexistent in compiler #####################################

BinOp_OP_CLASSES = {_Add: '+',
              _Div: '/',
              _FloorDiv: '//',
              _Mod: '%',
              _Mul: '*',
              _Power: '**',
              _Sub: '-',
              _Bitand: '&',
              _Bitor: '|',
              _Bitxor: '^',
              _LeftShift: '<<',
              _RightShift: '>>'
              }
BinOp_BIT_CLASSES = {'&': _Bitand,
               '|': _Bitor,
               '^': _Bitxor
               }


BoolOp_OP_CLASSES = {_And: 'and',
              _Or: 'or'
              }


UnaryOp_OP_CLASSES = {_UnaryAdd: '+',
              _UnarySub: '-',
              _Not: 'not',
              _Invert: '~'
              }

def _extslice(dim):
    """introduce Index or Slice nodes depending on situation"""
    if dim.__class__ == Sliceobj:
        if len(dim.nodes) == 2:
            dim.nodes.append(None)
        return new.Slice(dim.nodes[0], dim.nodes[1], dim.nodes[2], dim.lineno)
    else:
        return new.Index([dim])


# modify __repr__ of all Nodes as they are not compatible with ASTNG ##########

def generic__repr__(self):
    """simple representation method to override compiler.ast's methods"""
    return "<%s at 0x%x>" % (self.__class__.__name__, id(self))

for value in ast.__dict__.values():
    try:
        if issubclass(value, ast.Node):
            value.__repr__ = generic__repr__
    except:
        pass
del ast

# we have to be able to instantiate Tuple, Dict and List without any argument #

def init_noargs(self, *args, **kwargs):
    if not (args or kwargs):
        self._orig_init([])
    else:
        self._orig_init(*args, **kwargs)

Tuple._orig_init = Tuple.__init__
Tuple.__init__ = init_noargs
List._orig_init = List.__init__
List.__init__ = init_noargs
Dict._orig_init = Dict.__init__
Dict.__init__ = init_noargs


# compiler rebuilder ##########################################################

def _init_else_node(node):
    """remove Stmt node if exists"""
    if node.else_:
        node.orelse = node.else_.nodes
    else:
        node.orelse = []
    del node.else_

def _nodify_args(parent, values):
    res = []
    for arg in values:
        if isinstance(arg, (tuple, list)):
            n = new.Tuple()
            # set .nodes, not .elts since this will be visited as a node coming
            # from compiler tree
            n.nodes = _nodify_args(n, arg)
        else:
            n = new.AssName(None, None)
            n.name = arg
        n.parent = parent
        n.fromlineno = parent.fromlineno
        n.tolineno = parent.fromlineno
        res.append(n)
    return res

def args_compiler_to_ast(node):
    # insert Arguments node
    if node.flags & 8:
        kwarg = node.argnames.pop()
    else:
        kwarg = None
    if node.flags & 4:
        vararg = node.argnames.pop()
    else:
        vararg = None
    del node.flags
    args = _nodify_args(node, node.argnames)
    del node.argnames
    node.args = new.Arguments(args, node.defaults, vararg, kwarg)
    node.args.fromlineno = node.fromlineno
    try:
        node.args.tolineno = node.blockstart_tolineno
    except AttributeError: # lambda
        node.args.tolineno = node.tolineno
    del node.defaults


def _filter_none(node):
    """transform Const(None) to None"""
    if isinstance(node, Const) and node.value is None:
        return None
    else:
        return node

class TreeRebuilder(ASTVisitor):
    """Rebuilds the compiler tree to become an ASTNG tree"""

    def __init__(self, rebuild_visitor):
        self.visitor = rebuild_visitor


    def insert_delstmt_if_necessary(self, node):
        """insert a Delete statement node if necessary

        return True if we have mutated a AssTuple into a Delete
        """
        assign_nodes = (new.Assign, new.With, new.For, new.ExceptHandler, new.Delete, new.AugAssign)
        if isinstance(node.parent, assign_nodes) or not (
            node.parent.is_statement or isinstance(node.parent, new.Module)):
            return False
        if isinstance(node, AssTuple): # replace node by Delete
            node.__class__ = new.Delete
            node.targets = node.nodes
            del node.nodes
            stmt = node
        else: # introduce new Stmt node
            stmt = new.Delete()
            node.parent.replace(node, stmt)
            stmt.fromlineno = node.fromlineno
            stmt.tolineno = node.tolineno
            node.parent = stmt
            stmt.targets = [node]
        self.visitor.asscontext = stmt
        return stmt is node

    # scoped nodes #######################################################

    def visit_function(self, node):
        # remove Stmt node
        node.body = node.code.nodes
        del node.code
        args_compiler_to_ast(node)

    def visit_lambda(self, node):
        node.body = node.code
        del node.code
        args_compiler_to_ast(node)

    def visit_class(self, node):
        # remove Stmt node
        node.body = node.code.nodes
        del node.code

    def visit_module(self, node):
        # remove Stmt node
        node.body = node.node.nodes
        del node.node
        return True

    #  other visit_<node> #####################################################

    def visit_assattr(self, node):
        if node.flags == 'OP_DELETE':
            self.insert_delstmt_if_necessary(node)
            node.__class__ = new.DelAttr
        del node.flags

    def visit_assign(self, node):
        node.value = node.expr
        node.targets = node.nodes
        del node.nodes, node.expr

    def visit_asslist(self, node):
        self.insert_delstmt_if_necessary(node)
        node.__class__ = new.List
        self.visit_list(node)

    def visit_asstuple(self, node):
        if not self.insert_delstmt_if_necessary(node):
            node.__class__ = new.Tuple
            self.visit_tuple(node)

    def visit_assname(self, node):
        if node.flags == 'OP_DELETE':
            self.insert_delstmt_if_necessary(node)
            node.__class__ = new.DelName
        del node.flags

    def visit_augassign(self, node):
        node.value = node.expr
        del node.expr
        node.target = node.node
        del node.node

    def visit_backquote(self, node):
        node.value = node.expr
        del node.expr

    def visit_binop(self, node):
        node.op = BinOp_OP_CLASSES[node.__class__]
        node.__class__ = new.BinOp # XXX just instanciate the node
        if node.op in ('&', '|', '^'):
            node.right = node.nodes[-1]
            bitop = BinOp_BIT_CLASSES[node.op]
            if len(node.nodes) > 2:
                node.left = bitop(node.nodes[:-1])
            else:
                node.left = node.nodes[0]
            del node.nodes

    def visit_boolop(self, node):
        node.op = BoolOp_OP_CLASSES[node.__class__]
        node.__class__ = new.BoolOp # XXX just instanciate the node
        node.values = node.nodes
        del node.nodes

    def visit_callfunc(self, node):
        node.func = node.node
        node.starargs = node.star_args
        node.kwargs = node.dstar_args
        del node.node, node.star_args, node.dstar_args

    def visit_compare(self, node):
        node.left = node.expr
        del node.expr

    def visit_discard(self, node):
        node.value = node.expr
        del node.expr
        if node.lineno is None:
            # remove dummy Discard introduced when a statement
            # is ended by a semi-colon
            node.parent.child_sequence(node).remove(node)
            raise NodeRemoved

    def visit_exec(self, node):
        node.locals, node.globals = node.globals, node.locals

    def visit_for(self, node):
        node.target = node.assign
        del node.assign
        node.iter = node.list
        del node.list
        node.body = node.body.nodes
        _init_else_node(node)

    def visit_genexpr(self, node):
        # remove GenExprInner node
        node.elt = node.code.expr
        node.generators = node.code.quals
        del node.code

    def visit_getattr(self, node):
        if isinstance(self.visitor.asscontext, new.AugAssign):
            node.__class__ = new.AssAttr

    def visit_if(self, node):
        node.test, body = node.tests[0]
        node.body = body.nodes
        if node.tests[1:]:
            # create If node and put it in orelse
            # rely on the fact that the new If node will be visited
            # as well until no more tests remains
            subnode = If(node.tests[1:], node.else_ )
            subnode.fromlineno = node.tests[1][0].fromlineno
            subnode.tolineno = node.tests[1][1].nodes[-1].tolineno
            subnode.blockstart_tolineno = node.tests[1][0].tolineno
            del node.else_
            node.orelse = [subnode]
        else: # handle orelse
            _init_else_node(node)
        del node.tests

    def visit_list(self, node):
        node.elts = node.nodes
        del node.nodes

    def visit_keyword(self, node):
        node.value = node.expr
        node.arg = node.name
        del node.expr, node.name

    def visit_listcomp(self, node):
        node.elt = node.expr
        node.generators = node.quals
        del node.expr, node.quals

    def visit_name(self, node):
        if isinstance(self.visitor.asscontext, new.AugAssign):
            node.__class__ = new.AssName

    def visit_comprehension(self, node):
        if hasattr(node, "list"):
            # ListCompFor
            node.iter = node.list
            del node.list
        else: # GenExprFor
            node.__class__ = new.Comprehension
        node.target = node.assign
        if node.ifs:
            node.ifs = [iff.test for iff in node.ifs ]
        del node.assign

    def visit_print(self, node):
        node.values = node.nodes
        del node.nodes
        node.nl = False

    def visit_printnl(self, node):
        node.__class__ = Print
        node.values = node.nodes
        del node.nodes
        node.nl = True

    def visit_raise(self, node):
        node.type = node.expr1
        node.inst = node.expr2
        node.tback = node.expr3
        del node.expr1, node.expr2, node.expr3

    def visit_return(self, node):
        """visit Return: filter None Const"""
        node.value = _filter_none( node.value )

    def visit_slice(self, node):
        """visit slice"""
        # /!\ Careful :
        # if the node comes from compiler, it is actually an astng.Subscript
        # with only 'lower' and 'upper' attributes; no 'step'.
        # However we want its attribute 'slice' to be a astng.Slice;
        # hence node.slice will be visited here as a node's child
        # furthermore, some child nodes of Subscript are also Slice objects
        #
        # logilab.astng._nodes_compiler.Slice introduced before :
        if node.__class__ is Slice:
            return
        # compiler.ast.Slice :
        if node.flags == 'OP_DELETE':
            self.insert_delstmt_if_necessary(node)
        else:
            assert node.flags in ('OP_APPLY', 'OP_ASSIGN')
        node.__class__ = Subscript # XXX what should we do here ?
        node.value = node.expr
        node.slice = ew.Slice(node.lower, node.upper, None,
                           node.lineno)
        del node.expr, node.lower, node.upper, node.flags

    def visit_subscript(self, node):
        if node.flags == 'OP_DELETE':
            self.insert_delstmt_if_necessary(node)
        node.value = node.expr
        if [n for n in node.subs if isinstance(n, Sliceobj)]:
            subs = node.subs
            if len(node.subs) == 1:# Slice
                subs = node.subs[0].nodes
                node.slice = new.Slice(subs[0], subs[1], subs[2], node.lineno)
            else: # ExtSlice
                node.slice = new.ExtSlice()
                node.dims = [_extslice(n) for n in node.subs]
        else: # Index
            node.slice = new.Index(node.subs)
        del node.expr, node.subs, node.flags

    def visit_tryexcept(self, node):
        # remove Stmt node
        node.body = node.body.nodes
        # remove Stmt node
        node.handlers = [new.ExceptHandler(exctype, excobj, body.nodes)
                        for exctype, excobj, body in node.handlers]
        _init_else_node(node)

    def visit_tryfinally(self, node):
        # remove Stmt nodes
        node.body = node.body.nodes
        node.finalbody = node.final.nodes
        del node.final

    visit_tuple = visit_list

    def visit_unaryop(self, node):
        node.op = UnaryOp_OP_CLASSES[node.__class__]
        node.__class__ = new.UnaryOp # XXX just instanciate the node
        node.operand = node.expr
        del node.expr

    def visit_while(self, node):
        node.body = node.body.nodes
        _init_else_node(node)

    def visit_yield(self, node):
        """visit yield : add parent Discard node"""
        if not isinstance(node.parent, new.Discard):
            stmt = new.Discard(None)
            del stmt.expr
            stmt.value = node
            stmt.fromlineno = node.fromlineno
            stmt.tolineno = node.tolineno
            node.parent.replace(node, stmt)
            node.parent = stmt



