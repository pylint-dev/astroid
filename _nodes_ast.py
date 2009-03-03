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
                  If, Import,
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
                  comprehension as Comprehension,
                  keyword as Keyword
                  )

from _ast import Num, Str, Eq, alias, arguments

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

from _ast import UAdd as _UAdd, USub as _USub, Not as _Not, Invert as _Invert
UNARY_OP_CLASSES = {_UAdd: '+',
                    _USub: '-',
                    _Not: 'not',
                    _Invert: '~'}

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

from logilab.astng.utils import ASTVisitor


class AssAttr(Node):
    """represent Attribute Assignment statements"""

class AssName(Node):
    """represent AssName statements"""

class Const(Node):
    """represent a Str or Num node"""

class DelAttr(Node):
    """represent del attribute statements"""

class DelName(Node):
    """represent del statements"""

class EmptyNode(Node):
    """represent a Empty node for compatibility"""

class Decorators(Node):
    """represent a Decorator node"""
    def __init__(self, items):
        self.items = items

##  some auxiliary functions ##########################

def _recurse_if(ifnode, tests, orelse):
    """recurse on nested If nodes"""
    tests.append( (ifnode.test, ifnode.body) )
    del ifnode.test, ifnode.body
    if ifnode.orelse:
        if isinstance( ifnode.orelse[0], If):
            tests, orelse =  _recurse_if(ifnode.orelse[0], tests, orelse)
            del ifnode.orelse[0]
        else:
            orelse = ifnode.orelse
    return tests, orelse

def _init_set_doc(node):
    node.doc = None
    try:
        if isinstance(node.body[0], Discard) and isinstance(node.body[0].value, Str):
            node.doc = node.body[0].value.s
            node.body = node.body[1:]
    except IndexError:
        pass # ast built from scratch


def _init_function(node):
    argnames = []
    for arg in node.args.args:
        if isinstance(arg, Name):
            argnames.append(arg.id )
        elif isinstance(arg, Tuple):
            argnames.extend( elt.id for elt in arg.elts )
    node.argnames = argnames
    node.defaults = node.args.defaults
    if node.args.vararg:
        node.argnames.append(node.args.vararg)
    if node.args.kwarg:
        node.argnames.append(node.args.kwarg)
    flags = 0
    if node.args.vararg:
        flags += 4
    if node.args.kwarg:
        flags += 8
    node.flags = flags
    del node.args

class TreeRebuilder(ASTVisitor):
    """REbuilds the _ast tree to become an ASTNG tree"""

    # #  visit_<node> methods  # # ##########################################

    def __init__(self, rebuild_visitor):
        self.visitor = rebuild_visitor

    def visit_assert(self, node):
        node.fail = node.msg
        del node.msg

    def visit_binop(self, node):
        node.op = BIN_OP_CLASSES[node.op.__class__]
    
    def visit_boolop(self, node):
        node.op = BOOL_OP_CLASSES[node.op.__class__]
    
    def visit_callfunc(self, node):
        node.args.extend(node.keywords)
        del node.keywords

    def visit_class(self, node):
        _init_set_doc(node)

    def visit_compare(self, node):
        node.ops = [(CMP_OP_CLASSES[op.__class__], expr)
                    for op, expr in zip(node.ops, node.comparators)]
        del node.comparators

    def visit_dict(self, node):
        node.items = zip(node.keys, node.values)
        del node.keys, node.values

    def visit_exec(self, node):
        node.expr = node.body
        node.globals, node.locals = node.locals, node.globals # XXX ?
        del node.body

    def visit_function(self, node):
        _init_set_doc(node)
        _init_function(node)
        node.decorators = Decorators(node.decorators)

    def visit_getattr(self, node):
        node.attrname = node.attr
        node.expr = node.value
        del node.attr, node.value
        if isinstance(self.visitor.asscontext, Delete):
            node.__class__ = DelAttr
        elif self.visitor.asscontext is not None:
            node.__class__ = AssAttr
        self.visitor.asscontext = None # disable asscontext on 'Name' childnode
        
    def visit_if(self, node):
        tests, orelse = _recurse_if(node, [], [])
        node.tests = tests
        node.orelse = orelse
    
    def visit_import(self, node):
        node.names = [(alias.name, alias.asname) for alias in node.names]
    
    def visit_from(self, node):
        node.names = [(alias.name, alias.asname) for alias in node.names]
        node.modname = node.module
        del node.module

    def visit_lambda(self, node):
        _init_function(node)

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
    
    def visit_subscript(self, node):
        node.expr = node.value
        slices = node.slice
        if hasattr(slices, 'value'): # Index
            node.subs = [slices.value]
            node.sliceflag = 'index'
        elif hasattr(slices, 'lower'): # Slice
            node.subs = [slices.lower, slices.upper]
            if slices.step:
                node.subs.append(slices.step)
            node.sliceflag = 'slice'
        del node.slice, node.value

    def visit_unaryop(self, node):
        node.op = UNARY_OP_CLASSES[node.op.__class__]

    def visit_with(self, node):
        """build compiler like node """
        node.vars = node.optional_vars
        node.expr = node.context_expr
        del node.optional_vars, node.context_expr

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
    node = Function()
    node.decorators = []
    node.body = []
    node.name = name
    # XXX ensure we get a compatible representation
    #argsnode = arguments()
    node.args = args = []
    for arg in args:
        args.append(Name())
        args.args[-1].name = arg
        args.args[-1].parent = argsnode
    #argsnode.defaults = []
    node.defaults = defaults = []
    for default in defaults:
        defaults.append(const_factory(default))
        defaults[-1].parent = argsnode
    #argsnode.kwarg = None # XXX
    #argsnode.vararg = None # XXX
    #argsnode.parent = node
    #node.args = argsnode
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
