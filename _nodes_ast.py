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

Proxy_ = object

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


def _init_set_doc(node):
    node.doc = None
    try:
        if isinstance(node.body[0], Discard) and isinstance(node.body[0].value, _Str):
            node.tolineno = node.body[0].lineno
            node.doc = node.body[0].value.s
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


from _ast import Str as _Str, Num as _Num
_Num.accept = lambda self, visitor: visitor.visit_num(self)
_Str.accept = lambda self, visitor: visitor.visit_str(self)

# some astng nodes unexistant in _ast #########################################

class AssAttr(Node):
    """represent Attribute Assignment statements"""

class AssName(Node):
    """represent AssName statements"""

class Const(Node):
    """represent a Str or Num node"""
    def __init__(self, value=None):
        super(Const, self).__init__()
        self.value = value

class DelAttr(Node):
    """represent del attribute statements"""

class DelName(Node):
    """represent del statements"""

class EmptyNode(Node):
    """represent a Empty node for compatibility"""

class Decorators(Node):
    """represent a Decorator node"""
    def __init__(self, nodes):
        self.nodes = nodes

# _ast rebuilder ##############################################################

class TreeRebuilder(ASTVisitor):
    """REbuilds the _ast tree to become an ASTNG tree"""

    def __init__(self, rebuild_visitor):
        self.visitor = rebuild_visitor

    def visit_assert(self, node):
        node.fail = node.msg
        del node.msg

    def visit_augassign(self, node):
        node.op = _BIN_OP_CLASSES[node.op.__class__]

    def visit_binop(self, node):
        node.op = _BIN_OP_CLASSES[node.op.__class__]

    def visit_boolop(self, node):
        node.op = _BOOL_OP_CLASSES[node.op.__class__]

    def visit_callfunc(self, node):
        node.args.extend(node.keywords)
        del node.keywords

    def visit_class(self, node):
        _init_set_doc(node)

    def visit_compare(self, node):
        node.ops = [(_CMP_OP_CLASSES[op.__class__], expr)
                    for op, expr in zip(node.ops, node.comparators)]
        del node.comparators

    def visit_dict(self, node):
        node.items = zip(node.keys, node.values)
        del node.keys, node.values

    def visit_exec(self, node):
        node.expr = node.body
        del node.body

    def visit_function(self, node):
        _init_set_doc(node)
        if 'decorators' in node._fields: # py < 2.6
            attr = 'decorators'
        else:
            attr = 'decorator_list'
        decorators = getattr(node, attr)
        delattr(node, attr)
        if decorators:
            node.decorators = Decorators(decorators)
        else:
            node.decorators = None

    def visit_getattr(self, node):
        node.attrname = node.attr
        node.expr = node.value
        del node.attr, node.value
        if isinstance(self.visitor.asscontext, Delete):
            node.__class__ = DelAttr
        elif self.visitor.asscontext is not None:
            node.__class__ = AssAttr

    def visit_import(self, node):
        node.names = [(alias.name, alias.asname) for alias in node.names]

    def visit_from(self, node):
        node.names = [(alias.name, alias.asname) for alias in node.names]
        node.modname = node.module
        del node.module

    def visit_module(self, node):
        _init_set_doc(node)

    def visit_name(self, node):
        node.name = node.id
        del node.id
        if isinstance(self.visitor.asscontext, Delete):
            node.__class__ = DelName
        elif self.visitor.asscontext is not None:
            node.__class__ = AssName

    def visit_num(self, node):
        node.__class__ = Const
        node.value = node.n
        del node.n

    def visit_str(self, node):
        node.__class__ = Const
        node.value = node.s
        del node.s

    def visit_unaryop(self, node):
        node.op = _UNARY_OP_CLASSES[node.op.__class__]

    def visit_with(self, node):
        """build compiler like node """
        node.vars = node.optional_vars
        node.expr = node.context_expr
        del node.optional_vars, node.context_expr


# raw building ################################################################

def module_factory(doc):
    node = Module()
    node.body = []
    node.doc = doc
    return node


def import_from_factory(modname, membername):
    node = From()
    node.level = 0
    node.modname = modname
    node.names = [(membername, None)]
    return node


def _const_factory(value):
    if isinstance(value, (int, long, complex, float, basestring)):
        node = Const()
    else:
        raise Exception(type(value))
    node.value = value
    return node


def function_factory(name, args, defaults, flag=0, doc=None):
    """create and initialize a astng Function node"""
    # XXX local import necessary due to cyclic deps
    from logilab.astng.nodes import const_factory
    node = Function()
    node.decorators = None
    node.body = []
    node.name = name
    # XXX ensure we get a compatible representation
    node.args = argsnode = Arguments()
    argsnode.args = []
    for arg in args:
        argsnode.args.append(Name())
        argsnode.args[-1].name = arg
        argsnode.args[-1].parent = argsnode
    argsnode.defaults = []
    for default in defaults:
        argsnode.defaults.append(const_factory(default))
        argsnode.defaults[-1].parent = argsnode
    argsnode.kwarg = None
    argsnode.vararg = None
    argsnode.parent = node
    node.doc = doc
    return node


def class_factory(name, basenames=(), doc=None):
    """create and initialize a astng Class node"""
    node = Class()
    node.body = []
    node.name = name
    # XXX to check
    node.bases = []
    for base in basenames:
        basenode = Name()
        basenode.name = base
        node.bases.append(basenode)
        basenode.parent = node
    node.doc = doc
    return node
