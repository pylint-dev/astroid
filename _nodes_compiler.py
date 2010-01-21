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
from compiler.ast import And as _And, Or as _Or,\
     UnaryAdd as _UnaryAdd, UnarySub as _UnarySub, Not as _Not,\
     Invert as _Invert, Add as _Add, Div as _Div, FloorDiv as _FloorDiv,\
     Mod as _Mod, Mul as _Mul, Power as _Power, Sub as _Sub, Bitand as _Bitand,\
     Bitor as _Bitor, Bitxor as _Bitxor, LeftShift as _LeftShift,\
     RightShift as _RightShift, \
     Slice as _Slice, GenExprFor as _GenExprFor

from logilab.astng.utils import ASTVisitor
from logilab.astng._exceptions import NodeRemoved, ASTNGError

from logilab.astng import nodes as new
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


# compiler rebuilder ##########################################################

def _nodify_args(parent, values):
    res = []
    for arg in values:
        if isinstance(arg, (tuple, list)):
            n = new.Tuple()
            n.elts = _nodify_args(n, arg)
        else:
            n = new.AssName()
            assert isinstance(arg, basestring)
            n.name = arg
        n.parent = parent
        try: # TODO
            n.fromlineno = parent.fromlineno
            n.tolineno = parent.fromlineno
        except AttributeError:
            pass
        res.append(n)
    return res

def args_compiler_to_ast(newnode, node):
    # insert Arguments node
    if node.flags & 8:
        kwarg = node.argnames.pop()
    else:
        kwarg = None
    if node.flags & 4:
        vararg = node.argnames.pop()
    else:
        vararg = None
    args = _nodify_args(node, node.argnames)
    newnode.args = new.Arguments(args, vararg, kwarg)
    newnode.args.fromlineno = node.fromlineno
    try:
        newnode.args.tolineno = newnode.blockstart_tolineno
    except AttributeError: # lambda
        newnode.args.tolineno = node.tolineno


def _filter_none(node):
    """transform Const(None) to None"""
    if isinstance(node, Const) and node.value is None:
        return None
    else:
        return node


