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
:copyright: 2003-2010 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2010 Sylvain Thenault
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


