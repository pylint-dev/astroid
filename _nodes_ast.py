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


CONST_NAME_TRANSFORMS = {'None':  None,
                         'True':  True,
                         'False': False}


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

    def _set_infos(self, oldnode, newnode, parent):
        if hasattr(oldnode, 'lineno'):
            newnode.lineno = oldnode.lineno
        last = newnode.last_child()
        newnode.set_line_info(last) # set_line_info accepts None

    def visit_arguments(self, node, parent):
        """visit a Arguments node by returning a fresh instance of it"""
        newnode = new.Arguments()
        newnode.parent = parent
        self.asscontext = "Ass"
        newnode.args = [self.visit(child, newnode) for child in node.args]
        self.asscontext = None
        newnode.defaults = [self.visit(child, newnode) for child in node.defaults]
        newnode.vararg = node.vararg
        newnode.kwarg = node.kwarg
        self._save_argument_name(newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_assattr(self, node, parent):
        """visit a AssAttr node by returning a fresh instance of it"""
        assc, self.asscontext = self.asscontext, None
        newnode = new.AssAttr()
        newnode.parent = parent
        newnode.expr = self.visit(node.expr, newnode)
        self.asscontext = assc
        self._delayed_assattr.append(newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_assert(self, node, parent):
        """visit a Assert node by returning a fresh instance of it"""
        newnode = new.Assert()
        newnode.parent = parent
        newnode.test = self.visit(node.test, newnode)
        newnode.fail = self.visit(node.msg, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_assign(self, node, parent):
        """visit a Assign node by returning a fresh instance of it"""
        newnode = new.Assign()
        newnode.parent = parent
        self.asscontext = "Ass"
        newnode.targets = [self.visit(child, newnode) for child in node.targets]
        self.asscontext = None
        newnode.value = self.visit(node.value, newnode)
        self._set_assign_infos(newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_augassign(self, node, parent):
        """visit a AugAssign node by returning a fresh instance of it"""
        newnode = new.AugAssign()
        newnode.parent = parent
        newnode.op = _BIN_OP_CLASSES[node.op.__class__] + "="
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, newnode)
        self.asscontext = None
        newnode.value = self.visit(node.value, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_backquote(self, node, parent):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = new.Backquote()
        newnode.parent = parent
        newnode.value = self.visit(node.value, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_binop(self, node, parent):
        """visit a BinOp node by returning a fresh instance of it"""
        newnode = new.BinOp()
        newnode.parent = parent
        newnode.left = self.visit(node.left, newnode)
        newnode.right = self.visit(node.right, newnode)
        newnode.op = _BIN_OP_CLASSES[node.op.__class__]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_boolop(self, node, parent):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = new.BoolOp()
        newnode.parent = parent
        newnode.values = [self.visit(child, newnode) for child in node.values]
        newnode.op = _BOOL_OP_CLASSES[node.op.__class__]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_callfunc(self, node, parent):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = new.CallFunc()
        newnode.parent = parent
        newnode.func = self.visit(node.func, newnode)
        newnode.args = [self.visit(child, newnode) for child in node.args]
        newnode.starargs = self.visit(node.starargs, newnode)
        newnode.kwargs = self.visit(node.kwargs, newnode)
        newnode.args.extend(self.visit(child, newnode) for child in node.keywords)
        self._set_infos(node, newnode, parent)
        return newnode

    def _visit_class(self, node, parent):
        """visit a Class node by returning a fresh instance of it"""
        newnode = new.Class()
        newnode.parent = parent
        _init_set_doc(node, newnode)
        newnode.bases = [self.visit(child, newnode) for child in node.bases]
        newnode.body = [self.visit(child, newnode) for child in node.body]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_compare(self, node, parent):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = new.Compare()
        newnode.parent = parent
        newnode.left = self.visit(node.left, newnode)
        newnode.ops = [(_CMP_OP_CLASSES[op.__class__], self.visit(expr, newnode))
                    for (op, expr) in zip(node.ops, node.comparators)]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_comprehension(self, node, parent):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = new.Comprehension()
        newnode.parent = parent
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, newnode)
        self.asscontext = None
        newnode.iter = self.visit(node.iter, newnode)
        newnode.ifs = [self.visit(child, newnode) for child in node.ifs]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_decorators(self, node, parent):
        """visit a Decorators node by returning a fresh instance of it"""
        # /!\ node is actually a _ast.Function node while
        # parent is a astng.nodes.Function node
        newnode = new.Decorators()
        newnode.parent = parent
        newnode.nodes = [self.visit(child, newnode) for child in node.decorators]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_delete(self, node, parent):
        """visit a Delete node by returning a fresh instance of it"""
        newnode = new.Delete()
        newnode.parent = parent
        self.asscontext = "Del"
        newnode.targets = [self.visit(child, newnode) for child in node.targets]
        self.asscontext = None
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_dict(self, node, parent):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = new.Dict()
        newnode.parent = parent
        newnode.items = [(self.visit(key, newnode), self.visit(value, newnode))
                          for key, value in zip(node.keys, node.values)]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_discard(self, node, parent):
        """visit a Discard node by returning a fresh instance of it"""
        newnode = new.Discard()
        newnode.parent = parent
        newnode.value = self.visit(node.value, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_excepthandler(self, node, parent):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = new.ExceptHandler()
        newnode.parent = parent
        newnode.type = self.visit(node.type, newnode)
        self.asscontext = "Ass"
        newnode.name = self.visit(node.name, newnode)
        self.asscontext = None
        newnode.body = [self.visit(child, newnode) for child in node.body]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_exec(self, node, parent):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = new.Exec()
        newnode.parent = parent
        newnode.expr = self.visit(node.body, newnode)
        newnode.globals = self.visit(node.globals, newnode)
        newnode.locals = self.visit(node.locals, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_extslice(self, node, parent):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = new.ExtSlice()
        newnode.parent = parent
        newnode.dims = [self.visit(dim, newnode) for dim in node.dims]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_for(self, node, parent):
        """visit a For node by returning a fresh instance of it"""
        newnode = new.For()
        newnode.parent = parent
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, newnode)
        self.asscontext = None
        newnode.iter = self.visit(node.iter, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_from(self, node, parent):
        """visit a From node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = new.From(node.module, names)
        newnode.parent = parent
        self._add_from_names_to_locals(newnode)
        self._set_infos(node, newnode, parent)
        newnode.level = node.level
        return newnode

    def _visit_function(self, node, parent):
        """visit a Function node by returning a fresh instance of it"""
        newnode = new.Function()
        newnode.parent = parent
        _init_set_doc(node, newnode)
        newnode.args = self.visit(node.args, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        self._set_infos(node, newnode.args, parent)
        if 'decorators' in node._fields: # py < 2.6
            attr = 'decorators'
        else:
            attr = 'decorator_list'
        decorators = getattr(node, attr)
        if decorators:
            newnode.decorators = self.visit_decorators(node, newnode)
        else:
            newnode.decorators = None
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_genexpr(self, node, parent):
        """visit a GenExpr node by returning a fresh instance of it"""
        newnode = new.GenExpr()
        newnode.parent = parent
        newnode.elt = self.visit(node.elt, newnode)
        newnode.generators = [self.visit(child, newnode) for child in node.generators]
        self._set_infos(node, newnode, parent)
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
            self._delayed_assattr.append(newnode)
        else:
            newnode = new.Getattr()
        newnode.parent = parent
        asscontext, self.asscontext = self.asscontext, None
        newnode.expr = self.visit(node.value, newnode)
        self.asscontext = asscontext
        newnode.attrname = node.attr
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_if(self, node, parent):
        """visit a If node by returning a fresh instance of it"""
        newnode = new.If()
        newnode.parent = parent
        newnode.test = self.visit(node.test, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_ifexp(self, node, parent):
        """visit a IfExp node by returning a fresh instance of it"""
        newnode = new.IfExp()
        newnode.parent = parent
        newnode.test = self.visit(node.test, newnode)
        newnode.body = self.visit(node.body, newnode)
        newnode.orelse = self.visit(node.orelse, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_import(self, node, parent):
        """visit a Import node by returning a fresh instance of it"""
        newnode = new.Import()
        newnode.parent = parent
        newnode.names = [(alias.name, alias.asname) for alias in node.names]
        self._save_import_locals(newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_index(self, node, parent):
        """visit a Index node by returning a fresh instance of it"""
        newnode = new.Index()
        newnode.parent = parent
        newnode.value = self.visit(node.value, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_keyword(self, node, parent):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = new.Keyword()
        newnode.parent = parent
        newnode.arg = node.arg
        newnode.value = self.visit(node.value, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_lambda(self, node, parent):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = new.Lambda()
        newnode.parent = parent
        newnode.args = self.visit(node.args, newnode)
        newnode.body = self.visit(node.body, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_list(self, node, parent):
        """visit a List node by returning a fresh instance of it"""
        newnode = new.List()
        newnode.parent = parent
        newnode.elts = [self.visit(child, newnode) for child in node.elts]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_listcomp(self, node, parent):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = new.ListComp()
        newnode.parent = parent
        newnode.elt = self.visit(node.elt, newnode)
        newnode.generators = [self.visit(child, newnode)
                              for child in node.generators]
        self._set_infos(node, newnode, parent)
        return newnode

    def _visit_module(self, node, parent):
        """visit a Module node by returning a fresh instance of it"""
        newnode = new.Module()
        newnode.parent = parent
        _init_set_doc(node, newnode)
        newnode.name = node.name
        newnode.body = [self.visit(child, newnode) for child in node.body]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_name(self, node, parent):
        """visit a Name node by returning a fresh instance of it"""
        if node.id in CONST_NAME_TRANSFORMS:
            newnode = new.Const(CONST_NAME_TRANSFORMS[node.id])
            self._set_infos(node, newnode, parent)
            return newnode
        if self.asscontext == "Del":
            newnode = new.DelName()
        elif self.asscontext is not None: # Ass
            assert self.asscontext == "Ass"
            newnode = new.AssName()
        else:
            newnode = new.Name()
        newnode.parent = parent
        newnode.name = node.id
        # XXX REMOVE me :
        if self.asscontext in ('Del', 'Ass'): # 'Aug' ??
            self._save_assignment(newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_num(self, node, parent):
        """visit a a Num node by returning a fresh instance of Const"""
        newnode = new.Const(node.n)
        newnode.parent = parent
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_str(self, node, parent):
        """visit a a Str node by returning a fresh instance of Const"""
        newnode = new.Const(node.s)
        newnode.parent = parent
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_print(self, node, parent):
        """visit a Print node by returning a fresh instance of it"""
        newnode = new.Print()
        newnode.parent = parent
        newnode.nl = node.nl
        newnode.dest = self.visit(node.dest, newnode)
        newnode.values = [self.visit(child, newnode) for child in node.values]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_raise(self, node, parent):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise()
        newnode.parent = parent
        newnode.type = self.visit(node.type, newnode)
        newnode.inst = self.visit(node.inst, newnode)
        newnode.tback = self.visit(node.tback, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_return(self, node, parent):
        """visit a Return node by returning a fresh instance of it"""
        newnode = new.Return()
        newnode.parent = parent
        newnode.value = self.visit(node.value, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_slice(self, node, parent):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = new.Slice()
        newnode.parent = parent
        newnode.lower = self.visit(node.lower, newnode)
        newnode.upper = self.visit(node.upper, newnode)
        newnode.step = self.visit(node.step, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_subscript(self, node, parent):
        """visit a Subscript node by returning a fresh instance of it"""
        newnode = new.Subscript()
        newnode.parent = parent
        subcontext, self.asscontext = self.asscontext, None
        newnode.value = self.visit(node.value, newnode)
        newnode.slice = self.visit(node.slice, newnode)
        self.asscontext = subcontext
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_tryexcept(self, node, parent):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = new.TryExcept()
        newnode.parent = parent
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.handlers = [self.visit(child, newnode) for child in node.handlers]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_tryfinally(self, node, parent):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = new.TryFinally()
        newnode.parent = parent
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.finalbody = [self.visit(n, newnode) for n in node.finalbody]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_tuple(self, node, parent):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Tuple()
        newnode.parent = parent
        newnode.elts = [self.visit(child, newnode) for child in node.elts]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_unaryop(self, node, parent):
        """visit a UnaryOp node by returning a fresh instance of it"""
        newnode = new.UnaryOp()
        newnode.parent = parent
        newnode.operand = self.visit(node.operand, newnode)
        newnode.op = _UNARY_OP_CLASSES[node.op.__class__]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_while(self, node, parent):
        """visit a While node by returning a fresh instance of it"""
        newnode = new.While()
        newnode.parent = parent
        newnode.test = self.visit(node.test, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_with(self, node, parent):
        """visit a With node by returning a fresh instance of it"""
        newnode = new.With()
        newnode.parent = parent
        newnode.expr = self.visit(node.context_expr, newnode)
        self.asscontext = "Ass"
        newnode.vars = self.visit(node.optional_vars, newnode)
        self.asscontext = None
        newnode.body = [self.visit(child, newnode) for child in node.body]
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_yield(self, node, parent):
        """visit a Yield node by returning a fresh instance of it"""
        newnode = new.Yield()
        newnode.parent = parent
        newnode.value = self.visit(node.value, newnode)
        self._set_infos(node, newnode, parent)
        return newnode

