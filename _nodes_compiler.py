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
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2008 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""
from __future__ import generators

__docformat__ = "restructuredtext en"

import sys
from compiler.ast import AssAttr, AssList, AssName, \
     AssTuple, Assert, Assign, AugAssign, \
     Backquote, Break, CallFunc, Class, \
     Compare, Const, Continue, Dict, Discard, \
     Ellipsis, EmptyNode, Exec, \
     For, From, Function, Getattr, Global, \
     If, Import, Invert, Keyword, Lambda, \
     List, ListComp, ListCompFor, ListCompIf, Module, Name, Node, \
     Pass, Print, Raise, Return, Slice, \
     Sliceobj, Stmt, Subscript, TryExcept, TryFinally, Tuple, \
     While, Yield


try:
    # introduced in python 2.4
    from compiler.ast import GenExpr, GenExprFor, GenExprIf, GenExprInner
except:
    class GenExpr:
        """dummy GenExpr node, shouldn't be used with py < 2.4"""
    class GenExprFor: 
        """dummy GenExprFor node, shouldn't be used with py < 2.4"""
    class GenExprIf: 
        """dummy GenExprIf node, shouldn't be used with py < 2.4"""
    class GenExprInner: 
        """dummy GenExprInner node, shouldn't be used with py < 2.4"""
try:
    # introduced in python 2.4
    from compiler.ast import Decorators
except:
    class Decorators:
        """dummy Decorators node, shouldn't be used with py < 2.4"""

try:
    # introduced in python 2.5
    from compiler.ast import With
except:
    class With:
        """dummy With node, shouldn't be used since py < 2.5"""

# additional nodes

class ExceptHandler(Node):
    def __init__(self, type, name, body, lineno):
        self.type = type
        self.name = name
        self.body = body
        self.lineno = lineno

class BinOp(Node):
    """replace Add, Div, FloorDiv, Mod, Mul, Power, Sub nodes"""
    from compiler.ast import Add, Div, FloorDiv, Mod, Mul, Power, Sub
    from compiler.ast import Bitand, Bitor, Bitxor, LeftShift, RightShift
    OP_CLASSES = {Add: '+',
                  Div: '/',
                  FloorDiv: '//',
                  Mod: '%',
                  Mul: '*',
                  Power: '**',
                  Sub: '-',
                  Bitand: '&',
                  Bitor: '|',
                  Bitxor: '^',
                  LeftShift: '<<',
                  RightShift: '>>'}
    
class BoolOp(Node):
    """replace And, Or"""
    from compiler.ast import And, Or
    OP_CLASSES = {And: 'and',
                  Or: 'or'}
    
class UnaryOp(Node):
    """replace UnaryAdd, UnarySub, Not"""
    from compiler.ast import UnaryAdd, UnarySub, Not
    OP_CLASSES = {UnaryAdd: '+',
                  UnarySub: '-',
                  Not: 'not'}


class Delete(Node):
    """represent del statements"""


###############################################################################
        

COMPREHENSIONS_SCOPES = (GenExprFor, ListCompFor)

def assattr_as_string(node):
    """return an ast.AssAttr node as string"""
    if node.flags == 'OP_DELETE':
        return 'del %s.%s' % (node.expr.as_string(), node.attrname)
    return '%s.%s' % (node.expr.as_string(), node.attrname)
AssAttr.as_string = assattr_as_string

def asslist_as_string(node):
    """return an ast.AssList node as string"""
    string = ', '.join([n.as_string() for n in node.nodes])
    return '[%s]' % string
AssList.as_string = asslist_as_string

def assname_as_string(node):
    """return an ast.AssName node as string"""
    if node.flags == 'OP_DELETE':
        return 'del %s' % node.name
    return node.name
AssName.as_string = assname_as_string

def asstuple_as_string(node):
    """return an ast.AssTuple node as string"""
    string = ', '.join([n.as_string() for n in node.nodes])
    # fix for del statement
    return string.replace(', del ', ', ')
AssTuple.as_string = asstuple_as_string

