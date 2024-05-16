# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import contextlib
import unittest
from collections.abc import Callable, Iterator
from typing import Any

import pytest

import astroid
from astroid import extract_node, nodes
from astroid.const import PY310_PLUS, PY312_PLUS
from astroid.exceptions import InferenceError
from astroid.manager import AstroidManager
from astroid.util import Uninferable, UninferableBase


@contextlib.contextmanager
def _add_transform(
    manager: AstroidManager,
    node: type,
    transform: Callable,
    predicate: Any | None = None,
) -> Iterator:
    manager.register_transform(node, transform, predicate)
    try:
        yield
    finally:
        manager.unregister_transform(node, transform, predicate)


class ProtocolTests(unittest.TestCase):
    def assertConstNodesEqual(
        self, nodes_list_expected: list[int], nodes_list_got: list[nodes.Const]
    ) -> None:
        self.assertEqual(len(nodes_list_expected), len(nodes_list_got))
        for node in nodes_list_got:
            self.assertIsInstance(node, nodes.Const)
        for node, expected_value in zip(nodes_list_got, nodes_list_expected):
            self.assertEqual(expected_value, node.value)

    def assertNameNodesEqual(
        self, nodes_list_expected: list[str], nodes_list_got: list[nodes.Name]
    ) -> None:
        self.assertEqual(len(nodes_list_expected), len(nodes_list_got))
        for node in nodes_list_got:
            self.assertIsInstance(node, nodes.Name)
        for node, expected_name in zip(nodes_list_got, nodes_list_expected):
            self.assertEqual(expected_name, node.name)

    def test_assigned_stmts_simple_for(self) -> None:
        assign_stmts = extract_node(
            """
        for a in (1, 2, 3):  #@
          pass

        for b in range(3): #@
          pass
        """
        )

        for1_assnode = next(assign_stmts[0].nodes_of_class(nodes.AssignName))
        assigned = list(for1_assnode.assigned_stmts())
        self.assertConstNodesEqual([1, 2, 3], assigned)

        for2_assnode = next(assign_stmts[1].nodes_of_class(nodes.AssignName))
        self.assertRaises(InferenceError, list, for2_assnode.assigned_stmts())

    def test_assigned_stmts_nested_for_tuple(self) -> None:
        assign_stmts = extract_node(
            """
        for a, (b, c) in [(1, (2, 3))]:  #@
          pass
        """
        )

        assign_nodes = assign_stmts.nodes_of_class(nodes.AssignName)

        for1_assnode = next(assign_nodes)
        assigned = list(for1_assnode.assigned_stmts())
        self.assertConstNodesEqual([1], assigned)

        for2_assnode = next(assign_nodes)
        assigned2 = list(for2_assnode.assigned_stmts())
        self.assertConstNodesEqual([2], assigned2)

    def test_assigned_stmts_nested_for_dict(self) -> None:
        assign_stmts = extract_node(
            """
        for a, (b, c) in {1: ("a", str), 2: ("b", bytes)}.items():  #@
            pass
        """
        )
        assign_nodes = assign_stmts.nodes_of_class(nodes.AssignName)

        # assigned: [1, 2]
        for1_assnode = next(assign_nodes)
        assigned = list(for1_assnode.assigned_stmts())
        self.assertConstNodesEqual([1, 2], assigned)

        # assigned2: ["a", "b"]
        for2_assnode = next(assign_nodes)
        assigned2 = list(for2_assnode.assigned_stmts())
        self.assertConstNodesEqual(["a", "b"], assigned2)

        # assigned3: [str, bytes]
        for3_assnode = next(assign_nodes)
        assigned3 = list(for3_assnode.assigned_stmts())
        self.assertNameNodesEqual(["str", "bytes"], assigned3)

    def test_assigned_stmts_starred_for(self) -> None:
        assign_stmts = extract_node(
            """
        for *a, b in ((1, 2, 3), (4, 5, 6, 7)): #@
            pass
        """
        )

        for1_starred = next(assign_stmts.nodes_of_class(nodes.Starred))
        assigned = next(for1_starred.assigned_stmts())
        assert isinstance(assigned, astroid.List)
        assert assigned.as_string() == "[1, 2]"

    def _get_starred_stmts(self, code: str) -> list | UninferableBase:
        assign_stmt = extract_node(f"{code} #@")
        starred = next(assign_stmt.nodes_of_class(nodes.Starred))
        return next(starred.assigned_stmts())

    def _helper_starred_expected_const(self, code: str, expected: list[int]) -> None:
        stmts = self._get_starred_stmts(code)
        self.assertIsInstance(stmts, nodes.List)
        stmts = stmts.elts
        self.assertConstNodesEqual(expected, stmts)

    def _helper_starred_expected(self, code: str, expected: UninferableBase) -> None:
        stmts = self._get_starred_stmts(code)
        self.assertEqual(expected, stmts)

    def _helper_starred_inference_error(self, code: str) -> None:
        assign_stmt = extract_node(f"{code} #@")
        starred = next(assign_stmt.nodes_of_class(nodes.Starred))
        self.assertRaises(InferenceError, list, starred.assigned_stmts())

    def test_assigned_stmts_starred_assnames(self) -> None:
        self._helper_starred_expected_const("a, *b = (1, 2, 3, 4) #@", [2, 3, 4])
        self._helper_starred_expected_const("*a, b = (1, 2, 3) #@", [1, 2])
        self._helper_starred_expected_const("a, *b, c = (1, 2, 3, 4, 5) #@", [2, 3, 4])
        self._helper_starred_expected_const("a, *b = (1, 2) #@", [2])
        self._helper_starred_expected_const("*b, a = (1, 2) #@", [1])
        self._helper_starred_expected_const("[*b] = (1, 2) #@", [1, 2])

    def test_assigned_stmts_starred_yes(self) -> None:
        # Not something iterable and known
        self._helper_starred_expected("a, *b = range(3) #@", Uninferable)
        # Not something inferable
        self._helper_starred_expected("a, *b = balou() #@", Uninferable)
        # In function, unknown.
        self._helper_starred_expected(
            """
        def test(arg):
            head, *tail = arg #@""",
            Uninferable,
        )
        # These cases aren't worth supporting.
        self._helper_starred_expected(
            "a, (*b, c), d = (1, (2, 3, 4), 5) #@", Uninferable
        )

    def test_assigned_stmts_starred_inside_call(self) -> None:
        """Regression test for https://github.com/pylint-dev/pylint/issues/6372."""
        code = "string_twos = ''.join(str(*y) for _, *y in [[1, 2], [1, 2]]) #@"
        stmt = extract_node(code)
        starred = next(stmt.nodes_of_class(nodes.Starred))
        starred_stmts = starred.assigned_stmts()
        self.assertIs(next(starred_stmts), Uninferable)
        # Generator exhausted after one call
        with self.assertRaises(StopIteration):
            next(starred_stmts)

    def test_assign_stmts_starred_fails(self) -> None:
        # Too many starred
        self._helper_starred_inference_error("a, *b, *c = (1, 2, 3) #@")
        # This could be solved properly, but it complicates needlessly the
        # code for assigned_stmts, without offering real benefit.
        self._helper_starred_inference_error(
            "(*a, b), (c, *d) = (1, 2, 3), (4, 5, 6) #@"
        )

    def test_assigned_stmts_assignments(self) -> None:
        assign_stmts = extract_node(
            """
        c = a #@

        d, e = b, c #@
        """
        )

        simple_assnode = next(assign_stmts[0].nodes_of_class(nodes.AssignName))
        assigned = list(simple_assnode.assigned_stmts())
        self.assertNameNodesEqual(["a"], assigned)

        assnames = assign_stmts[1].nodes_of_class(nodes.AssignName)
        simple_mul_assnode_1 = next(assnames)
        assigned = list(simple_mul_assnode_1.assigned_stmts())
        self.assertNameNodesEqual(["b"], assigned)
        simple_mul_assnode_2 = next(assnames)
        assigned = list(simple_mul_assnode_2.assigned_stmts())
        self.assertNameNodesEqual(["c"], assigned)

    def test_assigned_stmts_annassignments(self) -> None:
        annassign_stmts = extract_node(
            """
        a: str = "abc"  #@
        b: str  #@
        """
        )
        simple_annassign_node = next(
            annassign_stmts[0].nodes_of_class(nodes.AssignName)
        )
        assigned = list(simple_annassign_node.assigned_stmts())
        self.assertEqual(1, len(assigned))
        self.assertIsInstance(assigned[0], nodes.Const)
        self.assertEqual(assigned[0].value, "abc")

        empty_annassign_node = next(annassign_stmts[1].nodes_of_class(nodes.AssignName))
        assigned = list(empty_annassign_node.assigned_stmts())
        self.assertEqual(1, len(assigned))
        self.assertIs(assigned[0], Uninferable)

    def test_sequence_assigned_stmts_not_accepting_empty_node(self) -> None:
        def transform(node: nodes.Assign) -> None:
            node.root().locals["__all__"] = [node.value]

        manager = astroid.MANAGER
        with _add_transform(manager, astroid.Assign, transform):
            module = astroid.parse(
                """
            __all__ = ['a']
            """
            )
            module.wildcard_import_names()

    def test_not_passing_uninferable_in_seq_inference(self) -> None:
        class Visitor:
            def visit(self, node: nodes.Assign | nodes.BinOp | nodes.List) -> Any:
                for child in node.get_children():
                    child.accept(self)

            visit_module = visit
            visit_assign = visit
            visit_binop = visit
            visit_list = visit
            visit_const = visit
            visit_name = visit

            def visit_assignname(self, node: nodes.AssignName) -> None:
                for _ in node.infer():
                    pass

        parsed = extract_node(
            """
        a = []
        x = [a*2, a]*2*2
        """
        )
        parsed.accept(Visitor())

    @staticmethod
    def test_uninferable_exponents() -> None:
        """Attempting to calculate the result is prohibitively expensive."""
        parsed = extract_node("15 ** 20220609")
        assert parsed.inferred() == [Uninferable]

        # Test a pathological case (more realistic: None as naive inference result)
        parsed = extract_node("None ** 2")
        assert parsed.inferred() == [Uninferable]

    @staticmethod
    def test_uninferable_list_multiplication() -> None:
        """Attempting to calculate the result is prohibitively expensive."""
        parsed = extract_node("[0] * 123456789")
        element = parsed.inferred()[0].elts[0]
        assert element.value is Uninferable


