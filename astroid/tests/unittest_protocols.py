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

import unittest

from astroid import YES
from astroid.test_utils import extract_node, require_version
from astroid import InferenceError
from astroid.node_classes import AssName, Const, Name, Starred


class ProtocolTests(unittest.TestCase):

    def assertConstNodesEqual(self, nodes_list_expected, nodes_list_got):
        self.assertEqual(len(nodes_list_expected), len(nodes_list_got))
        for node in nodes_list_got:
            self.assertIsInstance(node, Const)
        for node, expected_value in zip(nodes_list_got, nodes_list_expected):
            self.assertEqual(expected_value, node.value)

    def assertNameNodesEqual(self, nodes_list_expected, nodes_list_got):
        self.assertEqual(len(nodes_list_expected), len(nodes_list_got))
        for node in nodes_list_got:
            self.assertIsInstance(node, Name)
        for node, expected_name in zip(nodes_list_got, nodes_list_expected):
            self.assertEqual(expected_name, node.name)

    def test_assigned_stmts_simple_for(self):
        assign_stmts = extract_node("""
        for a in (1, 2, 3):  #@
          pass

        for b in range(3): #@
          pass
        """)

        for1_assnode = next(assign_stmts[0].nodes_of_class(AssName))
        assigned = list(for1_assnode.assigned_stmts())
        self.assertConstNodesEqual([1, 2, 3], assigned)

        for2_assnode = next(assign_stmts[1].nodes_of_class(AssName))
        self.assertRaises(InferenceError,
                          list, for2_assnode.assigned_stmts())

    @require_version(minver='3.0')
    def test_assigned_stmts_starred_for(self):
        assign_stmts = extract_node("""
        for *a, b in ((1, 2, 3), (4, 5, 6, 7)): #@
            pass
        """)

        for1_starred = next(assign_stmts.nodes_of_class(Starred))
        assigned = list(for1_starred.assigned_stmts())
        self.assertEqual(assigned, [])

    def _get_starred_stmts(self, code, expected):
        assign_stmt = extract_node("{} #@".format(code))
        starred = next(assign_stmt.nodes_of_class(Starred))
        return list(starred.assigned_stmts())

    def _helper_starred_expected_const(self, code, expected):
        stmts = self._get_starred_stmts(code, expected)
        self.assertConstNodesEqual(expected, stmts)

    def _helper_starred_expected(self, code, expected):
        stmts = self._get_starred_stmts(code, expected)
        self.assertEqual(expected, stmts)

    def _helper_starred_inference_error(self, code):
        assign_stmt = extract_node("{} #@".format(code))
        starred = next(assign_stmt.nodes_of_class(Starred))
        self.assertRaises(InferenceError, list, starred.assigned_stmts())

    @require_version(minver='3.0')
    def test_assigned_stmts_starred_assnames(self):
        self._helper_starred_expected_const(
            "a, *b = (1, 2, 3, 4) #@", [2, 3, 4])
        self._helper_starred_expected_const(
            "*a, b = (1, 2, 3) #@", [1, 2])
        self._helper_starred_expected_const(
            "a, *b, c = (1, 2, 3, 4, 5) #@",
            [2, 3, 4])
        self._helper_starred_expected_const(
            "a, *b = (1, 2) #@", [2])
        self._helper_starred_expected_const(
            "*b, a = (1, 2) #@", [1])
        self._helper_starred_expected_const(
            "[*b] = (1, 2) #@", [1, 2])

    @require_version(minver='3.0')
    def test_assigned_stmts_starred_yes(self):
        # Not something iterable and known
        self._helper_starred_expected("a, *b = range(3) #@", [YES])
        # Not something inferrable
        self._helper_starred_expected("a, *b = balou() #@", [YES])
        # In function, unknown.
        self._helper_starred_expected("""
        def test(arg):
            head, *tail = arg #@""", [YES])
        # These cases aren't worth supporting.
        self._helper_starred_expected(
            "a, (*b, c), d = (1, (2, 3, 4), 5) #@", [])

    @require_version(minver='3.0')
    def test_assign_stmts_starred_fails(self):
        # Too many starred
        self._helper_starred_inference_error("a, *b, *c = (1, 2, 3) #@")
        # Too many lhs values
        self._helper_starred_inference_error("a, *b, c = (1, 2) #@")
        # Not in Assign or For
        self._helper_starred_inference_error("[*b for b in (1, 2, 3)] #@")
        # This could be solved properly, but it complicates needlessly the
        # code for assigned_stmts, without oferring real benefit.
        self._helper_starred_inference_error(
            "(*a, b), (c, *d) = (1, 2, 3), (4, 5, 6) #@")

    def test_assigned_stmts_assignments(self):
        assign_stmts = extract_node("""
        c = a #@

        d, e = b, c #@
        """)

        simple_assnode = next(assign_stmts[0].nodes_of_class(AssName))
        assigned = list(simple_assnode.assigned_stmts())
        self.assertNameNodesEqual(['a'], assigned)

        assnames = assign_stmts[1].nodes_of_class(AssName)
        simple_mul_assnode_1 = next(assnames)
        assigned = list(simple_mul_assnode_1.assigned_stmts())
        self.assertNameNodesEqual(['b'], assigned)
        simple_mul_assnode_2 = next(assnames)
        assigned = list(simple_mul_assnode_2.assigned_stmts())
        self.assertNameNodesEqual(['c'], assigned)


if __name__ == '__main__':
    unittest.main()
