# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/LICENSE
from typing import Optional

from astroid.nodes.node_ng import NodeNG


class Statement(NodeNG):
    """Statement node adding a few attributes"""

    is_statement = True
    """Whether this node indicates a statement."""

    def next_sibling(self):
        """The next sibling statement node.

        :returns: The next sibling statement node.
        :rtype: NodeNG or None
        """
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        try:
            return stmts[index + 1]
        except IndexError:
            return None

    def previous_sibling(self):
        """The previous sibling statement.

        :returns: The previous sibling statement node.
        :rtype: NodeNG or None
        """
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        if index >= 1:
            return stmts[index - 1]
        return None


class Assert(Statement):
    """Class representing an :class:`ast.Assert` node.

    An :class:`Assert` node represents an assert statement.

    >>> from astroid.builder import extract_node
    >>> node = extract_node('assert len(things) == 10, "Not enough things"')
    >>> node
    <Assert l.1 at 0x7effe1d527b8>
    """

    _astroid_fields = ("test", "fail")

    def __init__(
        self,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
        parent: Optional[NodeNG] = None,
    ) -> None:
        """
        :param lineno: The line that this node appears on in the source code.

        :param col_offset: The column that this node appears on in the
            source code.

        :param parent: The parent node in the syntax tree.
        """
        self.test: Optional[NodeNG] = None
        """The test that passes or fails the assertion."""

        self.fail: Optional[NodeNG] = None  # can be None
        """The message shown when the assertion fails."""

        super().__init__(lineno=lineno, col_offset=col_offset, parent=parent)

    def postinit(
        self, test: Optional[NodeNG] = None, fail: Optional[NodeNG] = None
    ) -> None:
        """Do some setup after initialisation.

        :param test: The test that passes or fails the assertion.

        :param fail: The message shown when the assertion fails.
        """
        self.fail = fail
        self.test = test

    def get_children(self):
        yield self.test

        if self.fail is not None:
            yield self.fail


class Expr(Statement):
    """Class representing an :class:`ast.Expr` node.

    An :class:`Expr` is any expression that does not have its value used or
    stored.

    >>> from astroid.builder import extract_node
    >>> node = extract_node('method()')
    >>> node
    <Call l.1 at 0x7f23b2e352b0>
    >>> node.parent
    <Expr l.1 at 0x7f23b2e35278>
    """

    _astroid_fields = ("value",)

    def __init__(
        self,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
        parent: Optional[NodeNG] = None,
    ) -> None:
        """
        :param lineno: The line that this node appears on in the source code.

        :param col_offset: The column that this node appears on in the
            source code.

        :param parent: The parent node in the syntax tree.
        """
        self.value: Optional[NodeNG] = None
        """What the expression does."""

        super().__init__(lineno=lineno, col_offset=col_offset, parent=parent)

    def postinit(self, value: Optional[NodeNG] = None) -> None:
        """Do some setup after initialisation.

        :param value: What the expression does.
        """
        self.value = value

    def get_children(self):
        yield self.value

    def _get_yield_nodes_skip_lambdas(self):
        if not self.value.is_lambda:
            yield from self.value._get_yield_nodes_skip_lambdas()


class Raise(Statement):
    """Class representing an :class:`ast.Raise` node.

    >>> from astroid.builder import extract_node
    >>> node = extract_node('raise RuntimeError("Something bad happened!")')
    >>> node
    <Raise l.1 at 0x7f23b2e9e828>
    """

    _astroid_fields = ("exc", "cause")

    def __init__(
        self,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
        parent: Optional[NodeNG] = None,
    ) -> None:
        """
        :param lineno: The line that this node appears on in the source code.

        :param col_offset: The column that this node appears on in the
            source code.

        :param parent: The parent node in the syntax tree.
        """
        self.exc: Optional[NodeNG] = None  # can be None
        """What is being raised."""

        self.cause: Optional[NodeNG] = None  # can be None
        """The exception being used to raise this one."""

        super().__init__(lineno=lineno, col_offset=col_offset, parent=parent)

    def postinit(
        self,
        exc: Optional[NodeNG] = None,
        cause: Optional[NodeNG] = None,
    ) -> None:
        """Do some setup after initialisation.

        :param exc: What is being raised.

        :param cause: The exception being used to raise this one.
        """
        self.exc = exc
        self.cause = cause

    def raises_not_implemented(self):
        """Check if this node raises a :class:`NotImplementedError`.

        :returns: True if this node raises a :class:`NotImplementedError`,
            False otherwise.
        :rtype: bool
        """
        if not self.exc:
            return False
        for name in self.exc._get_name_nodes():
            if name.name == "NotImplementedError":
                return True
        return False

    def get_children(self):
        if self.exc is not None:
            yield self.exc

        if self.cause is not None:
            yield self.cause