def test_named_expr_inference() -> None:
    code = """
    if (a := 2) == 2:
        a #@


    # Test a function call
    def test():
        return 24

    if (a := test()):
        a #@

    # Normal assignments in sequences
    { (a:= 4) } #@
    [ (a:= 5) ] #@

    # Something more complicated
    def test(value=(p := 24)): return p
    [ y:= test()] #@

    # Priority assignment
    (x := 1, 2)
    x #@
    """
    ast_nodes = extract_node(code)
    assert isinstance(ast_nodes, list)
    node = next(ast_nodes[0].infer())
    assert isinstance(node, nodes.Const)
    assert node.value == 2

    node = next(ast_nodes[1].infer())
    assert isinstance(node, nodes.Const)
    assert node.value == 24

    node = next(ast_nodes[2].infer())
    assert isinstance(node, nodes.Set)
    assert isinstance(node.elts[0], nodes.Const)
    assert node.elts[0].value == 4

    node = next(ast_nodes[3].infer())
    assert isinstance(node, nodes.List)
    assert isinstance(node.elts[0], nodes.Const)
    assert node.elts[0].value == 5

    node = next(ast_nodes[4].infer())
    assert isinstance(node, nodes.List)
    assert isinstance(node.elts[0], nodes.Const)
    assert node.elts[0].value == 24

    node = next(ast_nodes[5].infer())
    assert isinstance(node, nodes.Const)
    assert node.value == 1