Const.eq = lambda self, value: self.value == value

def const_as_string(node):
    """return an ast.Const node as string"""
    return repr(node.value)
Const.as_string = const_as_string

def decorators_scope(self):
    # skip the function node to go directly to the upper level scope
    return self.parent.parent.scope()
Decorators.scope = decorators_scope

def empty_as_string(node):
    return ''
EmptyNode.as_string = empty_as_string

EmptyNode.getChildNodes = lambda self: ()

# introduced in python 2.5
From.level = 0 # will be overiden by instance attribute with py>=2.5

def genexprinner_as_string(node):
    """return an ast.GenExpr node as string"""
    return '%s %s' % (node.expr.as_string(), ' '.join([n.as_string()
                                                       for n in node.quals]))
GenExprInner.as_string = genexprinner_as_string

def genexprfor_as_string(node):
    """return an ast.GenExprFor node as string"""
    return 'for %s in %s %s' % (node.assign.as_string(),
                                node.iter.as_string(),
                                ' '.join([n.as_string() for n in node.ifs]))
GenExprFor.as_string = genexprfor_as_string

def genexprif_as_string(node):
    """return an ast.GenExprIf node as string"""
    return 'if %s' % node.test.as_string()
GenExprIf.as_string = genexprif_as_string

def keyword_as_string(node):
    """return an ast.Keyword node as string"""
    return '%s=%s' % (node.name, node.expr.as_string())
Keyword.as_string = keyword_as_string

def listcompfor_as_string(node):
    """return an ast.ListCompFor node as string"""
    return 'for %s in %s %s' % (node.assign.as_string(),
                                node.list.as_string(),
                                ' '.join([n.as_string() for n in node.ifs]))
ListCompFor.as_string = listcompfor_as_string

def listcompif_as_string(node):
    """return an ast.ListCompIf node as string"""
    return 'if %s' % node.test.as_string()
ListCompIf.as_string = listcompif_as_string

def sliceobj_as_string(node):
    """return an ast.Sliceobj node as string"""
    return ':'.join([n.as_string() for n in node.nodes])
Sliceobj.as_string = sliceobj_as_string

# scoped nodes ################################################################

def init_function(node):
    # remove Stmt node
    node.body = node.code.nodes
    del node.code
    node.argnames = list(node.argnames)

def init_lambda(node):
     node.body = node.code
     node.argnames = list(node.argnames)
     del node.code

def init_class(node):
    # remove Stmt node
    node.body = node.code.nodes
    del node.code

def init_assert(node):
    pass

def init_assname(node):
    if node.flags == 'OP_DELETE':
        node.targets = [Name(node.name)]
        node.__class__ = Delete
    elif node.flags == 'OP_ASSIGN':
        node.__class__ = Name
    elif node.flags not in ('OP_DELETE', 'OP_ASSIGN'):
        print "AssName flags:", node.flags
        raise
    del node.flags

def init_asstuple(node):
    if node.nodes[0].flags  == 'OP_DELETE':
        node.__class__ = Delete
        node.targets = [Name(item.name) for item in node.nodes]
        del node.nodes
    else:
        print "Uncatched AssTuple", node
        raise

# validated

def init_assign(node):
    node.value = node.expr
    del node.expr
    node.targets = node.nodes
    for target in node.targets:
        if isinstance(target, AssName):
            target.__class__ = Name
            del target.flags
        elif isinstance(target, AssTuple):
            target.__class__ = Tuple
        elif isinstance(target, AssAttr):
            target.__class__ = Getattr
    del node.nodes


def init_augassign(node):
    node.value = node.expr
    del node.expr
    node.target = node.node
    del node.node

def init_binop(node):
    node.op = BinOp.OP_CLASSES[node.__class__]
    node.__class__ = BinOp

def init_boolop(node):
    node.op = BoolOp.OP_CLASSES[node.__class__]
    node.__class__ = BoolOp
    node.values = node.nodes
    del node.nodes

