
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

from _ast import (Assert, Assign, AugAssign,
                  Break,
                  Compare, Continue,
                  Delete, Dict, 
                  Ellipsis, Exec, 
                  For,
                  Global, 
                  If, Import, Invert,
                  Lambda, List, ListComp, 
                  Module, 
                  Name,
                  Pass, Print,
                  Raise, Return,
                  Slice, Sub, Subscript, 
                  TryExcept, TryFinally, Tuple,
                  While, With,
                  Yield,
                  )
                  
from _ast import (AST as Node,
                  Attribute as Getattr,
                  Call as CallFunc,
                  ClassDef as Class,
                  FunctionDef as Function,
                  GeneratorExp as GenExpr,
                  Repr as Backquote,
                  
                  Expr as Discard, 
                  ImportFrom as From,
                  excepthandler as ExceptHandler,
                  )

# XXX : AugLoad, AugStore, Attribute
#       BoolOp
#       Del, Delete
#       Expr, Expression, ExtSlice
#       IfExp, Index, Interactive, 
#       Load, 
#       Param
#       Store, Suite
#       UnaryOp
from _ast import Num, Str, Eq, alias, arguments, comprehension

COMPREHENSIONS_SCOPES = (comprehension,)
Const = (Num, Str)

from _ast import (Add as _Add, Div as _Div, FloorDiv as _FloorDiv,
                  Mod as _Mod, Mult as _Mult, Pow as _Pow, Sub as _Sub,
                  BitAnd as _BitAnd, BitOr as _BitOr, BitXor as _BitXor,
                  LShift as _LShift, RShift as _RShift)