@pytest.mark.skipif(not PY310_PLUS, reason="Match requires python 3.10")
class TestPatternMatching:
    @staticmethod
    def test_assigned_stmts_match_mapping():
        """Assigned_stmts for MatchMapping not yet implemented.

        Test the result is 'Uninferable' and no exception is raised.
        """
        assign_stmts = extract_node(
            """
        var = {1: "Hello", 2: "World"}
        match var:
            case {**rest}:  #@
                pass
        """
        )
        match_mapping: nodes.MatchMapping = assign_stmts.pattern  # type: ignore[union-attr]
        assert match_mapping.rest
        assigned = next(match_mapping.rest.assigned_stmts())
        assert assigned == Uninferable

    @staticmethod
    def test_assigned_stmts_match_star():
        """Assigned_stmts for MatchStar not yet implemented.

        Test the result is 'Uninferable' and no exception is raised.
        """
        assign_stmts = extract_node(
            """
        var = (0, 1, 2)
        match var:
            case (0, 1, *rest):  #@
                pass
        """
        )
        match_sequence: nodes.MatchSequence = assign_stmts.pattern  # type: ignore[union-attr]
        match_star = match_sequence.patterns[2]
        assert isinstance(match_star, nodes.MatchStar) and match_star.name
        assigned = next(match_star.name.assigned_stmts())
        assert assigned == Uninferable

    @staticmethod
    def test_assigned_stmts_match_as():
        """Assigned_stmts for MatchAs only implemented for the most basic case (y)."""
        assign_stmts = extract_node(
            """
        var = 42
        match var:  #@
            case 2 | x:  #@
                pass
            case (1, 2) as y:  #@
                pass
            case z:  #@
                pass
        """
        )
        subject: nodes.Const = assign_stmts[0].subject  # type: ignore[index,union-attr]
        match_or: nodes.MatchOr = assign_stmts[1].pattern  # type: ignore[index,union-attr]
        match_as_with_pattern: nodes.MatchAs = assign_stmts[2].pattern  # type: ignore[index,union-attr]
        match_as: nodes.MatchAs = assign_stmts[3].pattern  # type: ignore[index,union-attr]

        match_or_1 = match_or.patterns[1]
        assert isinstance(match_or_1, nodes.MatchAs) and match_or_1.name
        assigned_match_or_1 = next(match_or_1.name.assigned_stmts())
        assert assigned_match_or_1 == Uninferable

        assert match_as_with_pattern.name and match_as_with_pattern.pattern
        assigned_match_as_pattern = next(match_as_with_pattern.name.assigned_stmts())
        assert assigned_match_as_pattern == Uninferable

        assert match_as.name
        assigned_match_as = next(match_as.name.assigned_stmts())
        assert assigned_match_as == subject