def init_callfunc(node):
    node.func = node.node
    node.starargs = node.star_args
    node.kwargs = node.dstar_args
    del node.node, node.star_args, node.dstar_args

def init_compare(node):
    node.left = node.expr
    node.ops = [op[1] for op in node.ops] # we dont want the operators
    del node.expr

def init_dict(node):
    node.items = list(node.items)

def init_discard(node):
    node.value = node.expr
    del node.expr

def _init_else_node(node):
    # remove Stmt node if exists
    if node.else_:
        node.orelse = node.else_.nodes
    else:
        node.orelse = []
    del node.else_

def init_exec(node):
    pass

def init_for(node):
    node.target = node.assign
    del node.assign
    node.iter = node.list
    del node.list
    node.body = node.body.nodes
    _init_else_node(node)

def init_getattr(node):
    pass

def init_if(node):
    node.tests = [(cond, expr.nodes) for cond, expr in node.tests]
    _init_else_node(node)

def init_import(node):
    pass

def init_import_from(node):
    pass

def init_list(node):
    node.elts = list(node.nodes) # tuple if empty list
    del node.nodes

def init_keyword(node):
    node.value = node.expr
    del node.expr

def init_listcomp(node):
    node.elt = node.expr
    node.generators = node.quals
    del node.expr, node.quals

def init_listcompfor(node):
    node.iter = node.list
    node.target = node.assign
    node.target.__class__ = Name
    if node.ifs:
        node.ifs = node.ifs[0].test
    del node.assign, node.list


def init_module(node):
    # remove Stmt node
    node.body = node.node.nodes
    del node.node

def init_name(node):
    pass


def init_num(node):
    pass

def init_str(node):
    pass


def init_print(node, nl=False):
    node.values = node.nodes
    del node.nodes
    node.nl = nl

def init_printnl(node):
    node.__class__ = Print
    init_print(node, True)

def init_raise(node):
    node.type = node.expr1
    node.inst = node.expr2
    node.tback = node.expr3
    del node.expr1, node.expr2, node.expr3

def init_subscript(node):
    pass

def init_try_except(node):
    node.body = node.body.nodes
    # remove Stmt node
    node.handlers = [ExceptHandler(exctype, excobj, body.nodes, node.lineno)
                     for exctype, excobj, body in node.handlers]
    _init_else_node(node)


def init_try_finally(node):
    # remove Stmt nodes
    node.body = node.body.nodes
    node.finalbody = node.final.nodes
    del node.final

init_tuple = init_list

def init_unaryop(node):
    node.op = UnaryOp.OP_CLASSES[node.__class__]
    node.__class__ = UnaryOp
    node.operand = node.expr
    del node.expr

def init_while(node):
    node.body = node.body.nodes
    _init_else_node(node)


# raw building ################################################################

def module_factory(doc):
    node = Module(doc, None)
    del node.node
    node.body = []
    return node
    
def dict_factory():
    return Dict([])

if sys.version_info < (2, 5):
    def import_from_factory(modname, membername):
        return From(modname, ( (membername, None), ) )
else:
    def import_from_factory(modname, membername):
        return From(modname, ( (membername, None), ), 0)

def _const_factory(value):
    return Const(value)

# introduction of decorators has changed the Function initializer arguments
if sys.version_info >= (2, 4):
    def function_factory(name, args, defaults, flag=0, doc=None):
        """create and initialize a astng Function node"""
        # first argument is now a list of decorators
        func = Function(Decorators([]), name, args, defaults, flag, doc, None)
        del func.code
        func.body = []
        return func
    
else:    
    def function_factory(name, args, defaults, flag=0, doc=None):
        """create and initialize a astng Function node"""
        func = Function(name, args, defaults, flag, doc, None)
        del func.code
        func.body = []
        return func

def class_factory(name, basenames=None, doc=None):
    """create and initialize a astng Class node"""
    node = Class(name, [], doc, None)
    del node.code
    node.body = []
    bases = [Name(base) for base in basenames]
    for base in bases:
        base.parent = node
    node.bases = bases
    return node

class Proxy_: pass


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
