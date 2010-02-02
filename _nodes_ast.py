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
    newnode.doc = None
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

    def visit_arguments(self, node, parent):
        """visit a Arguments node by returning a fresh instance of it"""
        newnode = new.Arguments()
        self.asscontext = "Ass"
        newnode.args = [self.visit(child, node) for child in node.args]
        self.asscontext = None
        newnode.defaults = [self.visit(child, node) for child in node.defaults]
        newnode.vararg = node.vararg
        newnode.kwarg = node.kwarg
        self._save_argument_name(newnode)
        return newnode

    def visit_assattr(self, node, parent):
        """visit a AssAttr node by returning a fresh instance of it"""
        assc, self.asscontext = self.asscontext, None
        newnode = new.AssAttr()
        newnode.expr = self.visit(node.expr, node)
        self.asscontext = assc
        self._delayed['assattr'].append(newnode)
        return newnode

    def visit_assert(self, node, parent):
        """visit a Assert node by returning a fresh instance of it"""
        newnode = new.Assert()
        newnode.test = self.visit(node.test, node)
        newnode.fail = self.visit(node.msg, node)
        return newnode

    def visit_assign(self, node, parent):
        """visit a Assign node by returning a fresh instance of it"""
        newnode = new.Assign()
        self.asscontext = "Ass"
        newnode.targets = [self.visit(child, node) for child in node.targets]
        self.asscontext = None
        newnode.value = self.visit(node.value, node)
        self._delayed['assign'].append(newnode)
        return newnode

    def visit_augassign(self, node, parent):
        """visit a AugAssign node by returning a fresh instance of it"""
        newnode = new.AugAssign()
        newnode.op = _BIN_OP_CLASSES[node.op.__class__] + "="
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, node)
        self.asscontext = None
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_backquote(self, node, parent):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = new.Backquote()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_binop(self, node, parent):
        """visit a BinOp node by returning a fresh instance of it"""
        newnode = new.BinOp()
        newnode.left = self.visit(node.left, node)
        newnode.right = self.visit(node.right, node)
        newnode.op = _BIN_OP_CLASSES[node.op.__class__]
        return newnode

    def visit_boolop(self, node, parent):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = new.BoolOp()
        newnode.values = [self.visit(child, node) for child in node.values]
        newnode.op = _BOOL_OP_CLASSES[node.op.__class__]
        return newnode

    def visit_break(self, node, parent):
        """visit a Break node by returning a fresh instance of it"""
        newnode = new.Break()
        return newnode

    def visit_callfunc(self, node, parent):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = new.CallFunc()
        newnode.func = self.visit(node.func, node)
        newnode.args = [self.visit(child, node) for child in node.args]
        newnode.starargs = self.visit(node.starargs, node)
        newnode.kwargs = self.visit(node.kwargs, node)
        newnode.args.extend(self.visit(child, node) for child in node.keywords)
        return newnode

    def _visit_class(self, node, parent):
        """visit a Class node by returning a fresh instance of it"""
        newnode = new.Class()
        _init_set_doc(node, newnode)
        newnode.bases = [self.visit(child, node) for child in node.bases]
        newnode.body = [self.visit(child, node) for child in node.body]
        return newnode

    def visit_compare(self, node, parent):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = new.Compare()
        newnode.left = self.visit(node.left, node)
        newnode.ops = [(_CMP_OP_CLASSES[op.__class__], self.visit(expr, node))
                    for (op, expr) in zip(node.ops, node.comparators)]
        return newnode

    def visit_comprehension(self, node, parent):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = new.Comprehension()
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, node)
        self.asscontext = None
        newnode.iter = self.visit(node.iter, node)
        newnode.ifs = [self.visit(child, node) for child in node.ifs]
        return newnode

    def visit_decorators(self, node, parent):
        """visit a Decorators node by returning a fresh instance of it"""
        newnode = new.Decorators()
        newnode.nodes = [self.visit(child, node) for child in node.decorators]
        self.set_infos(newnode, node)
        self._delayed['decorators'].append(newnode)
        return newnode


    def visit_delete(self, node, parent):
        """visit a Delete node by returning a fresh instance of it"""
        newnode = new.Delete()
        self.asscontext = "Del"
        newnode.targets = [self.visit(child, node) for child in node.targets]
        self.asscontext = None
        return newnode

    def visit_dict(self, node, parent):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = new.Dict()
        newnode.items = [(self.visit(key, node), self.visit(value, node))
                          for key, value in zip(node.keys, node.values)]
        return newnode

    def visit_discard(self, node, parent):
        """visit a Discard node by returning a fresh instance of it"""
        newnode = new.Discard()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_excepthandler(self, node, parent):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        return self._build_excepthandler(node, node.type, node.name, node.body)

    def visit_exec(self, node, parent):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = new.Exec()
        newnode.expr = self.visit(node.body, node)
        newnode.globals = self.visit(node.globals, node)
        newnode.locals = self.visit(node.locals, node)
        return newnode

    def visit_extslice(self, node, parent):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = new.ExtSlice()
        newnode.dims = [self.visit(dim, node) for dim in node.dims]
        return newnode

    def visit_for(self, node, parent):
        """visit a For node by returning a fresh instance of it"""
        newnode = new.For()
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, node)
        self.asscontext = None
        newnode.iter = self.visit(node.iter, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_from(self, node, parent):
        """visit a From node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = new.From(node.module, names)
        self._delayed['from'].append(newnode)
        return newnode

    def _visit_function(self, node, parent):
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
            newnode.decorators = self.visit_decorators(node, parent)
        else:
            newnode.decorators = None
        return newnode

    def visit_genexpr(self, node, parent):
        """visit a GenExpr node by returning a fresh instance of it"""
        newnode = new.GenExpr()
        newnode.elt = self.visit(node.elt, node)
        newnode.generators = [self.visit(child, node) for child in node.generators]
        return newnode

    def visit_getattr(self, node, parent):
        """visit a Getattr node by returning a fresh instance of it"""
        if self.asscontext == "Del":
            # FIXME : maybe we should reintroduce and visit_delattr ?
            # for instance, deactivating asscontext
            newnode = new.DelAttr()
        elif self.asscontext == "Ass":
            # FIXME : maybe we should call visit_assattr ?
            newnode = new.AssAttr()
            self._delayed['assattr'].append(newnode)
        else:
            newnode = new.Getattr()
        asscontext, self.asscontext = self.asscontext, None
        newnode.expr = self.visit(node.value, node)
        self.asscontext = asscontext
        newnode.attrname = node.attr
        return newnode

    def visit_if(self, node, parent):
        """visit a If node by returning a fresh instance of it"""
        newnode = new.If()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_ifexp(self, node, parent):
        """visit a IfExp node by returning a fresh instance of it"""
        newnode = new.IfExp()
        newnode.test = self.visit(node.test, node)
        newnode.body = self.visit(node.body, node)
        newnode.orelse = self.visit(node.orelse, node)
        return newnode

    def visit_import(self, node, parent):
        """visit a Import node by returning a fresh instance of it"""
        newnode = new.Import()
        newnode.names = [(alias.name, alias.asname) for alias in node.names]
        self._save_import_locals(newnode)
        return newnode

    def visit_index(self, node, parent):
        """visit a Index node by returning a fresh instance of it"""
        newnode = new.Index()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_keyword(self, node, parent):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = new.Keyword()
        newnode.arg = node.arg
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_lambda(self, node, parent):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = new.Lambda()
        newnode.args =  self.visit(node.args, node)
        newnode.body = self.visit(node.body, node)
        return newnode

    def visit_list(self, node, parent):
        """visit a List node by returning a fresh instance of it"""
        newnode = new.List()
        newnode.elts = [self.visit(child, node) for child in node.elts]
        return newnode

    def visit_listcomp(self, node, parent):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = new.ListComp()
        newnode.elt = self.visit(node.elt, node)
        newnode.generators = [self.visit(child, node)
                              for child in node.generators]
        return newnode

    def _visit_module(self, node, parent):
        """visit a Module node by returning a fresh instance of it"""
        newnode = new.Module()
        _init_set_doc(node, newnode)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.name = node.name
        return newnode

    def _visit_name(self, node, parent):
        """visit a Name node by returning a fresh instance of it"""
        if self.asscontext == "Del":
            newnode = new.DelName()
            newnode.name = node.id
            self._save_assignment(newnode)
        elif self.asscontext is not None: # Ass
            assert self.asscontext == "Ass"
            newnode = new.AssName()
            newnode.name = node.id
            self._save_assignment(newnode)
        else:
            newnode = new.Name()
        newnode.name = node.id
        return newnode

    def visit_num(self, node, parent):
        """visit a a Num node by returning a fresh instance of Const"""
        newnode = new.Const(node.n)
        return newnode

    def visit_str(self, node, parent):
        """visit a a Str node by returning a fresh instance of Const"""
        newnode = new.Const(node.s)
        return newnode

    def visit_print(self, node, parent):
        """visit a Print node by returning a fresh instance of it"""
        newnode = new.Print()
        newnode.nl = node.nl
        newnode.dest = self.visit(node.dest, node)
        newnode.values = [self.visit(child, node) for child in node.values]
        return newnode

    def visit_raise(self, node, parent):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise()
        newnode.type = self.visit(node.type, node)
        newnode.inst = self.visit(node.inst, node)
        newnode.tback = self.visit(node.tback, node)
        return newnode

    def visit_return(self, node, parent):
        """visit a Return node by returning a fresh instance of it"""
        newnode = new.Return()
        newnode.value = self.visit(node.value, node)
        return newnode

    def visit_slice(self, node, parent):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = new.Slice()
        newnode.lower = self.visit(node.lower, node)
        newnode.upper = self.visit(node.upper, node)
        newnode.step = self.visit(node.step, node)
        return newnode

    def visit_subscript(self, node, parent):
        """visit a Subscript node by returning a fresh instance of it"""
        newnode = new.Subscript()
        subcontext, self.asscontext = self.asscontext, None
        newnode.value = self.visit(node.value, node)
        newnode.slice = self.visit(node.slice, node)
        self.asscontext = subcontext
        return newnode

    def visit_tryexcept(self, node, parent):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = new.TryExcept()
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.handlers = [self.visit(child, node) for child in node.handlers]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_tryfinally(self, node, parent):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = new.TryFinally()
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.finalbody = [self.visit(n, node) for n in node.finalbody]
        return newnode

    def visit_tuple(self, node, parent):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Tuple()
        newnode.elts = [self.visit(child, node) for child in node.elts]
        return newnode

    def visit_unaryop(self, node, parent):
        """visit a UnaryOp node by returning a fresh instance of it"""
        newnode = new.UnaryOp()
        newnode.operand = self.visit(node.operand, node)
        newnode.op = _UNARY_OP_CLASSES[node.op.__class__]
        return newnode

    def visit_while(self, node, parent):
        """visit a While node by returning a fresh instance of it"""
        newnode = new.While()
        newnode.test = self.visit(node.test, node)
        newnode.body = [self.visit(child, node) for child in node.body]
        newnode.orelse = [self.visit(child, node) for child in node.orelse]
        return newnode

    def visit_with(self, node, parent):
        """visit a With node by returning a fresh instance of it"""
        newnode = new.With()
        newnode.expr = self.visit(node.context_expr, node)
        self.asscontext = "Ass"
        newnode.vars = self.visit(node.optional_vars, node)
        self.asscontext = None
        newnode.body = [self.visit(child, node) for child in node.body]
        return newnode

    def visit_yield(self, node, parent):
        """visit a Yield node by returning a fresh instance of it"""
        newnode = new.Yield()
        newnode.value = self.visit(node.value, node)
        return newnode

