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
"""
on all nodes :
 .is_statement, returning true if the node should be considered as a
  statement node
 .root(), returning the root node of the tree (i.e. a Module)
 .previous_sibling(), returning previous sibling statement node
 .next_sibling(), returning next sibling statement node
 .statement(), returning the first parent node marked as statement node
 .frame(), returning the first node defining a new local scope (i.e.
  Module, Function or Class)
 .set_local(name, node), define an identifier <name> on the first parent frame,
  with the node defining it. This is used by the astng builder and should not
  be used from out there.

on From and Import :
 .real_name(name),

:author:    Sylvain Thenault
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com

"""

__docformat__ = "restructuredtext en"

from logilab.astng.node_classes import (Arguments, AssAttr, Assert,
    Assign, AssName, AugAssign, Backquote, BinOp, BoolOp, Break, CallFunc, Compare,
    Comprehension, Const, Continue, Decorators, DelAttr, DelName, Delete,
    Dict, Discard, Ellipsis, EmptyNode, ExceptHandler, Exec, ExtSlice, For,
    From, Getattr, Global, If, IfExp, Import, Index, Keyword,
    List, ListComp, Name, Pass, Print, Raise, Return, Slice, Subscript,
    TryExcept, TryFinally, Tuple, UnaryOp, While, With, Yield, const_factory )
from logilab.astng.scoped_nodes import Module, GenExpr, Lambda, Function, Class


# astng fields definition ####################################################
Arguments._astng_fields = ('args', 'defaults')
AssAttr._astng_fields = ('expr',)
Assert._astng_fields = ('test', 'fail',)
Assign._astng_fields = ('targets', 'value',)
AssName._astng_fields = ()
AugAssign._astng_fields = ('target', 'value',)
Backquote._astng_fields = ('value',)
BinOp._astng_fields = ('left', 'right',)
BoolOp._astng_fields = ('values',)
Break._astng_fields = ()
CallFunc._astng_fields = ('func', 'args', 'starargs', 'kwargs')
Class._astng_fields = ('bases', 'body',) # name
Compare._astng_fields = ('left', 'ops',)
Comprehension._astng_fields = ('target', 'iter' ,'ifs')
Const._astng_fields = ()
Continue._astng_fields = ()
Decorators._astng_fields = ('nodes',)
DelAttr._astng_fields = ('expr',)
Delete._astng_fields = ('targets', )
DelName._astng_fields = ()
Dict._astng_fields = ('items',)
Discard._astng_fields = ('value',)
Ellipsis._astng_fields = ()
EmptyNode._astng_fields = ()
ExceptHandler._astng_fields = ('type', 'name', 'body',)
Exec._astng_fields = ('expr', 'globals', 'locals',)
ExtSlice._astng_fields =('dims',)
For._astng_fields = ('target', 'iter', 'body', 'orelse',)
From._astng_fields = ()
Function._astng_fields = ('decorators', 'args', 'body')
GenExpr._astng_fields = ('elt', 'generators')
Getattr._astng_fields = ('expr',) # (former value), attr (now attrname), ctx
Global._astng_fields = ()
If._astng_fields = ('test', 'body', 'orelse')
IfExp._astng_fields = ('test', 'body', 'orelse')
Import._astng_fields = ()
Index._astng_fields = ('value',)
Keyword._astng_fields = ('value',)
Lambda._astng_fields = ('args', 'body',)
List._astng_fields = ('elts',)  # ctx
ListComp._astng_fields = ('elt', 'generators')
Module._astng_fields = ('body',)
Name._astng_fields = () # id, ctx
Pass._astng_fields = ()
Print._astng_fields = ('dest', 'values',) # nl
Raise._astng_fields = ('type', 'inst', 'tback')
Return._astng_fields = ('value',)
Slice._astng_fields = ('lower', 'upper', 'step')
Subscript._astng_fields = ('value', 'slice')
TryExcept._astng_fields = ('body', 'handlers', 'orelse',)
TryFinally._astng_fields = ('body', 'finalbody',)
Tuple._astng_fields = ('elts',)  # ctx
UnaryOp._astng_fields = ('operand',)
With._astng_fields = ('expr', 'vars', 'body')
While._astng_fields = ('test', 'body', 'orelse',)
Yield._astng_fields = ('value',)