BIN_OP_CLASSES = {_Add: '+',
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


from _ast import And as _And, Or as _Or
BOOL_OP_CLASSES = {_And: 'and',
                   _Or: 'or'}

from _ast import UAdd as _UAdd, USub as _USub, Not as _Not
UNARY_OP_CLASSES = {_UAdd: '+',
                    _USub: '-',
                    _Not: 'not'}

from _ast import BinOp, BoolOp, UnaryOp

from _ast import (Eq as _Eq, Gt as _Gt, GtE as _GtE, In as _In, Is as _Is,
                  IsNot as _IsNot, Lt as _Lt, LtE as _LtE, NotEq as _NotEq,
                  NotIn as _NotIn)
CMP_OP_CLASSES = {_Eq: '==',
                  _Gt: '>',
                  _GtE: '>=',
                  _In: 'in',
                  _Is: 'is',
                  _IsNot: 'is not',
                  _Lt: '<',
                  _LtE: '<=',
                  _NotEq: '!=',
                  _NotIn: 'not in',
                  }

#Eq._astng_fields = () # Eq nodes should disappear after astng builder
Num._astng_fields = ()
Str._astng_fields = ()

#from _ast import Load, Store, Del
#Load.lineno = Store.lineno = 0 # XXX

# def Name__init__(self, name):
#     self.name = name
# Name.__init__ = Name__init__

# def _get_children_value(self):
#     return (self.value,)
# Expr.getChildNodes = _get_children_value
# Getattr.getChildNodes = _get_children_value

# Global.getChildNodes = _get_children_nochildren
# Import.getChildNodes = _get_children_nochildren
# From.getChildNodes = _get_children_nochildren
# Name.getChildNodes = _get_children_nochildren
# Str.getChildNodes = _get_children_nochildren
# Num.getChildNodes = _get_children_nochildren
# Pass.getChildNodes = _get_children_nochildren
# Eq.getChildNodes = _get_children_nochildren

# def _get_children_call(self):
#     children = [self.func]
#     children.extend(self.args)
#     children.extend(self.keywords)
#     if self.starargs:
#         children.extend(self.starargs)
#     if self.kwargs:
#         children.extend(self.kwargs)
#     return children
# CallFunc.getChildNodes = _get_children_call

# def _get_children_tryexcept(self):
#     return self.body + self.handlers + self.orelse
# TryExcept.getChildNodes = _get_children_tryexcept

# def _get_children_excepthandler(self):
#     children = []
#     if self.name is not None:
#         children.append(self.name)
#     if self.type is not None:
#         children.append(self.type)
#     children += self.body
#     return self.body
# excepthandler.getChildNodes = _get_children_excepthandler

# def _get_children_assign(self):
#     return self.targets + [self.value]
# Assign.getChildNodes = _get_children_assign

# def _get_children_augassign(self):
#     return [self.target, self.value]
# AugAssign.getChildNodes = _get_children_augassign

# def _get_children_if(self):
#     return [self.test] + self.body + self.orelse
# If.getChildNodes = _get_children_if

# def _get_children_print(self):
#     if self.dest:
#         return [self.dest] + self.values
#     return self.values
# Print.getChildNodes = _get_children_print

# def _get_children_compare(self):
#     return [self.left] + self.ops + self.comparators
# Compare.getChildNodes = _get_children_compare

# def _get_children_generatorexp(self):
#     return [self.elt] + self.generators
# GenExpr.getChildNodes = _get_children_generatorexp

# def _get_children_comprehension(self):
#     return [self.target] + [self.iter] + self.ifs
# comprehension.getChildNodes = _get_children_comprehension


# def getattr_as_string(node):
#     """return an ast.Getattr node as string"""
#     return '%s.%s' % (node.value.as_string(), node.attr)
# Getattr.as_string = getattr_as_string

# scoped nodes ################################################################

# def _get_children_body(self):
#     return self.body
# Module.getChildNodes = _get_children_body

# def _get_children_class(self):
#     return self.bases + self.body
# Class.getChildNodes = _get_children_class

# def _get_children_function(self):
#     return [self.defaults] + self.body
# Function.getChildNodes = _get_children_function
# Lambda.getChildNodes = _get_children_function


def _init_set_doc(node):
    node.doc = None
    try:
        if isinstance(node.body[0], Discard) and isinstance(node.body[0].value, Str):
            node.doc = node.body[0].value.s
    except IndexError:
        pass # ast built from scratch

def _init_function(node):
    # XXX tuple
    node.argnames = [n.id for n in node.args.args]
    node.defaults = node.args.defaults
    if node.args.vararg:
        node.argnames.append(node.args.vararg)
    if node.args.kwarg:
        node.argnames.append(node.args.kwarg)

init_class = _init_set_doc

def init_function(node):
    _init_set_doc(node)
    _init_function(node)
    
def init_lambda(node):
    _init_function(node)
    
 
def init_delete(node):
    pass

   
# validated

def init_assign(node):
    pass

def init_augassign(node):
    pass

def init_binop(node):
    node.op = BIN_OP_CLASSES[node.op.__class__]
    
def init_boolop(node):
    node.op = BOOL_OP_CLASSES[node.op.__class__]


def _compare_get_children(node):
    """override get_children for zipped fields"""
    yield node.left
    for ops, comparators in node.ops:
        yield comparators # we don't want the 'ops'
Compare.get_children = _compare_get_children

def init_compare(node):
    node.ops = [(CMP_OP_CLASSES[op.__class__], expr)
                for op, expr in zip(node.ops, node.comparators)]
    del node.comparators


def init_dict(node):
    node.items = zip(node.keys, node.values)
    del node.keys, node.values
    
def init_discard(node):
    pass

def init_exec(node):
    node.expr = node.body
    del node.body

def init_getattr(node):
    node.attrname = node.attr
    node.expr = node.value
    del node.attr, node.value
    
def init_for(node):
    pass

Import._astng_fields = ()
def init_import(node):
    node.names = [(alias.name, alias.asname) for alias in node.names]

def init_import_from(node):
    init_import(node)
    node.modname = node.module
    del node.module

def init_list(node):
    pass    

init_module = _init_set_doc

Name._astng_fields = ()
def init_name(node):
    node.name = node.id
    del node.id

def init_print(node):
    pass

def init_subscript(node):
    node.expr = node.value
    del node.value
    if hasattr(node.slice.value, 'elts'):
        node.subs = node.slice.value.elts
    else:
        node.subs = [node.slice.value]
    del node.slice
    
def init_try_except(node):
    pass

def init_try_finally(node):
    pass

def init_tuple(node):
    pass    
    
def init_unaryop(node):
    node.op = UNARY_OP_CLASSES[node.op.__class__]

def init_while(node):
    pass

# raw building ################################################################

def _add_docstring(node, doc):
    node.doc = doc
#     if doc:
#         expr = Expr()
#         node.body.append(expr)
#         expr.parent = None
#         docstr = Str()
#         docstr.s = doc
#         expr.value = docstr
#         docstr.parent = expr
    
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

def _const_factory(value):
    if isinstance(value, (int, long, complex)):
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
        argsnode.args.append(Name())
        argsnode.args[-1].name = arg
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
        basenode = Name()
        basenode.name = base
        node.bases.append(basenode)
        basenode.parent = node
    _add_docstring(node, doc)
    return node

class Proxy_(object): pass


class EmptyNode(object):
    """dummy class for some situations"""
    is_statement = False
    _astng_fields = ()

from _ast import Load as _Load, Store as _Store, Del as _Del
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
