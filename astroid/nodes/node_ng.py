import pprint
import typing
from functools import singledispatch as _singledispatch
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Iterator,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

from astroid import decorators, util
from astroid.exceptions import AstroidError, InferenceError, UseInferenceDefault
from astroid.manager import AstroidManager
from astroid.nodes.as_string import AsStringVisitor
from astroid.nodes.const import OP_PRECEDENCE

if TYPE_CHECKING:
    from astroid import nodes

    T_Nodes = TypeVar(
        "T_Nodes",
        Type["nodes.AnnAssign"],
        Type["nodes.Arguments"],
        Type["nodes.Assert"],
        Type["nodes.Assign"],
        Type["nodes.AssignAttr"],
        Type["nodes.AssignName"],
        Type["nodes.AsyncFor"],
        Type["nodes.AsyncFunctionDef"],
        Type["nodes.AsyncWith"],
        Type["nodes.Attribute"],
        Type["nodes.AugAssign"],
        Type["nodes.Await"],
        Type["nodes.BinOp"],
        Type["nodes.BoolOp"],
        Type["nodes.Break"],
        Type["nodes.Call"],
        Type["nodes.ClassDef"],
        Type["nodes.Compare"],
        Type["nodes.Comprehension"],
        Type["nodes.Const"],
        Type["nodes.Continue"],
        Type["nodes.Decorators"],
        Type["nodes.DelAttr"],
        Type["nodes.DelName"],
        Type["nodes.Delete"],
        Type["nodes.Dict"],
        Type["nodes.DictComp"],
        Type["nodes.DictUnpack"],
        Type["nodes.Ellipsis"],
        Type["nodes.EmptyNode"],
        Type["nodes.ExceptHandler"],
        Type["nodes.Expr"],
        Type["nodes.ExtSlice"],
        Type["nodes.For"],
        Type["nodes.FormattedValue"],
        Type["nodes.FunctionDef"],
        Type["nodes.GeneratorExp"],
        Type["nodes.Global"],
        Type["nodes.If"],
        Type["nodes.IfExp"],
        Type["nodes.Import"],
        Type["nodes.ImportFrom"],
        Type["nodes.Index"],
        Type["nodes.JoinedStr"],
        Type["nodes.Keyword"],
        Type["nodes.Lambda"],
        Type["nodes.List"],
        Type["nodes.ListComp"],
        Type["nodes.Match"],
        Type["nodes.MatchAs"],
        Type["nodes.MatchCase"],
        Type["nodes.MatchClass"],
        Type["nodes.MatchMapping"],
        Type["nodes.MatchOr"],
        Type["nodes.MatchSequence"],
        Type["nodes.MatchSingleton"],
        Type["nodes.MatchStar"],
        Type["nodes.MatchValue"],
        Type["nodes.Module"],
        Type["nodes.Name"],
        Type["nodes.Nonlocal"],
        Type["nodes.Pass"],
        Type["nodes.Raise"],
        Type["nodes.Return"],
        Type["nodes.Set"],
        Type["nodes.SetComp"],
        Type["nodes.Slice"],
        Type["nodes.Starred"],
        Type["nodes.Subscript"],
        Type["nodes.TryExcept"],
        Type["nodes.TryFinally"],
        Type["nodes.Tuple"],
        Type["nodes.UnaryOp"],
        Type["nodes.Unknown"],
        Type["nodes.While"],
        Type["nodes.With"],
        Type["nodes.YieldFrom"],
        Type["nodes.Yield"],
        Type["nodes.Statement"],
        Type["nodes.Pattern"],
        Type["NodeNG"],
    )


