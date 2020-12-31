# Copyright (c) 2020 rioj7

from textwrap import dedent
import unittest

import astroid

class TurtleTest(unittest.TestCase):

    def test_pencolor(self):
        node = dedent("""
            import turtle
            turtle.pencolor
            """)
        inferred = next(astroid.extract_node(node).infer())
        self.assertIsInstance(inferred, astroid.FunctionDef)
        self.assertEqual(inferred.name, 'pencolor')

    def test_Turtle(self):
        node = dedent("""
            import turtle
            turtle.Turtle()
            """)
        inferred = next(astroid.extract_node(node).infer())
        self.assertIsInstance(inferred, astroid.Instance)

if __name__ == "__main__":
    unittest.main()
