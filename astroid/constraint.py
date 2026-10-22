# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Classes representing different types of constraints on inference values."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Self

from astroid import bases, helpers, nodes, util
from astroid.context import InferenceContext
from astroid.exceptions import (
    AstroidError,
    AstroidTypeError,
    InferenceError,
    MroError,
)
from astroid.typing import InferenceResult

_NameNodes = nodes.AssignAttr | nodes.Attribute | nodes.AssignName | nodes.Name


class Constraint(ABC):
    """Represents a single constraint on a variable."""

    def __init__(self, node: nodes.NodeNG, negate: bool) -> None:
        self.node = node
        """The node that this constraint applies to."""
        self.negate = negate
        """True if this constraint is negated. E.g., "is not" instead of "is"."""

    @classmethod
    @abstractmethod
    def match(
        cls, node: _NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Self | None:
        """Return a new constraint for node matched from expr, if expr matches
        the constraint pattern.

        If negate is True, negate the constraint.
        """

    @abstractmethod
    def satisfied_by(
        self, inferred: InferenceResult, context: InferenceContext
    ) -> bool:
        """Return True if this constraint is satisfied by the given inferred value."""


class NoneConstraint(Constraint):
    """Represents an "is None" or "is not None" constraint."""

    CONST_NONE: nodes.Const = nodes.Const(None)

    @classmethod
    def match(
        cls, node: _NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Self | None:
        """Return a new constraint for node matched from expr, if expr matches
        the constraint pattern.

        Negate the constraint based on the value of negate.
        """
        if isinstance(expr, nodes.Compare) and len(expr.ops) == 1:
            left = expr.left
            op, right = expr.ops[0]
            if op in {"is", "is not"} and (
                _matches(left, node) and _matches(right, cls.CONST_NONE)
            ):
                negate = (op == "is" and negate) or (op == "is not" and not negate)
                return cls(node=node, negate=negate)

        return None

    def satisfied_by(
        self, inferred: InferenceResult, context: InferenceContext
    ) -> bool:
        """Return True if this constraint is satisfied by the given inferred value."""
        # Assume true if uninferable
        if inferred is util.Uninferable:
            return True

        # Return the XOR of self.negate and matches(inferred, self.CONST_NONE)
        return self.negate ^ _matches(inferred, self.CONST_NONE)


class BooleanConstraint(Constraint):
    """Represents an "x" or "not x" constraint."""

    @classmethod
    def match(
        cls, node: _NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Self | None:
        """Return a new constraint for node if expr is node, else return None.

        ``not x`` is matched by ``_match_constraint``, which flips negate.
        """
        if _matches(expr, node):
            return cls(node=node, negate=negate)

        return None

    def satisfied_by(
        self, inferred: InferenceResult, context: InferenceContext
    ) -> bool:
        """Return True for uninferable results, or depending on negate flag:

        - negate=False: satisfied if boolean value is True
        - negate=True: satisfied if boolean value is False
        """
        inferred_booleaness = inferred.bool_value()
        if inferred is util.Uninferable or inferred_booleaness is util.Uninferable:
            return True

        return self.negate ^ inferred_booleaness


class TypeConstraint(Constraint):
    """Represents an "isinstance(x, y)" constraint."""

    def __init__(
        self, node: nodes.NodeNG, classinfo: nodes.NodeNG, negate: bool
    ) -> None:
        super().__init__(node=node, negate=negate)
        self.classinfo = classinfo

    @classmethod
    def match(
        cls, node: _NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Self | None:
        """Return a new constraint for node if expr matches the
        "isinstance(x, y)" pattern. Else, return None.
        """
        is_instance_call = (
            isinstance(expr, nodes.Call)
            and isinstance(expr.func, nodes.Name)
            and expr.func.name == "isinstance"
            and not expr.keywords
            and len(expr.args) == 2
        )
        if is_instance_call and _matches(expr.args[0], node):
            return cls(node=node, classinfo=expr.args[1], negate=negate)

        return None

    def satisfied_by(
        self, inferred: InferenceResult, context: InferenceContext
    ) -> bool:
        """Return True for uninferable results, or depending on negate flag:

        - negate=False: satisfied when inferred is an instance of the checked types.
        - negate=True: satisfied when inferred is not an instance of the checked types.
        """
        if inferred is util.Uninferable:
            return True

        # This method is called once per inferred value, with the same context.
        # Use a clone: inferring the classinfo pushes it onto the context's
        # inference path but only its first value is consumed, so nothing is
        # cached and a reused context would make the classinfo uninferable
        # from the second call on.
        context = context.clone()
        try:
            types = helpers.class_or_tuple_to_container(self.classinfo, context)
            matches_checked_types = helpers.object_isinstance(inferred, types, context)

            if matches_checked_types is util.Uninferable:
                return True

            return self.negate ^ matches_checked_types
        except (InferenceError, AstroidTypeError, MroError):
            return True


class CallableConstraint(Constraint):
    """Represents a "callable(x)" constraint."""

    @classmethod
    def match(
        cls, node: _NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Self | None:
        """Return a new constraint for node if expr matches the "callable(x)"
        pattern. Else, return None.
        """
        is_callable_call = (
            isinstance(expr, nodes.Call)
            and isinstance(expr.func, nodes.Name)
            and expr.func.name == "callable"
            and not expr.keywords
            and len(expr.args) == 1
        )
        if is_callable_call and _matches(expr.args[0], node):
            return cls(node=node, negate=negate)

        return None

    def satisfied_by(
        self, inferred: InferenceResult, context: InferenceContext
    ) -> bool:
        """Return True for uninferable results, or depending on negate flag:

        - negate=False: satisfied when inferred is callable.
        - negate=True: satisfied when inferred is not callable.
        """
        if inferred is util.Uninferable:
            return True

        # A base class that cannot be inferred may define __call__.
        if isinstance(inferred, bases.Instance) and not helpers.has_known_bases(
            inferred._proxied, context
        ):
            return True

        return self.negate ^ inferred.callable()


class EqualityConstraint(Constraint):
    """Represents a "==" or "!=" constraint."""

    def __init__(self, node: nodes.NodeNG, operand: nodes.NodeNG, negate: bool) -> None:
        super().__init__(node=node, negate=negate)
        self.operand = operand

    @classmethod
    def match(
        cls, node: _NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Self | None:
        """Return a new constraint for node if expr matches one of these patterns:

        - "node == operand" or "operand == node": use given negate value
        - "node != operand" or "operand != node": flip negate value

        Return None if no pattern matches.
        """
        if isinstance(expr, nodes.Compare) and len(expr.ops) == 1:
            left = expr.left
            op, right = expr.ops[0]
            matches_left = _matches(left, node)

            if op in {"==", "!="} and (matches_left or _matches(right, node)):
                operand = right if matches_left else left
                negate = (op == "==" and negate) or (op == "!=" and not negate)
                return cls(node=node, operand=operand, negate=negate)

        return None

    def satisfied_by(
        self, inferred: InferenceResult, context: InferenceContext
    ) -> bool:
        """Return True for uninferable/ambiguous results, or depending on negate flag:

        - negate=False: satisfied when both operands are equal.
        - negate=True: satisfied when both operands are not equal.

        Only comparisons between constants and callables are supported.
        """
        if inferred is util.Uninferable:
            return True

        operand_inferred = util.safe_infer(self.operand, context)
        if operand_inferred is util.Uninferable or operand_inferred is None:
            return True

        if isinstance(inferred, nodes.Const) and isinstance(
            operand_inferred, nodes.Const
        ):
            return self.negate ^ (inferred.value == operand_inferred.value)

        if inferred.callable() and operand_inferred.callable():
            return self.negate ^ (inferred is operand_inferred)

        return True


class _CompoundConstraint(Constraint):
    """Represents an "x and y" or "x or y" constraint."""

    def __init__(
        self,
        node: nodes.NodeNG,
        op: str,
        children: list[Constraint],
        negate: bool,
    ) -> None:
        super().__init__(node=node, negate=negate)
        self.op = op
        self.children = children

    @classmethod
    def match(
        cls, node: _NameNodes, expr: nodes.NodeNG, negate: bool = False
    ) -> Self | None:
        """Return a new constraint for node if expr matches an "x and y" or
        "x or y" pattern.

        Return None if expr is not a supported boolean expression, or if any
        operand does not match a constraint pattern.
        """
        if not (isinstance(expr, nodes.BoolOp) and expr.op in {"and", "or"}):
            return None

        children: list[Constraint] = []
        for value in expr.values:
            matches = list(_match_constraint(node, value, negate))
            if not matches:
                return None
            children.extend(matches)

        return cls(node=node, op=expr.op, children=children, negate=negate)

    def satisfied_by(
        self, inferred: InferenceResult, context: InferenceContext
    ) -> bool:
        """Return True for uninferable results, or depending on op and negate:

        - negate=False: all children must be satisfied for "and", or any for "or".
        - negate=True: any child must be satisfied for "and", or all for "or".
        """
        if inferred is util.Uninferable:
            return True

        results = (
            constraint.satisfied_by(inferred, context) for constraint in self.children
        )

        strict = (self.op == "and") ^ self.negate
        return all(results) if strict else any(results)


def get_constraints(
    expr: _NameNodes, frame: nodes.LocalsDictNodeNG
) -> dict[nodes.NodeNG, set[Constraint]]:
    """Returns the constraints for the given expression.

    The returned dictionary maps the node where the constraint was generated to the
    corresponding constraint(s).

    Constraints are computed statically by analysing the code surrounding expr.
    Currently this only supports constraints generated from if conditions,
    comprehension conditions, preceding operands in boolean operations, and
    preceding guard statements: asserts, ifs whose body ends with a return, raise,
    continue or break, and ifs whose body assigns expr.
    """
    current_node: nodes.NodeNG | None = expr
    constraints_mapping: dict[nodes.NodeNG, set[Constraint]] = {}
    name = (
        expr.attrname
        if isinstance(expr, (nodes.Attribute, nodes.AssignAttr))
        else expr.name
    )
    # Guards before a function, lambda, class or generator expression do not
    # constrain its body: it may run later, after a reassignment.
    collect_guards = True
    while current_node is not None and current_node is not frame:
        parent = current_node.parent
        constraints: set[Constraint] | None = None

        if isinstance(
            current_node,
            (nodes.FunctionDef, nodes.Lambda, nodes.ClassDef, nodes.GeneratorExp),
        ):
            collect_guards = False
        elif collect_guards and current_node.is_statement:
            if guards := _preceding_guards(current_node).get(name):
                _add_guards_constraints(expr, guards, constraints_mapping)

        if isinstance(parent, (nodes.If, nodes.IfExp)):
            branch, _ = parent.locate_child(current_node)
            if branch == "body":
                constraints = set(_match_constraint(expr, parent.test))
            elif branch == "orelse":
                constraints = set(_match_constraint(expr, parent.test, invert=True))
            if constraints:
                constraints_mapping[parent] = constraints

        elif isinstance(parent, nodes.BoolOp):
            # Later operands are evaluated only if all preceding ones are
            # truthy for "and", or all falsy for "or".
            index = parent.values.index(current_node)
            constraints = set()
            for previous_value in parent.values[:index]:
                constraints.update(
                    _match_constraint(expr, previous_value, invert=parent.op == "or")
                )
            if constraints:
                constraints_mapping[parent] = constraints
        elif isinstance(parent, nodes.Comprehension):
            try:
                index = parent.ifs.index(current_node)
            except ValueError:
                pass
            else:
                # Preceding conditions of the same generator guard this condition.
                _add_ifs_constraints(expr, parent.ifs[:index], constraints_mapping)
        elif isinstance(
            parent, (nodes.ListComp, nodes.SetComp, nodes.DictComp, nodes.GeneratorExp)
        ):
            branch, _ = parent.locate_child(current_node)
            if branch == "generators":
                # Conditions guard the iterables of all later generators.
                index = parent.generators.index(current_node)
                generators = parent.generators[:index]
            else:  # elt, key or value: guarded by all conditions
                generators = parent.generators
            for comprehension in generators:
                _add_ifs_constraints(expr, comprehension.ifs, constraints_mapping)
        current_node = parent

    return constraints_mapping


def constraint_applies(
    constraint_stmt: nodes.NodeNG, stmt: InferenceResult, expr: _NameNodes
) -> bool:
    """Return True if the constraints generated at constraint_stmt for expr apply
    to the values assigned by stmt.

    They do not apply to an assignment inside constraint_stmt, nor to one that can
    run between constraint_stmt and expr, as in ``if x is None: return``, then
    ``x = None``.
    """
    if constraint_stmt.parent_of(stmt):
        return False
    start = (constraint_stmt.end_lineno, constraint_stmt.end_col_offset)
    position = (stmt.lineno, stmt.col_offset)
    if None in start or None in position or position < start:
        return True
    # A position in another module says nothing about when the assignment runs.
    if stmt.root() is not constraint_stmt.root():
        return True
    end = _unconstrained_range_end(constraint_stmt, expr)
    return None in end or position > end


def _unconstrained_range_end(
    constraint_stmt: nodes.NodeNG, expr: _NameNodes
) -> tuple[int | None, int | None]:
    """Return the position up to which an assignment after constraint_stmt can
    reach expr without running constraint_stmt again.

    That is expr itself, or the end of the outermost loop containing expr but not
    constraint_stmt: an assignment after expr in that loop reaches expr on the next
    iteration.
    """
    end: nodes.NodeNG | None = None
    node = expr.parent
    while (
        node is not None
        and node is not constraint_stmt
        and not node.parent_of(constraint_stmt)
    ):
        if isinstance(node, (nodes.For, nodes.While)):
            end = node
        node = node.parent
    if end is None:
        return (expr.lineno, expr.col_offset)
    return (end.end_lineno, end.end_col_offset)


_preceding_guards_cache: dict[
    nodes.NodeNG, dict[str, tuple[nodes.If | nodes.Assert, ...]]
] = {}
"""The asserts and ifs preceding each statement in its block, by the names and
attribute names their test reads.

They do not depend on the constrained name, so they are computed once per block.
"""


def clear_preceding_guards_cache() -> None:
    """Clear the cache of the guard statements preceding each statement."""
    _preceding_guards_cache.clear()


def _add_guards_constraints(
    expr: _NameNodes,
    guards: tuple[nodes.If | nodes.Assert, ...],
    constraints_mapping: dict[nodes.NodeNG, set[Constraint]],
) -> None:
    """Add the constraints of guards for expr.

    After an assert, its test holds. After an if, its test is false for a value
    assigned before it, if its body cannot let that value through: the body exits,
    or it assigns expr again.
    """
    for guard in guards:
        is_if = isinstance(guard, nodes.If)
        constraints = set(_match_constraint(expr, guard.test, invert=is_if))
        if constraints and not (is_if and _lets_through(guard.body, expr)):
            constraints_mapping[guard] = constraints


def _lets_through(body: list[nodes.NodeNG], expr: _NameNodes) -> bool:
    """Return True if a value of expr assigned before body can reach the code
    after it.
    """
    if isinstance(body[-1], (nodes.Return, nodes.Raise, nodes.Continue, nodes.Break)):
        return False
    for stmt in body:
        if isinstance(stmt, nodes.Assign):
            targets = stmt.targets
        elif isinstance(stmt, nodes.AnnAssign) and stmt.value is not None:
            targets = [stmt.target]
        else:
            continue
        if any(_same_target(target, expr) for target in targets):
            return False
    return True


def _preceding_guards(
    stmt: nodes.NodeNG,
) -> dict[str, tuple[nodes.If | nodes.Assert, ...]]:
    """Return the asserts and ifs preceding stmt in its block, by the names and
    attribute names their test reads: a test that does not read a name cannot
    constrain it.
    """
    if (cached := _preceding_guards_cache.get(stmt)) is not None:
        return cached
    try:
        stmts = stmt.parent.child_sequence(stmt)
    except AstroidError:
        # A type comment annotation is not a child of its parent.
        stmts = [stmt]
    # Fill the cache for the whole block at once. Statements between two guards
    # share the same mapping.
    guards: dict[str, tuple[nodes.If | nodes.Assert, ...]] = {}
    for sibling in stmts:
        _preceding_guards_cache[sibling] = guards
        if isinstance(sibling, (nodes.If, nodes.Assert)):
            guards = guards.copy()
            for name in _read_names(sibling.test):
                guards[name] = (*guards.get(name, ()), sibling)
    return _preceding_guards_cache[stmt]


def _read_names(test: nodes.NodeNG) -> set[str]:
    """Return the names and attribute names that test reads."""
    return {
        node.name if isinstance(node, nodes.Name) else node.attrname
        for node in test.nodes_of_class((nodes.Name, nodes.Attribute))
    }


def _same_target(target: nodes.NodeNG, expr: _NameNodes) -> bool:
    """Return True if target assigns the name or attribute that expr reads."""
    if isinstance(target, nodes.AssignName) and isinstance(expr, nodes.Name):
        return target.name == expr.name
    if isinstance(target, nodes.AssignAttr) and isinstance(expr, nodes.Attribute):
        return target.attrname == expr.attrname and _matches(target.expr, expr.expr)
    return False


def _add_ifs_constraints(
    expr: _NameNodes,
    ifs: list[nodes.NodeNG],
    constraints_mapping: dict[nodes.NodeNG, set[Constraint]],
) -> None:
    """Add the constraints matching each comprehension condition in ifs."""
    for if_expr in ifs:
        constraints = set(_match_constraint(expr, if_expr))
        if constraints:
            constraints_mapping[if_expr] = constraints


_CONSTRAINTS_BY_NODE_TYPE: dict[type[nodes.NodeNG], tuple[type[Constraint], ...]] = {
    nodes.Attribute: (BooleanConstraint,),
    nodes.BoolOp: (_CompoundConstraint,),
    nodes.Call: (TypeConstraint, CallableConstraint),
    nodes.Compare: (NoneConstraint, EqualityConstraint),
    nodes.Name: (BooleanConstraint,),
    # No nodes.UnaryOp entry: _match_constraint handles ``not`` itself, by matching
    # the operand with the inversion flipped, so that any constraint can be negated.
}
"""Constraint types that can match each expression node type."""


def _matches(node1: nodes.NodeNG | bases.Proxy, node2: nodes.NodeNG) -> bool:
    """Returns True if the two nodes match."""
    if isinstance(node1, nodes.Name) and isinstance(node2, nodes.Name):
        return node1.name == node2.name
    if isinstance(node1, nodes.Attribute) and isinstance(node2, nodes.Attribute):
        return node1.attrname == node2.attrname and _matches(node1.expr, node2.expr)
    if isinstance(node1, nodes.Const) and isinstance(node2, nodes.Const):
        return node1.value == node2.value

    return False


def _match_constraint(
    node: _NameNodes, expr: nodes.NodeNG, invert: bool = False
) -> Iterator[Constraint]:
    """Yields all constraint patterns for node that match."""
    if isinstance(expr, nodes.UnaryOp) and expr.op == "not":
        yield from _match_constraint(node, expr.operand, not invert)
        return
    for constraint_cls in _CONSTRAINTS_BY_NODE_TYPE.get(type(expr), ()):
        constraint = constraint_cls.match(node, expr, invert)
        if constraint:
            yield constraint