class NodeNG:
    """A node of the new Abstract Syntax Tree (AST).

    This is the base class for all Astroid node classes.
    """

    is_statement: ClassVar[bool] = False
    """Whether this node indicates a statement."""
    optional_assign: ClassVar[
        bool
    ] = False  # True for For (and for Comprehension if py <3.0)
    """Whether this node optionally assigns a variable.

    This is for loop assignments because loop won't necessarily perform an
    assignment if the loop has no iterations.
    This is also the case from comprehensions in Python 2.
    """
    is_function: ClassVar[bool] = False  # True for FunctionDef nodes
    """Whether this node indicates a function."""
    is_lambda: ClassVar[bool] = False

    # Attributes below are set by the builder module or by raw factories
    _astroid_fields: ClassVar[typing.Tuple[str, ...]] = ()
    """Node attributes that contain child nodes.

    This is redefined in most concrete classes.
    """
    _other_fields: ClassVar[typing.Tuple[str, ...]] = ()
    """Node attributes that do not contain child nodes."""
    _other_other_fields: ClassVar[typing.Tuple[str, ...]] = ()
    """Attributes that contain AST-dependent fields."""
    # instance specific inference function infer(node, context)
    _explicit_inference = None

    def __init__(
        self,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
        parent: Optional["NodeNG"] = None,
    ) -> None:
        """
        :param lineno: The line that this node appears on in the source code.

        :param col_offset: The column that this node appears on in the
            source code.

        :param parent: The parent node in the syntax tree.
        """
        self.lineno: Optional[int] = lineno
        """The line that this node appears on in the source code."""

        self.col_offset: Optional[int] = col_offset
        """The column that this node appears on in the source code."""

        self.parent: Optional["NodeNG"] = parent
        """The parent node in the syntax tree."""

    def infer(self, context=None, **kwargs):
        """Get a generator of the inferred values.

        This is the main entry point to the inference system.

        .. seealso:: :ref:`inference`

        If the instance has some explicit inference function set, it will be
        called instead of the default interface.

        :returns: The inferred values.
        :rtype: iterable
        """
        if context is not None:
            context = context.extra_context.get(self, context)
        if self._explicit_inference is not None:
            # explicit_inference is not bound, give it self explicitly
            try:
                # pylint: disable=not-callable
                results = tuple(self._explicit_inference(self, context, **kwargs))
                if context is not None:
                    context.nodes_inferred += len(results)
                yield from results
                return
            except UseInferenceDefault:
                pass

        if not context:
            # nodes_inferred?
            yield from self._infer(context, **kwargs)
            return

        key = (self, context.lookupname, context.callcontext, context.boundnode)
        if key in context.inferred:
            yield from context.inferred[key]
            return

        generator = self._infer(context, **kwargs)
        results = []

        # Limit inference amount to help with performance issues with
        # exponentially exploding possible results.
        limit = AstroidManager().max_inferable_values
        for i, result in enumerate(generator):
            if i >= limit or (context.nodes_inferred > context.max_inferred):
                yield util.Uninferable
                break
            results.append(result)
            yield result
            context.nodes_inferred += 1

        # Cache generated results for subsequent inferences of the
        # same node using the same context
        context.inferred[key] = tuple(results)
        return

    def _repr_name(self):
        """Get a name for nice representation.

        This is either :attr:`name`, :attr:`attrname`, or the empty string.

        :returns: The nice name.
        :rtype: str
        """
        if all(name not in self._astroid_fields for name in ("name", "attrname")):
            return getattr(self, "name", "") or getattr(self, "attrname", "")
        return ""

    def __str__(self):
        rname = self._repr_name()
        cname = type(self).__name__
        if rname:
            string = "%(cname)s.%(rname)s(%(fields)s)"
            alignment = len(cname) + len(rname) + 2
        else:
            string = "%(cname)s(%(fields)s)"
            alignment = len(cname) + 1
        result = []
        for field in self._other_fields + self._astroid_fields:
            value = getattr(self, field)
            width = 80 - len(field) - alignment
            lines = pprint.pformat(value, indent=2, width=width).splitlines(True)

            inner = [lines[0]]
            for line in lines[1:]:
                inner.append(" " * alignment + line)
            result.append("{}={}".format(field, "".join(inner)))

        return string % {
            "cname": cname,
            "rname": rname,
            "fields": (",\n" + " " * alignment).join(result),
        }

    def __repr__(self):
        rname = self._repr_name()
        if rname:
            string = "<%(cname)s.%(rname)s l.%(lineno)s at 0x%(id)x>"
        else:
            string = "<%(cname)s l.%(lineno)s at 0x%(id)x>"
        return string % {
            "cname": type(self).__name__,
            "rname": rname,
            "lineno": self.fromlineno,
            "id": id(self),
        }

    def accept(self, visitor):
        """Visit this node using the given visitor."""
        func = getattr(visitor, "visit_" + self.__class__.__name__.lower())
        return func(self)

    def get_children(self) -> Iterator["NodeNG"]:
        """Get the child nodes below this node.

        :returns: The children.
        :rtype: iterable(NodeNG)
        """
        for field in self._astroid_fields:
            attr = getattr(self, field)
            if attr is None:
                continue
            if isinstance(attr, (list, tuple)):
                yield from attr
            else:
                yield attr
        yield from ()

    def last_child(self) -> Optional["NodeNG"]:
        """An optimized version of list(get_children())[-1]"""
        for field in self._astroid_fields[::-1]:
            attr = getattr(self, field)
            if not attr:  # None or empty listy / tuple
                continue
            if isinstance(attr, (list, tuple)):
                return attr[-1]
            return attr
        return None

    def parent_of(self, node):
        """Check if this node is the parent of the given node.

        :param node: The node to check if it is the child.
        :type node: NodeNG

        :returns: True if this node is the parent of the given node,
            False otherwise.
        :rtype: bool
        """
        parent = node.parent
        while parent is not None:
            if self is parent:
                return True
            parent = parent.parent
        return False

    def statement(self):
        """The first parent node, including self, marked as statement node.

        :returns: The first parent statement.
        :rtype: NodeNG
        """
        if self.is_statement:
            return self
        return self.parent.statement()

    def frame(self):
        """The first parent frame node.

        A frame node is a :class:`Module`, :class:`FunctionDef`,
        or :class:`ClassDef`.

        :returns: The first parent frame node.
        :rtype: Module or FunctionDef or ClassDef
        """
        return self.parent.frame()

    def scope(self):
        """The first parent node defining a new scope.

        :returns: The first parent scope node.
        :rtype: Module or FunctionDef or ClassDef or Lambda or GenExpr
        """
        if self.parent:
            return self.parent.scope()
        return None

    def root(self):
        """Return the root node of the syntax tree.

        :returns: The root node.
        :rtype: Module
        """
        if self.parent:
            return self.parent.root()
        return self

    def child_sequence(self, child):
        """Search for the sequence that contains this child.

        :param child: The child node to search sequences for.
        :type child: NodeNG

        :returns: The sequence containing the given child node.
        :rtype: iterable(NodeNG)

        :raises AstroidError: If no sequence could be found that contains
            the given child.
        """
        for field in self._astroid_fields:
            node_or_sequence = getattr(self, field)
            if node_or_sequence is child:
                return [node_or_sequence]
            # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
            if (
                isinstance(node_or_sequence, (tuple, list))
                and child in node_or_sequence
            ):
                return node_or_sequence

        msg = "Could not find %s in %s's children"
        raise AstroidError(msg % (repr(child), repr(self)))

    def locate_child(self, child):
        """Find the field of this node that contains the given child.

        :param child: The child node to search fields for.
        :type child: NodeNG

        :returns: A tuple of the name of the field that contains the child,
            and the sequence or node that contains the child node.
        :rtype: tuple(str, iterable(NodeNG) or NodeNG)

        :raises AstroidError: If no field could be found that contains
            the given child.
        """
        for field in self._astroid_fields:
            node_or_sequence = getattr(self, field)
            # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
            if child is node_or_sequence:
                return field, child
            if (
                isinstance(node_or_sequence, (tuple, list))
                and child in node_or_sequence
            ):
                return field, node_or_sequence
        msg = "Could not find %s in %s's children"
        raise AstroidError(msg % (repr(child), repr(self)))

    # FIXME : should we merge child_sequence and locate_child ? locate_child
    # is only used in are_exclusive, child_sequence one time in pylint.

    def next_sibling(self):
        """The next sibling statement node.

        :returns: The next sibling statement node.
        :rtype: NodeNG or None
        """
        return self.parent.next_sibling()

    def previous_sibling(self):
        """The previous sibling statement.

        :returns: The previous sibling statement node.
        :rtype: NodeNG or None
        """
        return self.parent.previous_sibling()

    # these are lazy because they're relatively expensive to compute for every
    # single node, and they rarely get looked at

    @decorators.cachedproperty
    def fromlineno(self) -> Optional[int]:
        """The first line that this node appears on in the source code."""
        if self.lineno is None:
            return self._fixed_source_line()
        return self.lineno

    @decorators.cachedproperty
    def tolineno(self) -> Optional[int]:
        """The last line that this node appears on in the source code."""
        if not self._astroid_fields:
            # can't have children
            last_child = None
        else:
            last_child = self.last_child()
        if last_child is None:
            return self.fromlineno
        return last_child.tolineno

    def _fixed_source_line(self) -> Optional[int]:
        """Attempt to find the line that this node appears on.

        We need this method since not all nodes have :attr:`lineno` set.
        """
        line = self.lineno
        _node = self
        try:
            while line is None:
                _node = next(_node.get_children())
                line = _node.lineno
        except StopIteration:
            _node = self.parent
            while _node and line is None:
                line = _node.lineno
                _node = _node.parent
        return line

    def block_range(self, lineno):
        """Get a range from the given line number to where this node ends.

        :param lineno: The line number to start the range at.
        :type lineno: int

        :returns: The range of line numbers that this node belongs to,
            starting at the given line number.
        :rtype: tuple(int, int or None)
        """
        return lineno, self.tolineno

    def set_local(self, name, stmt):
        """Define that the given name is declared in the given statement node.

        This definition is stored on the parent scope node.

        .. seealso:: :meth:`scope`

        :param name: The name that is being defined.
        :type name: str

        :param stmt: The statement that defines the given name.
        :type stmt: NodeNG
        """
        self.parent.set_local(name, stmt)

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.AnnAssign"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.AnnAssign"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Arguments"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Arguments"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Assert"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Assert"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Assign"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Assign"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.AssignAttr"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.AssignAttr"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.AssignName"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.AssignName"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.AsyncFor"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.AsyncFor"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.AsyncFunctionDef"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.AsyncFunctionDef"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.AsyncWith"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.AsyncWith"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Attribute"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Attribute"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.AugAssign"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.AugAssign"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Await"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Await"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.BinOp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.BinOp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.BoolOp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.BoolOp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Break"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Break"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Call"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Call"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.ClassDef"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.ClassDef"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Compare"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Compare"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Comprehension"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Comprehension"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Const"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Const"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Continue"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Continue"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Decorators"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Decorators"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.DelAttr"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.DelAttr"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.DelName"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.DelName"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Delete"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Delete"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Dict"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Dict"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.DictComp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.DictComp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.DictUnpack"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.DictUnpack"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Ellipsis"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Ellipsis"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.EmptyNode"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.EmptyNode"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.ExceptHandler"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.ExceptHandler"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Expr"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Expr"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.ExtSlice"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.ExtSlice"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.For"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.For"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.FormattedValue"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.FormattedValue"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.FunctionDef"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.FunctionDef"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.GeneratorExp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.GeneratorExp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Global"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Global"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.If"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.If"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.IfExp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.IfExp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Import"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Import"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.ImportFrom"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.ImportFrom"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Index"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Index"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.JoinedStr"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.JoinedStr"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Keyword"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Keyword"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Lambda"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Lambda"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.List"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.List"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.ListComp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.ListComp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Match"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Match"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchAs"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchAs"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchCase"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchCase"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchClass"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchClass"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchMapping"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchMapping"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchOr"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchOr"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchSequence"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchSequence"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchSingleton"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchSingleton"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchStar"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchStar"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.MatchValue"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.MatchValue"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Module"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Module"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Name"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Name"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Nonlocal"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Nonlocal"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Pass"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Pass"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Raise"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Raise"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Return"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Return"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Set"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Set"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.SetComp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.SetComp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Slice"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Slice"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Starred"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Starred"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Subscript"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Subscript"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.TryExcept"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.TryExcept"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.TryFinally"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.TryFinally"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Tuple"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Tuple"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.UnaryOp"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.UnaryOp"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Unknown"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Unknown"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.While"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.While"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.With"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.With"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.YieldFrom"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.YieldFrom"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Yield"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Yield"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Statement"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Statement"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["nodes.Pattern"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["nodes.Pattern"]:
        ...

    @overload
    def nodes_of_class(
        self: "NodeNG",
        klass: Type["NodeNG"],
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["NodeNG"]:
        ...

    def nodes_of_class(
        self: "NodeNG",
        klass: "T_Nodes",
        skip_klass: Union[None, Type["NodeNG"], Tuple[Type["NodeNG"], ...]] = None,
    ) -> Iterator["NodeNG"]:
        """Get the nodes (including this one or below) of the given types.

        :param klass: The types of node to search for.
        :type klass: builtins.type or tuple(builtins.type)

        :param skip_klass: The types of node to ignore. This is useful to ignore
            subclasses of :attr:`klass`.
        :type skip_klass: builtins.type or tuple(builtins.type)

        :returns: The node of the given types.
        :rtype: iterable(NodeNG)
        """
        if isinstance(self, klass):
            yield self

        if skip_klass is None:
            for child_node in self.get_children():
                yield from child_node.nodes_of_class(klass, skip_klass)

            return

        for child_node in self.get_children():
            if isinstance(child_node, skip_klass):
                continue
            yield from child_node.nodes_of_class(klass, skip_klass)

    @decorators.cached
    def _get_assign_nodes(self):
        return []

    def _get_name_nodes(self):
        for child_node in self.get_children():
            yield from child_node._get_name_nodes()

    def _get_return_nodes_skip_functions(self):
        yield from ()

    def _get_yield_nodes_skip_lambdas(self):
        yield from ()

    def _infer_name(self, frame, name):
        # overridden for ImportFrom, Import, Global, TryExcept and Arguments
        pass

    def _infer(self, context=None):
        """we don't know how to resolve a statement by default"""
        # this method is overridden by most concrete classes
        raise InferenceError(
            "No inference function for {node!r}.", node=self, context=context
        )

    def inferred(self):
        """Get a list of the inferred values.

        .. seealso:: :ref:`inference`

        :returns: The inferred values.
        :rtype: list
        """
        return list(self.infer())

    def instantiate_class(self):
        """Instantiate an instance of the defined class.

        .. note::

            On anything other than a :class:`ClassDef` this will return self.

        :returns: An instance of the defined class.
        :rtype: object
        """
        return self

    def has_base(self, node):
        """Check if this node inherits from the given type.

        :param node: The node defining the base to look for.
            Usually this is a :class:`Name` node.
        :type node: NodeNG
        """
        return False

    def callable(self):
        """Whether this node defines something that is callable.

        :returns: True if this defines something that is callable,
            False otherwise.
        :rtype: bool
        """
        return False

    def eq(self, value):
        return False

    def as_string(self) -> str:
        """Get the source code that this node represents."""
        return AsStringVisitor()(self)

    def repr_tree(
        self,
        ids=False,
        include_linenos=False,
        ast_state=False,
        indent="   ",
        max_depth=0,
        max_width=80,
    ) -> str:
        """Get a string representation of the AST from this node.

        :param ids: If true, includes the ids with the node type names.
        :type ids: bool

        :param include_linenos: If true, includes the line numbers and
            column offsets.
        :type include_linenos: bool

        :param ast_state: If true, includes information derived from
            the whole AST like local and global variables.
        :type ast_state: bool

        :param indent: A string to use to indent the output string.
        :type indent: str

        :param max_depth: If set to a positive integer, won't return
            nodes deeper than max_depth in the string.
        :type max_depth: int

        :param max_width: Attempt to format the output string to stay
            within this number of characters, but can exceed it under some
            circumstances. Only positive integer values are valid, the default is 80.
        :type max_width: int

        :returns: The string representation of the AST.
        :rtype: str
        """

        @_singledispatch
        def _repr_tree(node, result, done, cur_indent="", depth=1):
            """Outputs a representation of a non-tuple/list, non-node that's
            contained within an AST, including strings.
            """
            lines = pprint.pformat(
                node, width=max(max_width - len(cur_indent), 1)
            ).splitlines(True)
            result.append(lines[0])
            result.extend([cur_indent + line for line in lines[1:]])
            return len(lines) != 1

        # pylint: disable=unused-variable,useless-suppression; doesn't understand singledispatch
        @_repr_tree.register(tuple)
        @_repr_tree.register(list)
        def _repr_seq(node, result, done, cur_indent="", depth=1):
            """Outputs a representation of a sequence that's contained within an AST."""
            cur_indent += indent
            result.append("[")
            if not node:
                broken = False
            elif len(node) == 1:
                broken = _repr_tree(node[0], result, done, cur_indent, depth)
            elif len(node) == 2:
                broken = _repr_tree(node[0], result, done, cur_indent, depth)
                if not broken:
                    result.append(", ")
                else:
                    result.append(",\n")
                    result.append(cur_indent)
                broken = _repr_tree(node[1], result, done, cur_indent, depth) or broken
            else:
                result.append("\n")
                result.append(cur_indent)
                for child in node[:-1]:
                    _repr_tree(child, result, done, cur_indent, depth)
                    result.append(",\n")
                    result.append(cur_indent)
                _repr_tree(node[-1], result, done, cur_indent, depth)
                broken = True
            result.append("]")
            return broken

        # pylint: disable=unused-variable,useless-suppression; doesn't understand singledispatch
        @_repr_tree.register(NodeNG)
        def _repr_node(node, result, done, cur_indent="", depth=1):
            """Outputs a strings representation of an astroid node."""
            if node in done:
                result.append(
                    indent
                    + "<Recursion on {} with id={}".format(
                        type(node).__name__, id(node)
                    )
                )
                return False
            done.add(node)

            if max_depth and depth > max_depth:
                result.append("...")
                return False
            depth += 1
            cur_indent += indent
            if ids:
                result.append(f"{type(node).__name__}<0x{id(node):x}>(\n")
            else:
                result.append("%s(" % type(node).__name__)
            fields = []
            if include_linenos:
                fields.extend(("lineno", "col_offset"))
            fields.extend(node._other_fields)
            fields.extend(node._astroid_fields)
            if ast_state:
                fields.extend(node._other_other_fields)
            if not fields:
                broken = False
            elif len(fields) == 1:
                result.append("%s=" % fields[0])
                broken = _repr_tree(
                    getattr(node, fields[0]), result, done, cur_indent, depth
                )
            else:
                result.append("\n")
                result.append(cur_indent)
                for field in fields[:-1]:
                    result.append("%s=" % field)
                    _repr_tree(getattr(node, field), result, done, cur_indent, depth)
                    result.append(",\n")
                    result.append(cur_indent)
                result.append("%s=" % fields[-1])
                _repr_tree(getattr(node, fields[-1]), result, done, cur_indent, depth)
                broken = True
            result.append(")")
            return broken

        result = []
        _repr_tree(self, result, set())
        return "".join(result)

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        The boolean value of a node can have three
        possible values:

            * False: For instance, empty data structures,
              False, empty strings, instances which return
              explicitly False from the __nonzero__ / __bool__
              method.
            * True: Most of constructs are True by default:
              classes, functions, modules etc
            * Uninferable: The inference engine is uncertain of the
              node's value.

        :returns: The boolean value of this node.
        :rtype: bool or Uninferable
        """
        return util.Uninferable

    def op_precedence(self):
        # Look up by class name or default to highest precedence
        return OP_PRECEDENCE.get(self.__class__.__name__, len(OP_PRECEDENCE))

    def op_left_associative(self):
        # Everything is left associative except `**` and IfExp
        return True
