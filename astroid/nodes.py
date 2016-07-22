# Copyright (c) 2006-2011, 2013 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2014-2016 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015-2016 Cara Vinson <ceridwenv@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""
on all nodes :
 .is_statement, returning true if the node should be considered as a
  statement node
 .root(), returning the root node of the tree (i.e. a Module)
 .previous_sibling(), returning previous sibling statement node
 .next_sibling(), returning next sibling statement node
 .statement(), returning the first parent node marked as statement node
 .frame(), returning the first node defining a new local scope (i.e.
  Module, FunctionDef or ClassDef)
 .set_local(name, node), define an identifier <name> on the first parent frame,
  with the node defining it. This is used by the astroid builder and should not
  be used from out there.

on ImportFrom and Import :
 .real_name(name),


"""
# pylint: disable=unused-import,redefined-builtin

from astroid.tree.node_classes import (
    Arguments, AssignAttr, Assert, Assign,
    AssignName, AugAssign, Repr, BinOp, BoolOp, Break, Call, Compare,
    Comprehension, Const, Continue, Decorators, DelAttr, DelName, Delete,
    Dict, Empty, Expr, Ellipsis, ExceptHandler, Exec, ExtSlice, For,
    ImportFrom, Attribute, Global, If, IfExp, Import, Index, Keyword,
    List, Name, NameConstant, Nonlocal, Pass, Parameter, Print, Raise, Return, Set, Slice,
    Starred, Subscript, TryExcept, TryFinally, Tuple, UnaryOp, While, With,
    WithItem, Yield, YieldFrom, AsyncFor, Await, AsyncWith,
    # Node not present in the builtin ast module.
    DictUnpack,
    # Special nodes for building from live objects.
    InterpreterObject, ReservedName, Unknown
)
from astroid.tree.scoped_nodes import (
    Module, GeneratorExp, Lambda, DictComp,
    ListComp, SetComp, FunctionDef, ClassDef,
    AsyncFunctionDef,
)



ALL_NODE_CLASSES = (
    AsyncFunctionDef, AsyncFor, AsyncWith, Await,

    Arguments, AssignAttr, Assert, Assign, AssignName, AugAssign,
    Repr, BinOp, BoolOp, Break,
    Call, ClassDef, Compare, Comprehension, Const, Continue,
    Decorators, DelAttr, DelName, Delete,
    Dict, DictComp, DictUnpack, Expr,
    Ellipsis, ExceptHandler, Exec, ExtSlice,
    For, ImportFrom, FunctionDef,
    Attribute, GeneratorExp, Global,
    If, IfExp, Import, Index, InterpreterObject,
    Keyword,
    Lambda, List, ListComp,
    Name, NameConstant, Nonlocal,
    Module,
    Parameter, Pass, Print,
    Raise, ReservedName, Return,
    Set, SetComp, Slice, Starred, Subscript,
    TryExcept, TryFinally, Tuple,
    UnaryOp, Unknown,
    While, With, WithItem,
    Yield, YieldFrom,
    )
