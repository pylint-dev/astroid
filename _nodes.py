# -*- coding: utf-8 -*-
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
Module containing the node classes; it is only used for avoiding circular imports
"""

from __future__ import generators

__docformat__ = "restructuredtext en"

from itertools import imap

try:
    from logilab.astng._nodes_ast import *
    from logilab.astng._nodes_ast import _const_factory
    AST_MODE = '_ast'
except ImportError:
    from logilab.astng._nodes_compiler import *
    from logilab.astng._nodes_compiler import _const_factory
    AST_MODE = 'compiler'


INFER_NEED_NAME_STMTS = (From, Import, Global, TryExcept)
LOOP_SCOPES = (Comprehension, For,)


STMT_NODES = (
    Assert, Assign, AugAssign, Break, Class, Continue, Delete, Discard,
    ExceptHandler, Exec, For, From, Function, Global, If, Import, Pass, Print,
    Raise, Return, TryExcept, TryFinally, While, With, Yield
    )

ALL_NODES = STMT_NODES + (
    Arguments, AssAttr, AssName, BinOp, BoolOp, Backquote,  CallFunc, Compare,
    Comprehension, Const, Decorators, DelAttr, DelName, Dict, Ellipsis,
    EmptyNode,  ExtSlice, Getattr,  GenExpr, IfExp, Index, Keyword, Lambda,
    List,  ListComp, Module, Name, Slice, Subscript, UnaryOp, Tuple
    )

# constants ... ##############################################################

CONST_CLS = {
    list: List,
    tuple: Tuple,
    dict: Dict,
    }

def const_factory(value):
    """return an astng node for a python value"""
    try:
        # if value is of class list, tuple, dict use specific class, not Const
        cls = CONST_CLS[value.__class__]
        node = cls()
        if isinstance(node, Dict):
            node.items = ()
        else:
            node.elts = ()
    except KeyError:
        try:
            node = Const(value)
        except KeyError:
            node = _const_factory(value)
    return node

