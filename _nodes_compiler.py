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

import logilab.astng.nodes as new
from logilab.astng.rebuilder import RebuildVisitor


class BaseClass: pass


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


class TreeRebuilder(RebuildVisitor):
    """Rebuilds the compiler tree to become an ASTNG tree"""

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
        self.asscontext = stmt
        return stmt is node

    def visit_arguments(self, node):
        """visit an Arguments node by returning a fresh instance of it"""
        newnode = new.Arguments()
        newnode.args = [self.visit(child, node) for child in node.args]
        newnode.defaults = [self.visit(child, node) for child in node.defaults]
        return newnode

    def visit_assattr(self, node):
        """visit an AssAttr node by returning a fresh instance of it"""
        newnode = new.AssAttr()
        newnode.expr = self.visit(node.expr, node)
        # XXX old code
        if node.flags == 'OP_DELETE':
            self.insert_delstmt_if_necessary(node)
            node.__class__ = DelAttr
        del node.flags
        # end old
        return newnode

    def visit_assname(self, node):
        """visit an AssName node by returning a fresh instance of it"""
        newnode = new.AssName()
        # XXX old code
        if node.flags == 'OP_DELETE':
            self.insert_delstmt_if_necessary(node)
            node.__class__ = DelName
        del node.flags
        # end old
        return newnode

    def visit_assert(self, node):
        """visit an Assert node by returning a fresh instance of it"""
        newnode = new.Assert()
        newnode.test = self.visit(node.test, node)
        newnode.fail = self.visit(node.fail, node)
        return newnode

    def visit_assign(self, node):
        """visit an Assign node by returning a fresh instance of it"""
        newnode = new.Assign()
        newnode.targets = [self.visit(child, node) for child in node.targets]
        newnode.value = self.visit(node.value, node)
        # XXX old code
        node.value = node.expr
        node.targets = node.nodes
        del node.nodes, node.expr
        # end old
        return newnode

    def visit_augassign(self, node):
        """visit an AugAssign node by returning a fresh instance of it"""
        newnode = new.AugAssign()
        newnode.target = self.visit(node.target, node)
        newnode.value = self.visit(node.value, node)
        # XXX old code
        node.value = node.expr
        del node.expr
        node.target = node.node
        del node.node
        # end old
        return newnode


   def visit_backquote(self, node):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = new.Backquote()
        newnode.value = self.visit(node.value, node)
        # XXX old code
        node.value = node.expr
        del node.expr
        # end old
        return newnode

    def visit_binop(self, node):
        """visit a BinOp node by returning a fresh instance of it"""
        newnode = new.BinOp()
        newnode.left = self.visit(node.left, node)
        newnode.right = self.visit(node.right, node)
        # XXX old code
        node.op = BinOp.OP_CLASSES[node.__class__]
        node.__class__ = BinOp
        if node.op in ('&', '|', '^'):
            node.right = node.nodes[-1]
            bitop = BinOp.BIT_CLASSES[node.op]
            if len(node.nodes) > 2:
                node.left = bitop(node.nodes[:-1])
            else:
                node.left = node.nodes[0]
            del node.nodes
        # end old
        return newnode

    def visit_boolop(self, node):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = new.BoolOp()
        newnode.values = [self.visit(child, node) for child in node.values]
        # XXX old code
        node.op = BoolOp.OP_CLASSES[node.__class__]
        node.__class__ = BoolOp
        node.values = node.nodes
        del node.nodes
        # end old
        return newnode

    def visit_break(self, node):
        """visit a Break node by returning a fresh instance of it"""
        newnode = new.Break()
        return newnode

    def visit_callfunc(self, node):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = new.CallFunc()
        newnode.func = self.visit(node.func, node)
        newnode.args = [self.visit(child, node) for child in node.args]
        newnode.starargs = [self.visit(child, node) for child in node.starargs]
        newnode.kwargs = [self.visit(child, node) for child in node.kwargs]
        # XXX old code
        node.func = node.node
        node.starargs = node.star_args
        node.kwargs = node.dstar_args
        del node.node, node.star_args, node.dstar_args
        # end old
        return newnode

    def visit_class(self, node):
        """visit a Class node by returning a fresh instance of it"""
        newnode = new.Class()
        newnode.bases = [self.visit(child, node) for child in node.bases]
        newnode.body = [self.visit(child, node) for child in node.body]
        # XXX old code
        node.body = node.code.nodes
        del node.code
        # end old
        return newnode

    def visit_compare(self, node):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = new.Compare()
        newnode.left = self.visit(node.left, node)
        newnode.ops = [self.visit(child, node) for child in node.ops]
        # XXX old code
        node.left = node.expr
        del node.expr
        # end old
        return newnode

    def visit_comprehension(self, node):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = new.Comprehension()
        newnode.target = self.visit(node.target, node)
        newnode.iter = self.visit(node.iter, node)
        newnode.ifs = [self.visit(child, node) for child in node.ifs]
        # XXX old code
        if hasattr(node, 'list'):
            # ListCompFor
            node.iter = node.list
            del node.list
        else: # GenExprFor
            node.__class__ = Comprehension
        node.target = node.assign
        if node.ifs:
            node.ifs = [iff.test for iff in node.ifs]
        del node.assign
        # end old
        return newnode

    def visit_const(self, node):
        """visit a Const node by returning a fresh instance of it"""
        newnode = new.Const()
        return newnode

    def visit_continue(self, node):
        """visit a Continue node by returning a fresh instance of it"""
        newnode = new.Continue()
        return newnode

    def visit_decorators(self, node):
        """visit a Decorators node by returning a fresh instance of it"""
        newnode = new.Decorators()
        newnode.nodes = [self.visit(child, node) for child in node.nodes]
        return newnode

    def visit_delattr(self, node):
        """visit a DelAttr node by returning a fresh instance of it"""
        newnode = new.DelAttr()
        newnode.expr = self.visit(node.expr, node)
        return newnode

    def visit_delname(self, node):
        """visit a DelName node by returning a fresh instance of it"""
        newnode = new.DelName()
        return newnode

    def visit_delete(self, node):
        """visit a Delete node by returning a fresh instance of it"""
        newnode = new.Delete()
        newnode.targets = [self.visit(child, node) for child in node.targets]
        return newnode

    def visit_dict(self, node):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = new.Dict()
        newnode.items = [self.visit(child, node) for child in node.items]
        return newnode

    def visit_discard(self, node):
        """visit a Discard node by returning a fresh instance of it"""
        newnode = new.Discard()
        newnode.value = self.visit(node.value, node)
        # XXX old code
        node.value = node.expr
        del node.expr
        if node.lineno is None:
            # remove dummy Discard introduced when a statement
            # is ended by a semi-colon
            node.parent.child_sequence(node).remove(node)
            raise NodeRemoved
        # end old
        return newnode

    def visit_ellipsis(self, node):
        """visit an Ellipsis node by returning a fresh instance of it"""
        newnode = new.Ellipsis()
        return newnode

    def visit_emptynode(self, node):
        """visit an EmptyNode node by returning a fresh instance of it"""
        newnode = new.EmptyNode()
        return newnode

    def visit_excepthandler(self, node):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = new.ExceptHandler()
        newnode.type = self.visit(node.type, node)
        newnode.name = self.visit(node.name, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        return newnode

    def visit_exec(self, node):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = new.Exec()
        newnode.expr = self.visit(node.expr, node)
        newnode.globals = [self.visit(child, node) for child in node.globals]
        newnode.locals = [self.visit(child, node) for child in node.locals]
        # XXX old code
        (node.locals, node.globals) = (node.globals, node.locals)
        # end old
        return newnode

    def visit_extslice(self, node):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = new.ExtSlice()
        newnode.dims = self.visit(node.dims, node)
        return newnode

    def visit_for(self, node):
        """visit a For node by returning a fresh instance of it"""
        newnode = new.For()
        newnode.target = self.visit(node.target, node)
        newnode.iter = self.visit(node.iter, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = self.visit(node.orelse, node)
        # XXX old code
        node.target = node.assign
        del node.assign
        node.iter = node.list
        del node.list
        node.body = node.body.nodes
        _init_else_node(node)
        # end old
        return newnode

    def visit_from(self, node):
        """visit a From node by returning a fresh instance of it"""
        newnode = new.From(node.modname, nodes.names)
        return newnode


    def visit_function(self, node):
        """visit a Function node by returning a fresh instance of it"""
        newnode = new.Function()
        newnode.decorators = [self.visit(child, node) for child in node.decorators]
        newnode.args = [self.visit(child, node) for child in node.args]
        newnode.body = [self.visit(child, node) for child in node.body]
        # XXX old code
        node.body = node.code.nodes
        del node.code
        args_compiler_to_ast(node)
        # end old
        return newnode

    def visit_genexpr(self, node):
        """visit a GenExpr node by returning a fresh instance of it"""
        newnode = new.GenExpr()
        newnode.elt = self.visit(node.elt, node)
        newnode.generators = [self.visit(child, node) for child in node.generators]
        # XXX old code
        # remove GenExprInner node
        node.elt = node.code.expr
        node.generators = node.code.quals
        del node.code
        # end old
        return newnode

    def visit_getattr(self, node):
        """visit a Getattr node by returning a fresh instance of it"""
        newnode = new.Getattr()
        newnode.expr = self.visit(node.expr, node)
        # XXX old code
        if isinstance(self.visitor.asscontext, AugAssign):
            node.__class__ = AssAttr
        # end old
        return newnode

    def visit_global(self, node):
        """visit a Global node by returning a fresh instance of it"""
        newnode = new.Global()
        return newnode


    def visit_if(self, node):
        """visit an If node by returning a fresh instance of it"""
        newnode = new.If()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = self.visit(node.orelse, node)
        # XXX old code
        (node.test, body) = node.tests[0]
        node.body = body.nodes
        if node.tests[1:]:
            # create If node and put it in orelse
            # rely on the fact that the new If node will be visited
            # as well until no more tests remains
            subnode = If(node.tests[1:], node.else_)
            subnode.fromlineno = node.tests[1][0].fromlineno
            subnode.tolineno = node.tests[1][1].nodes[-1].tolineno
            subnode.blockstart_tolineno = node.tests[1][0].tolineno
            del node.else_
            node.orelse = [subnode]
        else: # handle orelse
            _init_else_node(node)
        del node.tests
        # end old
        return newnode

    def visit_ifexp(self, node):
        """visit an IfExp node by returning a fresh instance of it"""
        newnode = new.IfExp()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = self.visit(node.orelse, node)
        return newnode

    def visit_import(self, node):
        """visit an Import node by returning a fresh instance of it"""
        newnode = new.Import()
        return newnode

    def visit_index(self, node):
        """visit an Index node by returning a fresh instance of it"""
        newnode = new.Index()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_keyword(self, node):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = new.Keyword()
        newnode.value = self.visit(node.value, node)
        # XXX old code
        node.value = node.expr
        node.arg = node.name
        del node.expr, node.name
        # end old
        return newnode

    def visit_lambda(self, node):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = new.Lambda()
        newnode.args = [self.visit(child, node) for child in node.args]
        newnode.body = [self.visit(child, node) for child in node.body]
        # XXX old code
        node.body = node.code
        del node.code
        args_compiler_to_ast(node)
        # end old
        return newnode

    def visit_list(self, node):
        """visit a List node by returning a fresh instance of it"""
        newnode = new.List()
        newnode.elts = [self.visit(child, node) for child in node.elts]
        # XXX old code
        node.elts = node.nodes
        del node.nodes
        # end old
        return newnode

    def visit_listcomp(self, node):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = new.ListComp()
        newnode.elt = self.visit(node.elt, node)
        newnode.generators = [self.visit(child, node) for child in node.generators]
        # XXX old code
        node.elt = node.expr
        node.generators = node.quals
        del node.expr, node.quals
        # end old
        return newnode

    def visit_module(self, node):
        """visit a Module node by returning a fresh instance of it"""
        newnode = new.Module()
        newnode.body = [self.visit(child, node) for child in node.body]
        # XXX old code
        node.body = node.node.nodes
        del node.node
        return True
        # end old
        return newnode

    def visit_name(self, node):
        """visit a Name node by returning a fresh instance of it"""
        newnode = new.Name()
        # XXX old code
        if isinstance(self.visitor.asscontext, AugAssign):
            node.__class__ = AssName
        # end old
        return newnode

    def visit_pass(self, node):
        """visit a Pass node by returning a fresh instance of it"""
        newnode = new.Pass()
        return newnode

    def visit_print(self, node):
        """visit a Print node by returning a fresh instance of it"""
        newnode = new.Print()
        newnode.dest = self.visit(node.dest, node)
        newnode.values = [self.visit(child, node) for child in node.values]
        # XXX old code
        node.values = node.nodes
        del node.nodes
        node.nl = False
        # end old
        return newnode

    def visit_raise(self, node):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise()
        newnode.type = self.visit(node.type, node)
        newnode.inst = self.visit(node.inst, node)
        newnode.tback = self.visit(node.tback, node)
        # XXX old code
        node.type = node.expr1
        node.inst = node.expr2
        node.tback = node.expr3
        del node.expr1, node.expr2, node.expr3
        # end old
        return newnode

    def visit_return(self, node):
        """visit a Return node by returning a fresh instance of it"""
        newnode = new.Return()
        newnode.value = self.visit(node.value, node)
        # XXX old code
        node.value = _filter_none(node.value)
        # end old
        return newnode

    def visit_slice(self, node):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = new.Slice()
        newnode.lower = self.visit(node.lower, node)
        newnode.upper = self.visit(node.upper, node)
        newnode.step = self.visit(node.step, node)
        # XXX old code
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
        node.__class__ = Subscript
        node.value = node.expr
        node.slice = Slice(node.lower, node.upper, None, node.lineno)
        del node.expr, node.lower, node.upper, node.flags
        # end old
        return newnode

    def visit_subscript(self, node):
        """visit a Subscript node by returning a fresh instance of it"""
        newnode = new.Subscript()
        newnode.value = self.visit(node.value, node)
        newnode.slice = self.visit(node.slice, node)
        # XXX old code
        if node.flags == 'OP_DELETE':
            self.insert_delstmt_if_necessary(node)
        node.value = node.expr
        if [n for n in node.subs if isinstance(n, Sliceobj)]:
            subs = node.subs
            if len(node.subs) == 1:
                subs = node.subs[0].nodes
                node.slice = Slice(subs[0], subs[1], subs[2], node.lineno)
            else: # ExtSlice
                node.slice = ExtSlice(node.subs)
        else: # Index
            node.slice = Index(node.subs)
        del node.expr, node.subs, node.flags
        # end old
        return newnode


    def visit_tryexcept(self, node):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = new.TryExcept()
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.handlers = [self.visit(child, node) for child in node.handlers]
        newnode.orelse = self.visit(node.orelse, node)
        # XXX old code
        # remove Stmt node
        node.body = node.body.nodes
        node.handlers = [ExceptHandler(exctype, excobj, body, node) for (exctype, excobj, body) in node.handlers]
        _init_else_node(node)
        # end old
        return newnode

    def visit_tryfinally(self, node):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = new.TryFinally()
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.finalbody = self.visit(node.finalbody, node)
        # XXX old code
        node.body = node.body.nodes
        node.finalbody = node.final.nodes
        del node.final
        # end old
        return newnode

    def visit_tuple(self, node):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Tuple()
        newnode.elts = [self.visit(child, node) for child in node.elts]
        return newnode

    def visit_unaryop(self, node):
        """visit an UnaryOp node by returning a fresh instance of it"""
        newnode = new.UnaryOp()
        newnode.operand = self.visit(node.operand, node)
        # XXX old code
        node.op = UnaryOp.OP_CLASSES[node.__class__]
        node.__class__ = UnaryOp
        node.operand = node.expr
        del node.expr
        # end old
        return newnode

    def visit_while(self, node):
        """visit a While node by returning a fresh instance of it"""
        newnode = new.While()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = self.visit(node.orelse, node)
        # XXX old code
        node.body = node.body.nodes
        _init_else_node(node)
        # end old
    def visit_with(self, node):
        """visit a With node by returning a fresh instance of it"""
        newnode = new.With()
        newnode.expr = self.visit(node.expr, node)
        newnode.vars = self.visit(node.vars, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        return newnode

    def visit_yield(self, node):
        """visit a Yield node by returning a fresh instance of it"""
        newnode = new.Yield()
        newnode.value = self.visit(node.value, node)
        return newnode


