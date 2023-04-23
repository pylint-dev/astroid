# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import unittest

from astroid import Uninferable, builder, extract_node, nodes
from astroid.exceptions import InferenceError


class InferenceUtil(unittest.TestCase):
    def test_not_exclusive(self) -> None:
        module = builder.parse(
            """
        x = 10
        for x in range(5):
            print (x)

        if x > 0:
            print ('#' * x)
        """,
            __name__,
            __file__,
        )
        xass1 = module.locals["x"][0]
        assert xass1.lineno == 2
        xnames = [n for n in module.nodes_of_class(nodes.Name) if n.name == "x"]
        assert len(xnames) == 3
        assert xnames[1].lineno == 6
        self.assertEqual(nodes.are_exclusive(xass1, xnames[1]), False)
        self.assertEqual(nodes.are_exclusive(xass1, xnames[2]), False)

    def test_not_exclusive_walrus_operator(self) -> None:
        node_if, node_body, node_or_else = extract_node(
            """
        if val := True:  #@
            print(val)  #@
        else:
            print(val)  #@
        """
        )
        node_if: nodes.If
        node_walrus = next(node_if.nodes_of_class(nodes.NamedExpr))

        assert nodes.are_exclusive(node_walrus, node_if) is False
        assert nodes.are_exclusive(node_walrus, node_body) is False
        assert nodes.are_exclusive(node_walrus, node_or_else) is False

        assert nodes.are_exclusive(node_if, node_body) is False
        assert nodes.are_exclusive(node_if, node_or_else) is False
        assert nodes.are_exclusive(node_body, node_or_else) is True

    def test_not_exclusive_walrus_multiple(self) -> None:
        node_if, body_1, body_2, or_else_1, or_else_2 = extract_node(
            """
        if (val := True) or (val_2 := True):  #@
            print(val)  #@
            print(val_2)  #@
        else:
            print(val)  #@
            print(val_2)  #@
        """
        )
        node_if: nodes.If
        walruses = list(node_if.nodes_of_class(nodes.NamedExpr))

        assert nodes.are_exclusive(node_if, walruses[0]) is False
        assert nodes.are_exclusive(node_if, walruses[1]) is False

        assert nodes.are_exclusive(walruses[0], walruses[1]) is False

        assert nodes.are_exclusive(walruses[0], body_1) is False
        assert nodes.are_exclusive(walruses[0], body_2) is False
        assert nodes.are_exclusive(walruses[1], body_1) is False
        assert nodes.are_exclusive(walruses[1], body_2) is False

        assert nodes.are_exclusive(walruses[0], or_else_1) is False
        assert nodes.are_exclusive(walruses[0], or_else_2) is False
        assert nodes.are_exclusive(walruses[1], or_else_1) is False
        assert nodes.are_exclusive(walruses[1], or_else_2) is False

    def test_not_exclusive_walrus_operator_nested(self) -> None:
        node_if, node_body, node_or_else = extract_node(
            """
        if all((last_val := i) % 2 == 0 for i in range(10)): #@
            print(last_val)  #@
        else:
            print(last_val)  #@
        """
        )
        node_if: nodes.If
        node_walrus = next(node_if.nodes_of_class(nodes.NamedExpr))

        assert nodes.are_exclusive(node_walrus, node_if) is False
        assert nodes.are_exclusive(node_walrus, node_body) is False
        assert nodes.are_exclusive(node_walrus, node_or_else) is False

        assert nodes.are_exclusive(node_if, node_body) is False
        assert nodes.are_exclusive(node_if, node_or_else) is False
        assert nodes.are_exclusive(node_body, node_or_else) is True

    def test_if(self) -> None:
        module = builder.parse(
            """
        if 1:
            a = 1
            a = 2
        elif 2:
            a = 12
            a = 13
        else:
            a = 3
            a = 4
        """
        )
        a1 = module.locals["a"][0]
        a2 = module.locals["a"][1]
        a3 = module.locals["a"][2]
        a4 = module.locals["a"][3]
        a5 = module.locals["a"][4]
        a6 = module.locals["a"][5]
        self.assertEqual(nodes.are_exclusive(a1, a2), False)
        self.assertEqual(nodes.are_exclusive(a1, a3), True)
        self.assertEqual(nodes.are_exclusive(a1, a5), True)
        self.assertEqual(nodes.are_exclusive(a3, a5), True)
        self.assertEqual(nodes.are_exclusive(a3, a4), False)
        self.assertEqual(nodes.are_exclusive(a5, a6), False)

    def test_try_except(self) -> None:
        module = builder.parse(
            """
        try:
            def exclusive_func2():
                "docstring"
        except TypeError:
            def exclusive_func2():
                "docstring"
        except:
            def exclusive_func2():
                "docstring"
        else:
            def exclusive_func2():
                "this one redefine the one defined line 42"
        """
        )
        f1 = module.locals["exclusive_func2"][0]
        f2 = module.locals["exclusive_func2"][1]
        f3 = module.locals["exclusive_func2"][2]
        f4 = module.locals["exclusive_func2"][3]
        self.assertEqual(nodes.are_exclusive(f1, f2), True)
        self.assertEqual(nodes.are_exclusive(f1, f3), True)
        self.assertEqual(nodes.are_exclusive(f1, f4), False)
        self.assertEqual(nodes.are_exclusive(f2, f4), True)
        self.assertEqual(nodes.are_exclusive(f3, f4), True)
        self.assertEqual(nodes.are_exclusive(f3, f2), True)

        self.assertEqual(nodes.are_exclusive(f2, f1), True)
        self.assertEqual(nodes.are_exclusive(f4, f1), False)
        self.assertEqual(nodes.are_exclusive(f4, f2), True)

    def test_unpack_infer_uninferable_nodes(self) -> None:
        node = builder.extract_node(
            """
        x = [A] * 1
        f = [x, [A] * 2]
        f
        """
        )
        inferred = next(node.infer())
        unpacked = list(nodes.unpack_infer(inferred))
        self.assertEqual(len(unpacked), 3)
        self.assertTrue(all(elt is Uninferable for elt in unpacked))

    def test_unpack_infer_empty_tuple(self) -> None:
        node = builder.extract_node(
            """
        ()
        """
        )
        inferred = next(node.infer())
        with self.assertRaises(InferenceError):
            list(nodes.unpack_infer(inferred))
