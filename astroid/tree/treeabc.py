# copyright 2003-2015 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.

"""Abstract classes for nodes and other runtime objects.

The idea is that these objects are used for isinstance checks and
any other use cases where the need for a concrete type does not exist,
while other cases, such as instantiating a node, should use the concrete
types instead.
"""

import abc

import six



@six.add_metaclass(abc.ABCMeta)
class NodeNG(object):
    """Base Class for all Astroid node classes.

    It represents a node of the new abstract syntax tree.
    """
    is_statement = False

    def __init__(self, lineno=None, col_offset=None, parent=None):
        self.lineno = lineno
        self.col_offset = col_offset
        self.parent = parent

    @abc.abstractmethod
    def infer(self, context=None, **kwargs):
        """Main interface to the interface system, return a generator on inferred values."""


# pylint: disable=abstract-method

class Statement(NodeNG):
    """Represents a Statement node."""
    is_statement = True


class AssignName(NodeNG):
    """Class representing an AssignName node"""


class DelName(NodeNG):
    """Class representing a DelName node"""


class Name(NodeNG):
    """Class representing a Name node"""


class Arguments(NodeNG):
    """Class representing an Arguments node"""


class AssignAttr(NodeNG):
    """Class representing an AssignAttr node"""


class Assert(Statement):
    """Class representing an Assert node"""


class Assign(Statement):
    """Class representing an Assign node"""


class AugAssign(Statement):
    """Class representing an AugAssign node"""


class Repr(NodeNG):
    """Class representing a Repr node"""


class BinOp(NodeNG):
    """Class representing a BinOp node"""


class BoolOp(NodeNG):
    """Class representing a BoolOp node"""


class Break(Statement):
    """Class representing a Break node"""


class Call(NodeNG):
    """Class representing a Call node"""


class Compare(NodeNG):
    """Class representing a Compare node"""


class Comprehension(NodeNG):
    """Class representing a Comprehension node"""


class Const(NodeNG):
    """Represent a constant node like num, str, bool, None, bytes"""


class Continue(Statement):
    """Class representing a Continue node"""


class Decorators(NodeNG):
    """Class representing a Decorators node"""


class DelAttr(NodeNG):
    """Class representing a DelAttr node"""


class Delete(Statement):
    """Class representing a Delete node"""


class Dict(NodeNG):
    """Class representing a Dict node"""


class Expr(Statement):
    """Class representing a Expr node"""


class Ellipsis(NodeNG): # pylint: disable=redefined-builtin
    """Class representing an Ellipsis node"""


class ExceptHandler(Statement):
    """Class representing an ExceptHandler node"""


class Exec(Statement):
    """Class representing an Exec node"""


class ExtSlice(NodeNG):
    """Class representing an ExtSlice node"""


class For(Statement):
    """Class representing a For node"""


class AsyncFor(For):
    """Asynchronous For built with `async` keyword."""


class Await(NodeNG):
    """Await node for the `await` keyword."""


class ImportFrom(Statement):
    """Class representing a ImportFrom node"""


class Attribute(NodeNG):
    """Class representing a Attribute node"""


class Global(Statement):
    """Class representing a Global node"""


class If(Statement):
    """Class representing an If node"""


class IfExp(NodeNG):
    """Class representing an IfExp node"""


class Import(Statement):
    """Class representing an Import node"""


class Index(NodeNG):
    """Class representing an Index node"""


class Keyword(NodeNG):
    """Class representing a Keyword node"""


class List(NodeNG):
    """Class representing a List node"""


class Nonlocal(Statement):
    """Class representing a Nonlocal node"""


class Pass(Statement):
    """Class representing a Pass node"""


class Print(Statement):
    """Class representing a Print node"""


class Raise(Statement):
    """Class representing a Raise node"""


class Return(Statement):
    """Class representing a Return node"""


class Set(NodeNG):
    """Class representing a Set node"""


class Slice(NodeNG):
    """Class representing a Slice node"""


class Starred(NodeNG):
    """Class representing a Starred node"""


class Subscript(NodeNG):
    """Class representing a Subscript node"""


class TryExcept(Statement):
    """Class representing a TryExcept node"""


class TryFinally(Statement):
    """Class representing a TryFinally node"""


class Tuple(NodeNG):
    """Class representing a Tuple node"""


class UnaryOp(NodeNG):
    """Class representing an UnaryOp node"""


class While(Statement):
    """Class representing a While node"""


class With(Statement):
    """Class representing a With node"""


class AsyncWith(With):
    """Asynchronous `with` built with the `async` keyword."""


class Yield(NodeNG):
    """Class representing a Yield node"""


class YieldFrom(Yield):
    """Class representing a YieldFrom node. """


class DictUnpack(NodeNG):
    """Represents the unpacking of dicts into dicts using PEP 448."""


class Module(NodeNG):
    """Class representing a Module node."""


class GeneratorExp(NodeNG):
    """Class representing a GeneratorExp node."""


class DictComp(NodeNG):
    """Class representing a generator comprehension node."""


class SetComp(NodeNG):
    """Class representing a set comprehension node."""


class ListComp(NodeNG):
    """Class representing a list comprehension node."""


class Lambda(NodeNG):
    """Class representing a lambda comprehension node."""


class AsyncFunctionDef(NodeNG):
    """Class representing an asynchronous function node."""


class ClassDef(Statement, NodeNG):
    """Class representing a class definition node."""


class FunctionDef(Statement, Lambda):
    """Class representing a function node."""


class InterpreterObject(NodeNG):
    pass
