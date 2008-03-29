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
:copyright: 2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2008 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

__docformat__ = "restructuredtext en"

from logilab.astng.utils import infer_end

from _ast import (Add, And, Assert, Assign, AugAssign,
                  Break,
                  Compare, Continue,
                  Dict, Div, 
                  Ellipsis, Exec, 
                  FloorDiv, For,
                  Global, 
                  If, Import, Invert,
                  Lambda, List, ListComp, 
                  Mod, Module, 
                  Name, Not,
                  Or,
                  Pass, Print,
                  Raise, Return,
                  Slice, Sub, Subscript, 
                  TryExcept, TryFinally, Tuple,
                  While, With,
                  Yield,
                  )

from _ast import (AST as Node,
                  BitAnd as Bitand, BitOr as Bitor, BitXor as Bitxor,
                  Call as CallFunc,
                  ClassDef as Class,
                  FunctionDef as Function,
                  GeneratorExp as GenExpr,
                  ImportFrom as From,
                  LShift as LeftShift,
                  Mult as Mul,
                  Repr as Backquote,
                  Pow as Power,
                  RShift as RightShift,
                  UAdd as UnaryAdd,
                  USub as UnarySub,
                  )
# XXX : AugLoad, AugStore, Attribute
#       BinOp, BoolOp
#       Del, Delete
#       Eq, Expr, Expression, ExtSlice
#       Gt, GtE
#       IfExp, In, Index, Interactive, Is, IsNot
#       Load, Lt, LtE
#       NotEq, NotIn, Num
#       Param
#       Store, Str, Suite
#       UnaryOp
from _ast import Num, Str, Expr, alias
Const = (Num, Str)

class EmptyNode(Node): pass

# scoped nodes ################################################################

def module_append_node(self, child_node):
    """append a child version specific to Module node"""
    self.body.append(child_node)
    child_node.parent = self
Module._append_node = module_append_node

def _append_node(self, child_node):
    """append a child, linking it in the tree"""
    # XXX
    self.code.nodes.append(child_node)
    child_node.parent = self
Class._append_node = _append_node
Function._append_node = _append_node

# inferences ##################################################################

from logilab.astng.utils import infer_end

Num.infer = infer_end
Str.infer = infer_end

# raw building ################################################################

def module_factory(doc):
    node = Module()
    node.body = []
    if doc:
        expr = Expr()
        node.body.append(expr)
        expr.parent = None
        docstr = Str()
        docstr.s = doc
        expr.value = docstr
        docstr.parent = expr
    return node

def dict_factory():
    return Dict()

def import_from_factory(modname, membername):
    node = From()
    node.level = 0
    node.module = modname
    aliasnode = alias()
    aliasnode.parent = node
    aliasnode.name = membername
    aliasnode.asname = None
    node.names = [aliasnode]
    return node

def const_factory(value):
    if value is None:
        node = Name()
        node.id = 'None'
    elif value is True:
        node = Name()
        node.id = 'True'
    elif value is False:
        node = Name()
        node.id = 'False'
    elif isinstance(value, (int, long, complex)):
        node = Num()
        node.n = value
    elif isinstance(value, basestring):
        node = Str()
        node.s = value
    else:
        raise Exception(repr(value))
    return node
        
