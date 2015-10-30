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

import abc
import warnings

import six


def register_implementation(base):
    def wrapped(impl):
        base.register(impl)
        return impl
    return wrapped


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


class Statement(NodeNG):
    """Represents a Statement node."""
    is_statement = True


class AssignName(NodeNG):
    """class representing an AssignName node"""


class DelName(NodeNG):
    """class representing a DelName node"""


class Name(NodeNG):
    """class representing a Name node"""


class Arguments(NodeNG):
    """class representing an Arguments node"""


class AssignAttr(NodeNG):
    """class representing an AssignAttr node"""


class Assert(Statement):
    """class representing an Assert node"""


class Assign(Statement):
    """class representing an Assign node"""


class AugAssign(Statement):
    """class representing an AugAssign node"""


class Repr(NodeNG):
    """class representing a Repr node"""


class BinOp(NodeNG):
    """class representing a BinOp node"""


class BoolOp(NodeNG):
    """class representing a BoolOp node"""


class Break(Statement):
    """class representing a Break node"""


class Call(NodeNG):
    """class representing a Call node"""


class Compare(NodeNG):
    """class representing a Compare node"""


class Comprehension(NodeNG):
    """class representing a Comprehension node"""


class Const(NodeNG):
    """represent a constant node like num, str, bool, None, bytes"""


class Continue(Statement):
    """class representing a Continue node"""


class Decorators(NodeNG):
    """class representing a Decorators node"""


class DelAttr(NodeNG):
    """class representing a DelAttr node"""


class Delete(Statement):
    """class representing a Delete node"""


class Dict(NodeNG):
    """class representing a Dict node"""


class Expr(Statement):
    """class representing a Expr node"""


class Ellipsis(NodeNG): # pylint: disable=redefined-builtin
    """class representing an Ellipsis node"""


class ExceptHandler(Statement):
    """class representing an ExceptHandler node"""


class Exec(Statement):
    """class representing an Exec node"""


class ExtSlice(NodeNG):
    """class representing an ExtSlice node"""


class For(Statement):
    """class representing a For node"""


class AsyncFor(For):
    """Asynchronous For built with `async` keyword."""


class Await(NodeNG):
    """Await node for the `await` keyword."""


class ImportFrom(Statement):
    """class representing a ImportFrom node"""


class Attribute(NodeNG):
    """class representing a Attribute node"""


class Global(Statement):
    """class representing a Global node"""


class If(Statement):
    """class representing an If node"""


class IfExp(NodeNG):
    """class representing an IfExp node"""


class Import(Statement):
    """class representing an Import node"""


class Index(NodeNG):
    """class representing an Index node"""


class Keyword(NodeNG):
    """class representing a Keyword node"""


class List(NodeNG):
    """class representing a List node"""


class Nonlocal(Statement):
    """class representing a Nonlocal node"""

class Pass(Statement):
    """class representing a Pass node"""


class Print(Statement):
    """class representing a Print node"""


class Raise(Statement):
    """class representing a Raise node"""


class Return(Statement):
    """class representing a Return node"""


class Set(NodeNG):
    """class representing a Set node"""


class Slice(NodeNG):
    """class representing a Slice node"""


class Starred(NodeNG):
    """class representing a Starred node"""


class Subscript(NodeNG):
    """class representing a Subscript node"""


class TryExcept(Statement):
    """class representing a TryExcept node"""


class TryFinally(Statement):
    """class representing a TryFinally node"""


class Tuple(NodeNG):
    """class representing a Tuple node"""

class UnaryOp(NodeNG):
    """class representing an UnaryOp node"""


class While(Statement):
    """class representing a While node"""

class With(Statement):
    """class representing a With node"""


class AsyncWith(With):
    """Asynchronous `with` built with the `async` keyword."""


class Yield(NodeNG):
    """class representing a Yield node"""


class YieldFrom(Yield):
    """Class representing a YieldFrom node. """


class DictUnpack(NodeNG):
    """Represents the unpacking of dicts into dicts using PEP 448."""


class Module(NodeNG):
    pass


class GeneratorExp(NodeNG):
    pass


class DictComp(NodeNG):
    pass


class SetComp(NodeNG):
    pass


class ListComp(NodeNG):
    pass


class Lambda(NodeNG):
    pass


class AsyncFunctionDef(NodeNG):
    pass


class ClassDef(Statement, NodeNG):
    pass


class FunctionDef(Statement, Lambda):
    pass


@six.add_metaclass(abc.ABCMeta)
class RuntimeObject(object):
    pass


class Instance(RuntimeObject):
    pass


class UnboundMethod(RuntimeObject):
    pass


class BoundMethod(UnboundMethod):
    pass


class Generator(RuntimeObject):
    pass