@pytest.mark.skipif(not PY312_PLUS, reason="Generic typing syntax requires python 3.12")
class TestGenericTypeSyntax:
    @staticmethod
    def test_assigned_stmts_type_var():
        """The result is 'Uninferable' and no exception is raised."""
        assign_stmts = extract_node("type Point[T] = tuple[float, float]")
        type_var: nodes.TypeVar = assign_stmts.type_params[0]
        assigned = next(type_var.name.assigned_stmts())
        # Hack so inference doesn't fail when evaluating __class_getitem__
        # Revert if it's causing issues.
        assert isinstance(assigned, nodes.Const)
        assert assigned.value is None

    @staticmethod
    def test_assigned_stmts_type_var_tuple():
        """The result is 'Uninferable' and no exception is raised."""
        assign_stmts = extract_node("type Alias[*Ts] = tuple[*Ts]")
        type_var_tuple: nodes.TypeVarTuple = assign_stmts.type_params[0]
        assigned = next(type_var_tuple.name.assigned_stmts())
        # Hack so inference doesn't fail when evaluating __class_getitem__
        # Revert if it's causing issues.
        assert isinstance(assigned, nodes.Const)
        assert assigned.value is None

    @staticmethod
    def test_assigned_stmts_param_spec():
        """The result is 'Uninferable' and no exception is raised."""
        assign_stmts = extract_node("type Alias[**P] = Callable[P, int]")
        param_spec: nodes.ParamSpec = assign_stmts.type_params[0]
        assigned = next(param_spec.name.assigned_stmts())
        # Hack so inference doesn't fail when evaluating __class_getitem__
        # Revert if it's causing issues.
        assert isinstance(assigned, nodes.Const)
        assert assigned.value is None
