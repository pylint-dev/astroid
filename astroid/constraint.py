# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""Classes representing different types of constraints on inference values."""

from typing import Dict, Optional, Type, TypeVar, Union

from astroid import nodes, util

NameNodes = Union[nodes.AssignAttr, nodes.Attribute, nodes.AssignName, nodes.Name]
ConstraintT = TypeVar("ConstraintT", bound="Constraint")


class Constraint:
    """Represents a single constraint on a variable."""

    def __init__(self, node: nodes.NodeNG, negate: bool) -> None:
        self.node = node
        """The node that this constraint applies to."""
        self.negate = negate
        """True if this constraint is negated. E.g., "is not" instead of "is"."""

    @classmethod
    def match(
        cls: ConstraintT, node: NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Optional[ConstraintT]:
        """Return a new constraint for node matched from expr, if expr matches
        the constraint pattern.

        If negate is True, negate the constraint.
        """

    def satisfied_by(
        self, inferred: Union[nodes.NodeNG, Type[util.Uninferable]]
    ) -> bool:
        """Return True if this constraint is satisfied by the given inferred value."""
        return True


class NoneConstraint(Constraint):
    """Represents an "is None" or "is not None" constraint."""

    @classmethod
    def match(
        cls: ConstraintT, node: NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Optional[ConstraintT]:
        """Return a new constraint for node matched from expr, if expr matches
        the constraint pattern.

        Negate the constraint based on the value of negate.
        """
        if isinstance(expr, nodes.Compare) and len(expr.ops) == 1:
            left = expr.left
            op, right = expr.ops[0]
            const_none = nodes.Const(None)
            if op in {"is", "is not"} and (
                matches(left, node)
                and matches(right, const_none)
                or matches(left, const_none)
                and matches(right, node)
            ):
                negate = (op == "is" and negate) or (op == "is not" and not negate)
                return cls(node=node, negate=negate)

        return None

    def satisfied_by(
        self, inferred: Union[nodes.NodeNG, Type[util.Uninferable]]
    ) -> bool:
        """Return True if this constraint is satisfied by the given inferred value."""
        # Assume true if uninferable
        if inferred is util.Uninferable:
            return True

        if self.negate and matches(inferred, nodes.Const(None)):
            return False
        if not self.negate and not matches(inferred, nodes.Const(None)):
            return False

        return True


def matches(node1: nodes.NodeNG, node2: nodes.NodeNG) -> bool:
    """Returns True if the two nodes match."""
    if isinstance(node1, nodes.Name) and isinstance(node2, nodes.Name):
        return node1.name == node2.name
    if isinstance(node1, nodes.Attribute) and isinstance(node2, nodes.Attribute):
        return node1.attrname == node2.attrname and matches(node1.expr, node2.expr)
    if isinstance(node1, nodes.Const) and isinstance(node2, nodes.Const):
        return node1.value == node2.value

    return False


def get_constraints(
    expr: NameNodes, frame: nodes.LocalsDictNodeNG
) -> Dict[nodes.If, Constraint]:
    """Returns the constraints for the given expression.

    The returned dictionary maps the node where the constraint was generated to the
    corresponding constraint.

    Constraints are computed statically by analysing the code surrounding expr.
    Currently this only supports constraints generated from if conditions.
    """
    current_node: nodes.NodeNG = expr
    constraints = {}
    while current_node is not None and current_node is not frame:
        parent = current_node.parent
        if isinstance(parent, nodes.If):
            branch, _ = parent.locate_child(current_node)
            if branch == "body":
                constraint = match_constraint(expr, parent.test)
            elif branch == "orelse":
                constraint = match_constraint(expr, parent.test, invert=True)
            else:
                constraint = None

            if constraint:
                constraints[parent] = constraint
        current_node = parent

    return constraints


ALL_CONSTRAINTS = (NoneConstraint,)
"""All supported constraint types."""


def match_constraint(
    node: NameNodes, expr: nodes.NodeNG, invert: bool = False
) -> Optional[Constraint]:
    """Returns a constraint pattern for node, if one matches."""
    for constraint_cls in ALL_CONSTRAINTS:
        constraint = constraint_cls.match(node, expr, invert)
        if constraint:
            return constraint

    return None
