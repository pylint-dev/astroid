
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

from logilab.astng.utils import infer_end, NoneType, Bool

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
                  Not,
                  Or,
                  Pass, Print,
                  Raise, Return,
                  Slice, Sub, Subscript, 
                  TryExcept, TryFinally, Tuple,
                  While, With,
                  Yield,
                  )

from _ast import (AST as Node,
                  Attribute as Getattr,
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

                  Name,
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
from _ast import Num, Str, Eq, Expr, alias, arguments, comprehension
Const = (Num, Str)

class EmptyNode(Node): pass

def Name__init__(self, name):
    self.id = name
Name.__init__ = Name__init__

def Name_get_name(self):
    return self.id
Name.name = property(Name_get_name)

def _get_children_value(self):
    return (self.value,)
Expr.getChildNodes = _get_children_value
Getattr.getChildNodes = _get_children_value

def _get_children_nochildren(self):
    return ()
Import.getChildNodes = _get_children_nochildren
print 'patching', Name, id(Name)
Name.getChildNodes = _get_children_nochildren
Str.getChildNodes = _get_children_nochildren
Num.getChildNodes = _get_children_nochildren
NoneType.getChildNodes = _get_children_nochildren
Bool.getChildNodes = _get_children_nochildren
Pass.getChildNodes = _get_children_nochildren
Eq.getChildNodes = _get_children_nochildren

def _get_children_call(self):
    children = [self.func]
    children.extend(self.args)
    children.extend(self.keywords)
    if self.starargs:
        children.extend(self.starargs)
    if self.kwargs:
        children.extend(self.kwargs)
    return children
CallFunc.getChildNodes = _get_children_call

        
def _get_children_assign(self):
    return self.targets + [self.value]
Assign.getChildNodes = _get_children_assign

def _get_children_if(self):
    return [self.test] + self.body + self.orelse
If.getChildNodes = _get_children_if

def _get_children_print(self):
    if self.dest:
        return [self.dest] + self.values
    return self.values
Print.getChildNodes = _get_children_print

def _get_children_compare(self):
    return [self.left] + self.ops + self.comparators
Compare.getChildNodes = _get_children_compare

def _get_children_generatorexp(self):
    return [self.elt] + self.generators
GenExpr.getChildNodes = _get_children_generatorexp

def _get_children_comprehension(self):
    return [self.target] + [self.iter] + self.ifs
comprehension.getChildNodes = _get_children_comprehension


def getattr_as_string(node):
    """return an ast.Getattr node as string"""
    return '%s.%s' % (node.value.as_string(), node.attr)
Getattr.as_string = getattr_as_string

# scoped nodes ################################################################

def _get_children_body(self):
    return self.body
Module.getChildNodes = _get_children_body
Class.getChildNodes = _get_children_body
Function.getChildNodes = _get_children_body

def _append_node(self, child_node):
    """append a child, linking it in the tree"""
    self.body.append(child_node)
    child_node.parent = self
Module._append_node = _append_node
Class._append_node = _append_node
Function._append_node = _append_node

#
def _init_set_doc(node):
    node.doc = None
    if isinstance(node.body[0], Expr) and isinstance(node.body[0].value, Str):
        node.doc = node.body[0].value.s
    print 'set doc', node
    return node
init_module = init_function = init_class = _init_set_doc

def init_import(node):
    node.names = [(alias.name, alias.asname) for alias in node.names]
    return node

def init_assign(node):
    return node
    
# raw building ################################################################
from logilab.astng.utils import NoneType, Bool

def _add_docstring(node, doc):
    node.doc = doc
    if doc:
        expr = Expr()
        node.body.append(expr)
        expr.parent = None
        docstr = Str()
        docstr.s = doc
        expr.value = docstr
        docstr.parent = expr
    
def module_factory(doc):
    node = Module()
    node.body = []
    _add_docstring(node, doc)
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
        node = NoneType(None)
    elif value is True:
        node = Bool(False)
    elif value is False:
        node = Bool(True)
    elif isinstance(value, (int, long, complex)):
        node = Num()
    elif isinstance(value, basestring):
        node = Str()
    else:
        raise Exception(repr(value))
    node.value = value
    return node
        
def function_factory(name, args, defaults, flag=0, doc=None):
    """create and initialize a astng Function node"""
    node = Function()
    node.body = []
    node.name = name
    argsnode = arguments()
    argsnode.args = []
    for arg in args:
        argsnode.args.append(Name(arg))
        argsnode.args[-1].parent = argsnode
    argsnode.defaults = []
    for default in defaults:
        argsnode.defaults.append(const_factory(default))
        argsnode.defaults[-1].parent = argsnode
    argsnode.kwarg = None # XXX
    argsnode.vararg = None # XXX
    argsnode.parent = node
    node.args = argsnode
    _add_docstring(node, doc)
    return node


def class_factory(name, basenames=None, doc=None):
    """create and initialize a astng Class node"""
    node = Class()
    node.body = []
    node.name = name
    # XXX to check
    node.bases = []
    for base in basenames:
        basenode = Name(base)
        node.bases.append(basenode)
        basenode.parent = node
    _add_docstring(node, doc)
    return node
