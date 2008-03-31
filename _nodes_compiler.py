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
"""python < 2.5 compiler package compatibility module

:author:    Sylvain Thenault
:copyright: 2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2008 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""
from __future__ import generators

__docformat__ = "restructuredtext en"

import sys
from compiler.ast import Add, And, AssAttr, AssList, AssName, \
     AssTuple, Assert, Assign, AugAssign, \
     Backquote, Bitand, Bitor, Bitxor, Break, CallFunc, Class, \
     Compare, Const, Continue, Dict, Discard, Div, \
     Ellipsis, EmptyNode, Exec, FloorDiv, \
     For, From, Function, Getattr, Global, \
     If, Import, Invert, Keyword, Lambda, LeftShift, \
     List, ListComp, ListCompFor, ListCompIf, Mod, Module, Mul, Name, Node, \
     Not, Or, Pass, Power, Print, Printnl, Raise, Return, RightShift, Slice, \
     Sliceobj, Stmt, Sub, Subscript, TryExcept, TryFinally, Tuple, UnaryAdd, \
     UnarySub, While, Yield
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


def is_statement(self):
    """return true if the node should be considered as statement node
    """
    if isinstance(self.parent, Stmt):
        return self
    return None
Node.is_statement = property(is_statement)

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

def discard_as_string(node):
    """return an ast.Discard node as string"""
    return node.expr.as_string()
Discard.as_string = discard_as_string

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

def getattr_as_string(node):
    """return an ast.Getattr node as string"""
    return '%s.%s' % (node.expr.as_string(), node.attrname)
Getattr.as_string = getattr_as_string

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

def printnl_as_string(node):
    """return an ast.Printnl node as string"""
    nodes = ', '.join([n.as_string() for n in node.nodes])
    if node.dest:
        return 'print >> %s, %s' % (node.dest.as_string(), nodes)
    return 'print %s' % nodes
Printnl.as_string = printnl_as_string

def sliceobj_as_string(node):
    """return an ast.Sliceobj node as string"""
    return ':'.join([n.as_string() for n in node.nodes])
Sliceobj.as_string = sliceobj_as_string

def stmt_as_string(node):
    """return an ast.Stmt node as string"""
    stmts = '\n'.join([n.as_string() for n in node.nodes])
    if isinstance(node.parent, Module):
        return stmts
    return stmts.replace('\n', '\n    ')
Stmt.as_string = stmt_as_string

# scoped nodes ################################################################

def module_append_node(self, child_node):
    """append a child version specific to Module node"""
    self.node.nodes.append(child_node)
    child_node.parent = self
Module._append_node = module_append_node

def _append_node(self, child_node):
    """append a child, linking it in the tree"""
    self.code.nodes.append(child_node)
    child_node.parent = self
Class._append_node = _append_node
Function._append_node = _append_node

#
def init_module(node):
    return node

def init_function(node):
    node.argnames = list(node.argnames)
    return node

def init_class(node):
    return node

def init_import(node):
    return node

def init_assign(node):
    node.value = node.expr
    node.targets = node.nodes
    return node

# raw building ################################################################

def module_factory(doc):
    node = Module(doc, Stmt([]))
    node.node.parent = node
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
        func = Function(Decorators([]), name, args, defaults, flag, doc,
                        Stmt([]))
        func.code.parent = func
        return func
    
else:    
    def function_factory(name, args, defaults, flag=0, doc=None):
        """create and initialize a astng Function node"""
        func = Function(name, args, defaults, flag, doc, Stmt([]))
        func.code.parent = func
        return func

def class_factory(name, basenames=None, doc=None):
    """create and initialize a astng Class node"""
    klass = Class(name, [], doc, Stmt([]))
    bases = [Name(base) for base in basenames]
    for base in bases:
        base.parent = klass
    klass.bases = bases
    klass.code.parent = klass
    for name, value in ( ('__name__', name),
                         #('__module__', node.root().name),
                         ):
        const = const_factory(value)
        const.parent = klass
        klass.locals[name] = [const]
    return klass