class TreeRebuilder(RebuildVisitor):
    """Rebuilds the compiler tree to become an ASTNG tree"""

    def _init_else_node(self, node):
        """visit else block; replace None by empty list"""
        if not node.else_:
            return []
        return [self.visit(child, node) for child in node.else_.nodes]

    def _check_del_node(self, node, targets):
        """insert a Delete node if necessary.

        As for assignments we have a Assign (or For or ...) node, this method
        is only called in delete contexts. Hence we return a Delete node"""
        if self.asscontext is None:
            self.asscontext = "Del"
            newnode = new.Delete()
            newnode.targets = [self.visit(elt, newnode) for elt in targets]
            self.asscontext = None
            return newnode
        else:
            # this will trigger the visit_ass* methods to create the right nodes
            return False

    def visit_arguments(self, node):
        """visit an Arguments node by returning a fresh instance of it"""
        newnode = new.Arguments()
        newnode.args = [self.visit(child, node) for child in node.args]
        newnode.defaults = [self.visit(child, node) for child in node.defaults]
        return newnode

    def visit_assattr(self, node):
        """visit an AssAttr node by returning a fresh instance of it"""
        delnode = self._check_del_node(node, [node])
        if delnode:
            return delnode
        elif self.asscontext == "Del":
            newnode = self.visit_delattr(node)
        elif self.asscontext == "Ass":
            newnode = new.AssAttr()
            newnode.expr = self.visit(node.expr, node)
            newnode.attrname = node.attrname
        self._delayed['assattr'].append(newnode)
        return newnode

    def visit_assname(self, node):
        """visit an AssName node by returning a fresh instance of it"""
        delnode = self._check_del_node(node, [node])
        if delnode:
            return delnode
        elif self.asscontext == "Del":
            newnode = self.visit_delname(node)
            self._save_assigment(newnode)
        elif self.asscontext == "Ass":
            assert node.flags == 'OP_ASSIGN'
            newnode = new.AssName()
            newnode.name = node.name
            self._save_assigment(newnode)
        return newnode

    def visit_assert(self, node):
        """visit an Assert node by returning a fresh instance of it"""
        newnode = new.Assert()
        newnode.test = self.visit(node.test, node)
        newnode.fail = self.visit(node.fail, node)
        return newnode

    def _visit_assign(self, node):
        """visit an Assign node by returning a fresh instance of it"""
        newnode = new.Assign()
        self.asscontext = 'Ass'
        newnode.targets = [self.visit(child, node) for child in node.nodes]
        newnode.value = self.visit(node.expr, node)
        self.asscontext = None
        return newnode

    def visit_asslist(self, node):
        # FIXME : use self._check_del_node(node, [node]) more precise ?
        delnode = self._check_del_node(node, node.nodes)
        if delnode:
            return delnode
        return self.visit_list(node)

    def visit_asstuple(self, node):
        delnode = self._check_del_node(node, node.nodes)
        if delnode:
            return delnode
        return self.visit_tuple(node)
            

    def visit_augassign(self, node):
        """visit an AugAssign node by returning a fresh instance of it"""
        newnode = new.AugAssign()
        newnode.target = self.visit(node.node, node)
        newnode.op = node.op
        newnode.value = self.visit(node.expr, node)
        return newnode

    def visit_backquote(self, node):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = new.Backquote()
        newnode.value = self.visit(node.expr, node)
        return newnode

    def visit_binop(self, node):
        """visit a BinOp node by returning a fresh instance of it"""
        newnode = new.BinOp()
        newnode.op = BinOp_OP_CLASSES[node.__class__]
        if newnode.op in ('&', '|', '^'):
            newnode.right = self.visit(node.nodes[-1], node)
            bitop = BinOp_BIT_CLASSES[node.op]
            if len(node.nodes) > 2:
                # create a bitop node on the fly and visit it:
                newnode.left = self.visit(bitop(node.nodes[:-1]), node)
            else:
                newnode.left = self.visit(node.nodes[0], node)
        else:
            newnode.left = self.visit(node.left, node)
            newnode.right = self.visit(node.right, node)
        return newnode

    def visit_boolop(self, node):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = new.BoolOp()
        newnode.values = [self.visit(child, node) for child in node.nodes]
        node.op = BoolOp_OP_CLASSES[node.__class__]
        return newnode

    def visit_break(self, node):
        """visit a Break node by returning a fresh instance of it"""
        newnode = new.Break()
        return newnode

    def visit_callfunc(self, node):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = new.CallFunc()
        newnode.func = self.visit(node.node, node)
        newnode.args = [self.visit(child, node) for child in node.args]
        if node.star_args:
            newnode.starargs = self.visit(node.star_args, node)
        if node.dstar_args:
            newnode.kwargs = self.visit(node.dstar_args, node)
        return newnode

    def _visit_class(self, node):
        """visit a Class node by returning a fresh instance of it"""
        newnode = new.Class()
        newnode.bases = [self.visit(child, node) for child in node.bases]
        newnode.body = [self.visit(child, node) for child in node.code.nodes]
        newnode.doc = node.doc
        return newnode

    def visit_compare(self, node):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = new.Compare()
        newnode.left = self.visit(node.expr, node)
        newnode.ops = [self.visit(child, node) for child in node.ops]
        return newnode

    def visit_comprehension(self, node):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = new.Comprehension()
        newnode.target = self.visit(node.assign, node)
        if hasattr(node, 'list'):# ListCompFor
            iters = node.list
        else:# GenExprFor
            iters = node.iter
        newnode.iter = self.visit(iters, node)
        if node.ifs:
            newnode.ifs = [self.visit(iff.test, node) for iff in node.ifs]
        else:
            newnode.ifs = []
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
        newnode.attrname = node.attrname
        return newnode

    def visit_delname(self, node):
        """visit a DelName node by returning a fresh instance of it"""
        newnode = new.DelName()
        newnode.name = node.name
        return newnode

    def visit_dict(self, node):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = new.Dict()
        newnode.items = [self.visit(child, node) for child in node.items]
        return newnode

    def visit_discard(self, node):
        """visit a Discard node by returning a fresh instance of it"""
        newnode = new.Discard()
        self.asscontext = "Dis"
        newnode.value = self.visit(node.expr, node)
        # TODO : remove dummy Discard
        '''
        if node.lineno is None:
            # remove dummy Discard introduced when a statement
            # is ended by a semi-colon
            newnode.parent.child_sequence(newnode).remove(newnode)
            raise NodeRemoved
        '''
        self.asscontext = None
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
        newnode.globals = self.visit(node.locals, node)
        newnode.locals = self.visit(node.globals, node)
        return newnode

    def visit_extslice(self, node):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = new.ExtSlice()
        newnode.dims = [self.visit(dim, node) for dim in node.subs]
        self.set_infos(newnode, node)
        return newnode

    def visit_for(self, node):
        """visit a For node by returning a fresh instance of it"""
        newnode = new.For()
        self.asscontext = "Ass"
        newnode.target = self.visit(node.assign, node)
        self.asscontext = None
        newnode.iter = self.visit(node.list, node)
        newnode.body = [self.visit(child, node) for child in node.body.nodes]
        newnode.orelse = self._init_else_node(node)
        return newnode

    def visit_from(self, node):
        """visit a From node by returning a fresh instance of it"""
        newnode = new.From(node.modname, node.names)
        return newnode


    def _visit_function(self, node):
        """visit a Function node by returning a fresh instance of it"""
        newnode = new.Function()
        newnode.decorators = self.visit(node.decorators, node)
        newnode.body = [self.visit(child, node) for child in node.code.nodes]
        newnode.doc = node.doc
        args_compiler_to_ast(newnode, node)
        newnode.args.defaults = [self.visit(n, newnode.args) for n in node.defaults]
        return newnode

    def visit_genexpr(self, node):
        """visit a GenExpr node by returning a fresh instance of it"""
        newnode = new.GenExpr()
        # remove GenExprInner node
        newnode.elt = self.visit(node.code.expr, node)
        newnode.generators = [self.visit(n, node) for n in node.code.quals]
        return newnode

    def visit_getattr(self, node):
        """visit a Getattr node by returning a fresh instance of it"""
        newnode = new.Getattr()
        if isinstance(self.asscontext, AugAssign):
            newnode = new.AssAttr()
        newnode.expr = self.visit(node.expr, node)
        newnode.attrname = node.attrname
        return newnode
        
    def visit_if(self, node):
        """visit an If node by returning a fresh instance of it"""
        newnode = subnode = new.If()
        test, body = node.tests[0]
        newnode.test = self.visit(test, node)
        newnode.body = [self.visit(child, node) for child in body.nodes]
        for test, body in node.tests[1:]:# this represents 'elif'
            # create successively If nodes and put it in orelse of the previous
            parent, subnode = subnode, new.If()
            subnode.parent = parent
            subnode.fromlineno = node.tests[1][0].fromlineno
            subnode.tolineno = node.tests[1][1].nodes[-1].tolineno
            subnode.blockstart_tolineno = node.tests[1][0].tolineno
            subnode.test = self.visit(test, 0)
            subnode.body = [self.visit(child, 0) for child in body.nodes]
            parent.orelse = [subnode]
            self.set_infos(parent, node)
        # the last subnode gets the else block:
        subnode.orelse = self._init_else_node(node)
        self.set_infos(subnode, node)
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
        newnode.names = node.names
        return newnode

    def visit_index(self, node):
        """visit an Index node by returning a fresh instance of it"""
        newnode = new.Index()
        newnode.value = self.visit(node.subs[0], node)
        self.set_infos(newnode, node)
        return newnode

    def visit_keyword(self, node):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = new.Keyword()
        newnode.value = self.visit(node.expr, node)
        newnode.arg = node.name
        return newnode

    def visit_lambda(self, node):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = new.Lambda()
        newnode.body = self.visit(node.code, node)
        args_compiler_to_ast(newnode, node)
        newnode.args.defaults = [self.visit(n, newnode.args) for n in node.defaults]
        return newnode

    def visit_list(self, node):
        """visit a List node by returning a fresh instance of it"""
        newnode = new.List()
        newnode.elts = [self.visit(child, node) for child in node.nodes]
        return newnode

    def visit_listcomp(self, node):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = new.ListComp()
        newnode.elt = self.visit(node.expr, node)
        newnode.generators = [self.visit(child, node) for child in node.quals]
        return newnode

    def _visit_module(self, node):
        """visit a Module node by returning a fresh instance of it"""
        newnode = new.Module()
        newnode.doc = node.doc
        newnode.body = [self.visit(child, node) for child in node.node.nodes]
        return newnode

    def _visit_name(self, node):
        """visit a Name node by returning a fresh instance of it"""
        if isinstance(self.asscontext, AugAssign):
            newnode = AssName()
        else:
           newnode = new.Name()
        newnode.name = node.name
        return newnode

    def visit_print(self, node):
        """visit a Print node by returning a fresh instance of it"""
        newnode = new.Print()
        newnode.dest = self.visit(node.dest, node)
        newnode.values = [self.visit(child, node) for child in node.nodes]
        newnode.nl = False
        return newnode

    def visit_printnl(self, node):
        newnode = self.visit_print(node)
        newnode.nl = True
        return newnode

    def visit_raise(self, node):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise()
        newnode.type = self.visit(node.expr1, node)
        newnode.inst = self.visit(node.expr2, node)
        newnode.tback = self.visit(node.expr3, node)
        return newnode

    def visit_return(self, node):
        """visit a Return node by returning a fresh instance of it"""
        newnode = new.Return()
        newnode.value = self.visit(_filter_none(node.value), node)
        return newnode

    def visit_slice(self, node):
        """visit a compiler.Slice by returning a astng.Subscript"""
        # compiler.Slice nodes represent astng.Subscript nodes
        # the astng.Subscript node has a astng.Slice node as child
        delnode = self._check_del_node(node, [node])
        if delnode:
            return delnode
        newnode = new.Subscript()
        newnode.value = self.visit(node.expr, node)
        newnode.slice = self.visit_sliceobj(node, slice=True)
        self.set_infos(newnode, node)
        return newnode

    def visit_sliceobj(self, node, slice=False):
        """visit a Slice or Sliceobj; transform Sliceobj into a astng.Slice"""
        newnode = new.Slice()
        if slice:
            subs = [node.lower, node.upper, None]
        else:
            subs = node.nodes
            if len(subs) == 2:
                subs.append(None)
        newnode.lower = self.visit(_filter_none(subs[0]), node)
        newnode.upper = self.visit(_filter_none(subs[1]), node)
        newnode.step = self.visit(_filter_none(subs[2]), node)
        self.set_infos(newnode, node)
        return newnode

    def visit_subscript(self, node):
        """visit a Subscript node by returning a fresh instance of it"""
        delnode = self._check_del_node(node, [node])
        if delnode:
            return delnode
        newnode = new.Subscript()
        newnode.value = self.visit(node.expr, node)
        if [n for n in node.subs if isinstance(n, Sliceobj)]:
            if len(node.subs) == 1: # Sliceobj -> new.Slice
                newnode.slice = self.visit_sliceobj(node.subs[0])
            else: # ExtSlice
                newnode.slice = self.visit_extslice(node)
        else: # Index
            newnode.slice = self.visit_index(node)
        return newnode

    def visit_tryexcept(self, node):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = new.TryExcept()
        newnode.body = [self.visit(child, node) for child in node.body.nodes]
        newnode.handlers = [self._build_excepthandler(node, exctype, excobj, body)
                            for (exctype, excobj, body) in node.handlers]
        newnode.orelse = self._init_else_node(node)
        return newnode


    def visit_tryfinally(self, node):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = new.TryFinally()
        newnode.body = [self.visit(child, node) for child in node.body.nodes]
        newnode.finalbody = [self.visit(n, node) for n in node.final.nodes]
        return newnode

    def visit_tuple(self, node):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Tuple()
        newnode.elts = [self.visit(child, node) for child in node.nodes]
        return newnode

    def visit_unaryop(self, node):
        """visit an UnaryOp node by returning a fresh instance of it"""
        newnode = new.UnaryOp()
        newnode.operand = self.visit(node.expr, node)
        newnode.op = UnaryOp_OP_CLASSES[node.__class__]
        return newnode

    def visit_while(self, node):
        """visit a While node by returning a fresh instance of it"""
        newnode = new.While()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body.nodes]
        newnode.orelse = self._init_else_node(node)
        return newnode

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
        try:
            newnode.value = self.visit(node.value, node)
        except AttributeError:
            print "AttributeError Yield node.expr:", node.__dict__
            newnode.value = None
        if not isinstance(node.parent, Discard): # XXX waiting for better solution
            newnode, yield_node = new.Discard(), newnode
            newnode.value = yield_node
        newnode.fromlineno = node.fromlineno
        newnode.tolineno = node.tolineno
        return newnode

    
