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
"""python 2.5 builtin _ast compatibility module

:author:    Sylvain Thenault
:copyright: 2008-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2008-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

__docformat__ = "restructuredtext en"

#  "as is" nodes
from _ast import (Assert, Assign, AugAssign,
                  BinOp, BoolOp, Break,
                  Compare, Continue,
                  Delete, Dict,
                  Ellipsis, Exec, ExtSlice,
                  For,
                  Global,
                  If, IfExp, Import, Index,
                  Lambda, List, ListComp,
                  Module,
                  Name,
                  Pass, Print,
                  Raise, Return,
                  Slice, Subscript,
                  TryExcept, TryFinally, Tuple,
                  UnaryOp,
                  While, With,
                  Yield,
                  )
#  aliased nodes
from _ast import (AST as Node,
                  Attribute as Getattr,
                  Call as CallFunc,
                  ClassDef as Class,
                  Expr as Discard,
                  FunctionDef as Function,
                  GeneratorExp as GenExpr,
                  ImportFrom as From,
                  Repr as Backquote,
                  arguments as Arguments,
                  comprehension as Comprehension,
                  keyword as Keyword,
                  excepthandler as ExceptHandler,
                  )
# nodes which are not part of astng
from _ast import (
    # binary operators
    Add as _Add, Div as _Div, FloorDiv as _FloorDiv,
    Mod as _Mod, Mult as _Mult, Pow as _Pow, Sub as _Sub,
    BitAnd as _BitAnd, BitOr as _BitOr, BitXor as _BitXor,
    LShift as _LShift, RShift as _RShift,
    # logical operators
    And as _And, Or as _Or,
    # unary operators
    UAdd as _UAdd, USub as _USub, Not as _Not, Invert as _Invert,
    # comparison operators
    Eq as _Eq, Gt as _Gt, GtE as _GtE, In as _In, Is as _Is,
    IsNot as _IsNot, Lt as _Lt, LtE as _LtE, NotEq as _NotEq,
    NotIn as _NotIn,
    # other nodes which are not part of astng
    Num as _Num, Str as _Str, Load as _Load, Store as _Store, Del as _Del,
    )

from logilab.astng.utils import ASTVisitor
from logilab.astng import nodes as new

_BIN_OP_CLASSES = {_Add: '+',
                   _BitAnd: '&',
                   _BitOr: '|',
                   _BitXor: '^',
                   _Div: '/',
                   _FloorDiv: '//',
                   _Mod: '%',
                   _Mult: '*',
                   _Pow: '**',
                   _Sub: '-',
                   _LShift: '<<',
                   _RShift: '>>'}

_BOOL_OP_CLASSES = {_And: 'and',
                    _Or: 'or'}

_UNARY_OP_CLASSES = {_UAdd: '+',
                     _USub: '-',
                     _Not: 'not',
                     _Invert: '~'}

_CMP_OP_CLASSES = {_Eq: '==',
                   _Gt: '>',
                   _GtE: '>=',
                   _In: 'in',
                   _Is: 'is',
                   _IsNot: 'is not',
                   _Lt: '<',
                   _LtE: '<=',
                   _NotEq: '!=',
                   _NotIn: 'not in'}


def _init_set_doc(node, newnode):
    node.doc = None
    try:
        if isinstance(node.body[0], Discard) and isinstance(node.body[0].value, _Str):
            newnode.tolineno = node.body[0].lineno
            newnode.doc = node.body[0].value.s
            node.body = node.body[1:]
    except IndexError:
        pass # ast built from scratch


def native_repr_tree(node, indent='', _done=None):
    if _done is None:
        _done = set()
    if node in _done:
        print ('loop in tree: %r (%s)' % (node, getattr(node, 'lineno', None)))
        return
    _done.add(node)
    print indent + str(node)
    if type(node) is str: # XXX crash on Globals
        return
    indent += '    '
    d = node.__dict__
    if hasattr(node, '_attributes'):
        for a in node._attributes:
            attr = d[a]
            if attr is None:
                continue
            print indent + a, repr(attr)
    for f in node._fields or ():
        attr = d[f]
        if attr is None:
            continue
        if type(attr) is list:
            if not attr: continue
            print indent + f + ' ['
            for elt in attr:
                native_repr_tree(elt, indent, _done)
            print indent + ']'
            continue
        if isinstance(attr, (_Load, _Store, _Del)):
            continue
        if isinstance(attr, Node):
            print indent + f
            native_repr_tree(attr, indent, _done)
        else:
            print indent + f, repr(attr)


from logilab.astng.rebuilder import RebuildVisitor
# _ast rebuilder ##############################################################

class TreeRebuilder(RebuildVisitor):
    """Rebuilds the _ast tree to become an ASTNG tree"""

    def visit_arguments(self, node):
        """visit a Arguments node by returning a fresh instance of it"""
        newnode = new.Arguments()
        newnode.args = [self.visit(child, node) for child in node.args]
        newnode.defaults = [self.visit(child, node) for child in node.defaults]
        return newnode

    def visit_assattr(self, node):
        """visit a AssAttr node by returning a fresh instance of it"""
        newnode = new.AssAttr()
        newnode.expr = self.visit(node.expr, node)
        return newnode

    def visit_assname(self, node):
        """visit a AssName node by returning a fresh instance of it"""
        newnode = new.AssName()
        return newnode

    def visit_assert(self, node):
        """visit a Assert node by returning a fresh instance of it"""
        newnode = new.Assert()
        newnode.test = self.visit(node.test, node)
        newnode.fail = self.visit(node.msg, node)
        return newnode

    def visit_assign(self, node):
        """visit a Assign node by returning a fresh instance of it"""
        newnode = new.Assign()
        newnode.targets = [self.visit(child, node) for child in node.targets]
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_augassign(self, node):
        """visit a AugAssign node by returning a fresh instance of it"""
        newnode = new.AugAssign()
        newnode.target = self.visit(node.target, node)
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_backquote(self, node):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = new.Backquote()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_binop(self, node):
        """visit a BinOp node by returning a fresh instance of it"""
        newnode = new.BinOp()
        newnode.left = self.visit(node.left, node)
        newnode.right = self.visit(node.right, node)
        newnode.op = _BIN_OP_CLASSES[node.op.__class__]
        return newnode

    def visit_boolop(self, node):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = new.BoolOp()
        newnode.values = [self.visit(child, node) for child in node.values]
        newnode.op = _BOOL_OP_CLASSES[node.op.__class__]
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
        print "kwargs=", node.kwargs, node.starargs
        if node.starargs:
            newnode.starargs = self.visit(node.starargs, node)
        if node.kwargs:
            newnode.kwargs = self.visit(node.kwargs, node)
        # XXX old code
        node.args.extend(node.keywords)
        del node.keywords
        # end old
        return newnode

    def visit_class(self, node):
        """visit a Class node by returning a fresh instance of it"""
        newnode = new.Class()
        _init_set_doc(node, newnode)
        newnode.bases = [self.visit(child, node) for child in node.bases]
        newnode.body = [self.visit(child, node) for child in node.body]
        return newnode

    def visit_compare(self, node):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = new.Compare()
        newnode.left = self.visit(node.left, node)
        #newnode.ops = [self.visit(child, node) for child in node.ops]
        # XXX old code
        newnode.ops = [(_CMP_OP_CLASSES[op.__class__], self.visit(expr, node))
                    for (op, expr) in zip(node.ops, node.comparators)]
        # end old
        return newnode

    def visit_comprehension(self, node):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = new.Comprehension()
        newnode.target = self.visit(node.target, node)
        newnode.iter = self.visit(node.iter, node)
        newnode.ifs = [self.visit(child, node) for child in node.ifs]
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
        newnode.items = [(self.visit(key, node),self.visit(value, node)) 
                          for key, value in zip(node.keys, node.values)]
        return newnode

    def visit_discard(self, node):
        """visit a Discard node by returning a fresh instance of it"""
        if isinstance(node.value, Yield):
            return self.visit(node.value, node)
        newnode = new.Discard()
        newnode.value = self.visit(node.value, node)
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
        newnode = new.ExceptHandler(self.visit(node.type, node),
                                    self.visit(node.name, node),
                                    [self.visit(n, node) for n in node.body])
        return newnode

    def visit_exec(self, node):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = new.Exec()
        newnode.expr = self.visit(node.body, node)
        newnode.globals = self.visit(node.globals, node)
        newnode.locals = self.visit(node.locals, node)
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
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_from(self, node):
        """visit a From node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = new.From(node.module, names)
        return newnode

    def visit_function(self, node):
        """visit a Function node by returning a fresh instance of it"""
        newnode = new.Function()
        _init_set_doc(node, newnode)
        newnode.args = self.visit(node.args, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        if 'decorators' in node._fields: # py < 2.6
            attr = 'decorators'
        else:
            attr = 'decorator_list'
        decorators = getattr(node, attr)
        if decorators:
            newnode.decorators = new.Decorators(decorators)
        else:
            newnode.decorators = None
        return newnode

    def visit_genexpr(self, node):
        """visit a GenExpr node by returning a fresh instance of it"""
        newnode = new.GenExpr()
        newnode.elt = self.visit(node.elt, node)
        newnode.generators = [self.visit(child, node) for child in node.generators]
        return newnode

    def visit_getattr(self, node):
        """visit a Getattr node by returning a fresh instance of it"""
        newnode = new.Getattr()
        newnode.expr = self.visit(node.value, node)
        newnode.attrname = node.attr
        # XXX old code
        del node.attr, node.value
        if isinstance(self.asscontext, Delete):
            node.__class__ = DelAttr
        else:
            if self.asscontext is not None:
                node.__class__ = AssAttr
        # end old
        return newnode

    def visit_global(self, node):
        """visit a Global node by returning a fresh instance of it"""
        newnode = new.Global()
        # XXX newnode.globals/targets = ...
        return newnode

    def visit_if(self, node):
        """visit a If node by returning a fresh instance of it"""
        newnode = new.If()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_ifexp(self, node):
        """visit a IfExp node by returning a fresh instance of it"""
        newnode = new.IfExp()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_import(self, node):
        """visit a Import node by returning a fresh instance of it"""
        newnode = new.Import()
        newnode.names = [(alias.name, alias.asname) for alias in node.names]
        return newnode

    def visit_index(self, node):
        """visit a Index node by returning a fresh instance of it"""
        newnode = new.Index()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_keyword(self, node):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = new.Keyword()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_lambda(self, node):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = new.Lambda()
        newnode.args =  self.visit(node.args, node)
        newnode.body = self.visit(node.body, node)
        return newnode

    def visit_list(self, node):
        """visit a List node by returning a fresh instance of it"""
        newnode = new.List()
        newnode.elts = [self.visit(child, node) for child in node.elts]
        return newnode

    def visit_listcomp(self, node):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = new.ListComp()
        newnode.elt = self.visit(node.elt, node)
        newnode.generators = [self.visit(child, node)
                              for child in node.generators]
        return newnode

    def visit_module(self, node):
        """visit a Module node by returning a fresh instance of it"""
        print "build new Module"
        newnode = new.Module()
        _init_set_doc(node, newnode)
        newnode.body = [self.visit(child, node) for child in node.body]
        return newnode

    def visit_name(self, node):
        """visit a Name node by returning a fresh instance of it"""
        newnode = new.Name()
        newnode.name = node.id
        # XXX old code
        if isinstance(self.asscontext, Delete):
            node.__class__ = DelName
        else:
            if self.asscontext is not None:
                node.__class__ = AssName
        # end old
        return newnode

    def visit_num(self, node):
        """visit a a Num node by returning a fresh instance of Const"""
        newnode = new.Const()
        newnode.value = node.n
        return newnode

    def visit_str(self, node):
        """visit a a Str node by returning a fresh instance of Const"""
        newnode = new.Const()
        newnode.value = node.s
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
        return newnode

    def visit_raise(self, node):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise()
        newnode.type = self.visit(node.type, node)
        newnode.inst = self.visit(node.inst, node)
        newnode.tback = self.visit(node.tback, node)
        return newnode

    def visit_return(self, node):
        """visit a Return node by returning a fresh instance of it"""
        newnode = new.Return()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_slice(self, node):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = new.Slice()
        newnode.lower = self.visit(node.lower, node)
        newnode.upper = self.visit(node.upper, node)
        newnode.step = self.visit(node.step, node)
        return newnode

    def visit_subscript(self, node):
        """visit a Subscript node by returning a fresh instance of it"""
        newnode = new.Subscript()
        newnode.value = self.visit(node.value, node)
        newnode.slice = self.visit(node.slice, node)
        return newnode

    def visit_tryexcept(self, node):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = new.TryExcept()
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.handlers = [self.visit(child, node) for child in node.handlers]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_tryfinally(self, node):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = new.TryFinally()
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.finalbody = [self.visit(n, node) for n in node.finalbody]
        return newnode

    def visit_tuple(self, node):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Tuple()
        newnode.elts = [self.visit(child, node) for child in node.elts]
        return newnode

    def visit_unaryop(self, node):
        """visit a UnaryOp node by returning a fresh instance of it"""
        newnode = new.UnaryOp()
        newnode.operand = self.visit(node.operand, node)
        newnode.op = _UNARY_OP_CLASSES[node.op.__class__]
        return newnode

    def visit_while(self, node):
        """visit a While node by returning a fresh instance of it"""
        newnode = new.While()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_with(self, node):
        """visit a With node by returning a fresh instance of it"""
        newnode = new.With()
        newnode.expr = self.visit(node.context_expr, node)
        newnode.vars = self.visit(node.optional_vars, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        return newnode

    def visit_yield(self, node):
        """visit a Yield node by returning a fresh instance of it"""
        newnode = new.Yield()
        newnode.value = self.visit(node.value, node)
        # removing discard parent handled in visit_discard
        return newnode

