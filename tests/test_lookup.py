# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the astroid variable lookup capabilities."""
import functools
import unittest

from astroid import builder, nodes
from astroid.exceptions import (
    AttributeInferenceError,
    InferenceError,
    NameInferenceError,
)

from . import resources


class LookupTest(resources.SysPathSetup, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.module = resources.build_file("data/module.py", "data.module")
        self.module2 = resources.build_file("data/module2.py", "data.module2")
        self.nonregr = resources.build_file("data/nonregr.py", "data.nonregr")

    def test_limit(self) -> None:
        code = """
            l = [a
                 for a,b in list]

            a = 1
            b = a
            a = None

            def func():
                c = 1
        """
        astroid = builder.parse(code, __name__)
        # a & b
        a = next(astroid.nodes_of_class(nodes.Name))
        self.assertEqual(a.lineno, 2)
        self.assertEqual(len(astroid.lookup("b")[1]), 1)
        self.assertEqual(len(astroid.lookup("a")[1]), 1)
        b = astroid.locals["b"][0]
        stmts = a.lookup("a")[1]
        self.assertEqual(len(stmts), 1)
        self.assertEqual(b.lineno, 6)
        b_infer = b.infer()
        b_value = next(b_infer)
        self.assertEqual(b_value.value, 1)
        # c
        self.assertRaises(StopIteration, functools.partial(next, b_infer))
        func = astroid.locals["func"][0]
        self.assertEqual(len(func.lookup("c")[1]), 1)

    def test_module(self) -> None:
        astroid = builder.parse("pass", __name__)
        # built-in objects
        none = next(astroid.ilookup("None"))
        self.assertIsNone(none.value)
        obj = next(astroid.ilookup("object"))
        self.assertIsInstance(obj, nodes.ClassDef)
        self.assertEqual(obj.name, "object")
        self.assertRaises(
            InferenceError, functools.partial(next, astroid.ilookup("YOAA"))
        )

        # XXX
        self.assertEqual(len(list(self.nonregr.ilookup("enumerate"))), 2)

    def test_class_ancestor_name(self) -> None:
        code = """
            class A:
                pass

            class A(A):
                pass
        """
        astroid = builder.parse(code, __name__)
        cls1 = astroid.locals["A"][0]
        cls2 = astroid.locals["A"][1]
        name = next(cls2.nodes_of_class(nodes.Name))
        self.assertEqual(next(name.infer()), cls1)

    # backport those test to inline code
    def test_method(self) -> None:
        method = self.module["YOUPI"]["method"]
        my_dict = next(method.ilookup("MY_DICT"))
        self.assertTrue(isinstance(my_dict, nodes.Dict), my_dict)
        none = next(method.ilookup("None"))
        self.assertIsNone(none.value)
        self.assertRaises(
            InferenceError, functools.partial(next, method.ilookup("YOAA"))
        )

    def test_function_argument_with_default(self) -> None:
        make_class = self.module2["make_class"]
        base = next(make_class.ilookup("base"))
        self.assertTrue(isinstance(base, nodes.ClassDef), base.__class__)
        self.assertEqual(base.name, "YO")
        self.assertEqual(base.root().name, "data.module")

    def test_class(self) -> None:
        klass = self.module["YOUPI"]
        my_dict = next(klass.ilookup("MY_DICT"))
        self.assertIsInstance(my_dict, nodes.Dict)
        none = next(klass.ilookup("None"))
        self.assertIsNone(none.value)
        obj = next(klass.ilookup("object"))
        self.assertIsInstance(obj, nodes.ClassDef)
        self.assertEqual(obj.name, "object")
        self.assertRaises(
            InferenceError, functools.partial(next, klass.ilookup("YOAA"))
        )

    def test_inner_classes(self) -> None:
        ddd = list(self.nonregr["Ccc"].ilookup("Ddd"))
        self.assertEqual(ddd[0].name, "Ddd")

    def test_loopvar_hiding(self) -> None:
        astroid = builder.parse(
            """
            x = 10
            for x in range(5):
                print (x)

            if x > 0:
                print ('#' * x)
        """,
            __name__,
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"]
        # inside the loop, only one possible assignment
        self.assertEqual(len(xnames[0].lookup("x")[1]), 1)
        # outside the loop, two possible assignments
        self.assertEqual(len(xnames[1].lookup("x")[1]), 2)
        self.assertEqual(len(xnames[2].lookup("x")[1]), 2)

    def test_list_comps(self) -> None:
        astroid = builder.parse(
            """
            print ([ i for i in range(10) ])
            print ([ i for i in range(10) ])
            print ( list( i for i in range(10) ) )
        """,
            __name__,
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "i"]
        self.assertEqual(len(xnames[0].lookup("i")[1]), 1)
        self.assertEqual(xnames[0].lookup("i")[1][0].lineno, 2)
        self.assertEqual(len(xnames[1].lookup("i")[1]), 1)
        self.assertEqual(xnames[1].lookup("i")[1][0].lineno, 3)
        self.assertEqual(len(xnames[2].lookup("i")[1]), 1)
        self.assertEqual(xnames[2].lookup("i")[1][0].lineno, 4)

    def test_list_comp_target(self) -> None:
        """Test the list comprehension target."""
        astroid = builder.parse(
            """
            ten = [ var for var in range(10) ]
            var
        """
        )
        var = astroid.body[1].value
        self.assertRaises(NameInferenceError, var.inferred)

    def test_dict_comps(self) -> None:
        astroid = builder.parse(
            """
            print ({ i: j for i in range(10) for j in range(10) })
            print ({ i: j for i in range(10) for j in range(10) })
        """,
            __name__,
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "i"]
        self.assertEqual(len(xnames[0].lookup("i")[1]), 1)
        self.assertEqual(xnames[0].lookup("i")[1][0].lineno, 2)
        self.assertEqual(len(xnames[1].lookup("i")[1]), 1)
        self.assertEqual(xnames[1].lookup("i")[1][0].lineno, 3)

        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "j"]
        self.assertEqual(len(xnames[0].lookup("i")[1]), 1)
        self.assertEqual(xnames[0].lookup("i")[1][0].lineno, 2)
        self.assertEqual(len(xnames[1].lookup("i")[1]), 1)
        self.assertEqual(xnames[1].lookup("i")[1][0].lineno, 3)

    def test_set_comps(self) -> None:
        astroid = builder.parse(
            """
            print ({ i for i in range(10) })
            print ({ i for i in range(10) })
        """,
            __name__,
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "i"]
        self.assertEqual(len(xnames[0].lookup("i")[1]), 1)
        self.assertEqual(xnames[0].lookup("i")[1][0].lineno, 2)
        self.assertEqual(len(xnames[1].lookup("i")[1]), 1)
        self.assertEqual(xnames[1].lookup("i")[1][0].lineno, 3)

    def test_set_comp_closure(self) -> None:
        astroid = builder.parse(
            """
            ten = { var for var in range(10) }
            var
        """
        )
        var = astroid.body[1].value
        self.assertRaises(NameInferenceError, var.inferred)

    def test_list_comp_nested(self) -> None:
        astroid = builder.parse(
            """
            x = [[i + j for j in range(20)]
                 for i in range(10)]
        """,
            __name__,
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "i"]
        self.assertEqual(len(xnames[0].lookup("i")[1]), 1)
        self.assertEqual(xnames[0].lookup("i")[1][0].lineno, 3)

    def test_dict_comp_nested(self) -> None:
        astroid = builder.parse(
            """
            x = {i: {i: j for j in range(20)}
                 for i in range(10)}
            x3 = [{i + j for j in range(20)}  # Can't do nested sets
                  for i in range(10)]
        """,
            __name__,
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "i"]
        self.assertEqual(len(xnames[0].lookup("i")[1]), 1)
        self.assertEqual(xnames[0].lookup("i")[1][0].lineno, 3)
        self.assertEqual(len(xnames[1].lookup("i")[1]), 1)
        self.assertEqual(xnames[1].lookup("i")[1][0].lineno, 3)

    def test_set_comp_nested(self) -> None:
        astroid = builder.parse(
            """
            x = [{i + j for j in range(20)}  # Can't do nested sets
                 for i in range(10)]
        """,
            __name__,
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "i"]
        self.assertEqual(len(xnames[0].lookup("i")[1]), 1)
        self.assertEqual(xnames[0].lookup("i")[1][0].lineno, 3)

    def test_lambda_nested(self) -> None:
        astroid = builder.parse(
            """
            f = lambda x: (
                    lambda y: x + y)
        """
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"]
        self.assertEqual(len(xnames[0].lookup("x")[1]), 1)
        self.assertEqual(xnames[0].lookup("x")[1][0].lineno, 2)

    def test_function_nested(self) -> None:
        astroid = builder.parse(
            """
            def f1(x):
                def f2(y):
                    return x + y

                return f2
        """
        )
        xnames = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"]
        self.assertEqual(len(xnames[0].lookup("x")[1]), 1)
        self.assertEqual(xnames[0].lookup("x")[1][0].lineno, 2)

    def test_class_variables(self) -> None:
        # Class variables are NOT available within nested scopes.
        astroid = builder.parse(
            """
            class A:
                a = 10

                def f1(self):
                    return a  # a is not defined

                f2 = lambda: a  # a is not defined

                b = [a for _ in range(10)]  # a is not defined

                class _Inner:
                    inner_a = a + 1
            """
        )
        names = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "a"]
        self.assertEqual(len(names), 4)
        for name in names:
            self.assertRaises(NameInferenceError, name.inferred)

    def test_class_in_function(self) -> None:
        # Function variables are available within classes, including methods
        astroid = builder.parse(
            """
            def f():
                x = 10
                class A:
                    a = x

                    def f1(self):
                        return x

                    f2 = lambda: x

                    b = [x for _ in range(10)]

                    class _Inner:
                        inner_a = x + 1
        """
        )
        names = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"]
        self.assertEqual(len(names), 5)
        for name in names:
            self.assertEqual(len(name.lookup("x")[1]), 1, repr(name))
            self.assertEqual(name.lookup("x")[1][0].lineno, 3, repr(name))

    def test_generator_attributes(self) -> None:
        tree = builder.parse(
            """
            def count():
                "test"
                yield 0

            iterer = count()
            num = iterer.next()
        """
        )
        next_node = tree.body[2].value.func
        gener = next_node.expr.inferred()[0]
        self.assertIsInstance(gener.getattr("__next__")[0], nodes.FunctionDef)
        self.assertIsInstance(gener.getattr("send")[0], nodes.FunctionDef)
        self.assertIsInstance(gener.getattr("throw")[0], nodes.FunctionDef)
        self.assertIsInstance(gener.getattr("close")[0], nodes.FunctionDef)

    def test_explicit___name__(self) -> None:
        code = """
            class Pouet:
                __name__ = "pouet"
            p1 = Pouet()

            class PouetPouet(Pouet): pass
            p2 = Pouet()

            class NoName: pass
            p3 = NoName()
        """
        astroid = builder.parse(code, __name__)
        p1 = next(astroid["p1"].infer())
        self.assertTrue(p1.getattr("__name__"))
        p2 = next(astroid["p2"].infer())
        self.assertTrue(p2.getattr("__name__"))
        self.assertTrue(astroid["NoName"].getattr("__name__"))
        p3 = next(astroid["p3"].infer())
        self.assertRaises(AttributeInferenceError, p3.getattr, "__name__")

    def test_function_module_special(self) -> None:
        astroid = builder.parse(
            '''
        def initialize(linter):
            """initialize linter with checkers in this package """
            package_load(linter, __path__[0])
        ''',
            "data.__init__",
        )
        path = next(
            n for n in astroid.nodes_of_class(nodes.Name) if n.name == "__path__"
        )
        self.assertEqual(len(path.lookup("__path__")[1]), 1)

    def test_builtin_lookup(self) -> None:
        self.assertEqual(nodes.builtin_lookup("__dict__")[1], ())
        intstmts = nodes.builtin_lookup("int")[1]
        self.assertEqual(len(intstmts), 1)
        self.assertIsInstance(intstmts[0], nodes.ClassDef)
        self.assertEqual(intstmts[0].name, "int")
        self.assertIs(intstmts[0], nodes.const_factory(1)._proxied)

    def test_decorator_arguments_lookup(self) -> None:
        code = """
            def decorator(value):
                def wrapper(function):
                    return function
                return wrapper

            class foo:
                member = 10  #@

                @decorator(member) #This will cause pylint to complain
                def test(self):
                    pass
        """

        node = builder.extract_node(code, __name__)
        assert isinstance(node, nodes.Assign)
        member = node.targets[0]
        it = member.infer()
        obj = next(it)
        self.assertIsInstance(obj, nodes.Const)
        self.assertEqual(obj.value, 10)
        self.assertRaises(StopIteration, functools.partial(next, it))

    def test_inner_decorator_member_lookup(self) -> None:
        code = """
            class FileA:
                def decorator(bla):
                    return bla

                @__(decorator)
                def funcA():
                    return 4
        """
        decname = builder.extract_node(code, __name__)
        it = decname.infer()
        obj = next(it)
        self.assertIsInstance(obj, nodes.FunctionDef)
        self.assertRaises(StopIteration, functools.partial(next, it))

    def test_static_method_lookup(self) -> None:
        code = """
            class FileA:
                @staticmethod
                def funcA():
                    return 4


            class Test:
                FileA = [1,2,3]

                def __init__(self):
                    print (FileA.funcA())
        """
        astroid = builder.parse(code, __name__)
        it = astroid["Test"]["__init__"].ilookup("FileA")
        obj = next(it)
        self.assertIsInstance(obj, nodes.ClassDef)
        self.assertRaises(StopIteration, functools.partial(next, it))

    def test_global_delete(self) -> None:
        code = """
            def run2():
                f = Frobble()

            class Frobble:
                pass
            Frobble.mumble = True

            del Frobble

            def run1():
                f = Frobble()
        """
        astroid = builder.parse(code, __name__)
        stmts = astroid["run2"].lookup("Frobbel")[1]
        self.assertEqual(len(stmts), 0)
        stmts = astroid["run1"].lookup("Frobbel")[1]
        self.assertEqual(len(stmts), 0)


class LookupControlFlowTest(unittest.TestCase):
    """Tests for lookup capabilities and control flow."""

    def test_consecutive_assign(self) -> None:
        """When multiple assignment statements are in the same block, only the last one
        is returned.
        """
        code = """
            x = 10
            x = 100
            print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 3)

    def test_assign_after_use(self) -> None:
        """An assignment statement appearing after the variable is not returned."""
        code = """
            print(x)
            x = 10
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 0)

    def test_del_removes_prior(self) -> None:
        """Delete statement removes any prior assignments."""
        code = """
            x = 10
            del x
            print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 0)

    def test_del_no_effect_after(self) -> None:
        """Delete statement doesn't remove future assignments."""
        code = """
            x = 10
            del x
            x = 100
            print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 4)

    def test_if_assign(self) -> None:
        """Assignment in if statement is added to lookup results, but does not replace
        prior assignments.
        """
        code = """
            def f(b):
                x = 10
                if b:
                    x = 100
                print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 2)
        self.assertCountEqual([stmt.lineno for stmt in stmts], [3, 5])

    def test_if_assigns_same_branch(self) -> None:
        """When if branch has multiple assignment statements, only the last one
        is added.
        """
        code = """
            def f(b):
                x = 10
                if b:
                    x = 100
                    x = 1000
                print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 2)
        self.assertCountEqual([stmt.lineno for stmt in stmts], [3, 6])

    def test_if_assigns_different_branch(self) -> None:
        """When different branches have assignment statements, the last one
        in each branch is added.
        """
        code = """
            def f(b):
                x = 10
                if b == 1:
                    x = 100
                    x = 1000
                elif b == 2:
                    x = 3
                elif b == 3:
                    x = 4
                print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 4)
        self.assertCountEqual([stmt.lineno for stmt in stmts], [3, 6, 8, 10])

    def test_assign_exclusive(self) -> None:
        """When the variable appears inside a branch of an if statement,
        no assignment statements from other branches are returned.
        """
        code = """
            def f(b):
                x = 10
                if b == 1:
                    x = 100
                    x = 1000
                elif b == 2:
                    x = 3
                elif b == 3:
                    x = 4
                else:
                    print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 3)

    def test_assign_not_exclusive(self) -> None:
        """When the variable appears inside a branch of an if statement,
        only the last assignment statement in the same branch is returned.
        """
        code = """
            def f(b):
                x = 10
                if b == 1:
                    x = 100
                    x = 1000
                elif b == 2:
                    x = 3
                elif b == 3:
                    x = 4
                    print(x)
                else:
                    x = 5
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 10)

    def test_if_else(self) -> None:
        """When an assignment statement appears in both an if and else branch, both
        are added.

        This does NOT replace an assignment statement appearing before the
        if statement. (See issue #213)
        """
        code = """
            def f(b):
                x = 10
                if b:
                    x = 100
                else:
                    x = 1000
                print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 3)
        self.assertCountEqual([stmt.lineno for stmt in stmts], [3, 5, 7])

    def test_if_variable_in_condition_1(self) -> None:
        """Test lookup works correctly when a variable appears in an if condition."""
        code = """
            x = 10
            if x > 10:
                print('a')
            elif x > 0:
                print('b')
        """
        astroid = builder.parse(code)
        x_name1, x_name2 = (
            n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"
        )

        _, stmts1 = x_name1.lookup("x")
        self.assertEqual(len(stmts1), 1)
        self.assertEqual(stmts1[0].lineno, 2)

        _, stmts2 = x_name2.lookup("x")
        self.assertEqual(len(stmts2), 1)
        self.assertEqual(stmts2[0].lineno, 2)

    def test_if_variable_in_condition_2(self) -> None:
        """Test lookup works correctly when a variable appears in an if condition,
        and the variable is reassigned in each branch.

        This is based on pylint-dev/pylint issue #3711.
        """
        code = """
            x = 10
            if x > 10:
                x = 100
            elif x > 0:
                x = 200
            elif x > -10:
                x = 300
            else:
                x = 400
        """
        astroid = builder.parse(code)
        x_names = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"]

        # All lookups should refer only to the initial x = 10.
        for x_name in x_names:
            _, stmts = x_name.lookup("x")
            self.assertEqual(len(stmts), 1)
            self.assertEqual(stmts[0].lineno, 2)

    def test_del_not_exclusive(self) -> None:
        """A delete statement in an if statement branch removes all previous
        assignment statements when the delete statement is not exclusive with
        the variable (e.g., when the variable is used below the if statement).
        """
        code = """
            def f(b):
                x = 10
                if b == 1:
                    x = 100
                elif b == 2:
                    del x
                elif b == 3:
                    x = 4  # Only this assignment statement is returned
                print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 9)

    def test_del_exclusive(self) -> None:
        """A delete statement in an if statement branch that is exclusive with the
        variable does not remove previous assignment statements.
        """
        code = """
            def f(b):
                x = 10
                if b == 1:
                    x = 100
                elif b == 2:
                    del x
                else:
                    print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 3)

    def test_assign_after_param(self) -> None:
        """When an assignment statement overwrites a function parameter, only the
        assignment is returned, even when the variable and assignment do not have
        the same parent.
        """
        code = """
            def f1(x):
                x = 100
                print(x)

            def f2(x):
                x = 100
                if True:
                    print(x)
        """
        astroid = builder.parse(code)
        x_name1, x_name2 = (
            n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"
        )
        _, stmts1 = x_name1.lookup("x")
        self.assertEqual(len(stmts1), 1)
        self.assertEqual(stmts1[0].lineno, 3)

        _, stmts2 = x_name2.lookup("x")
        self.assertEqual(len(stmts2), 1)
        self.assertEqual(stmts2[0].lineno, 7)

    def test_assign_after_kwonly_param(self) -> None:
        """When an assignment statement overwrites a function keyword-only parameter,
        only the assignment is returned, even when the variable and assignment do
        not have the same parent.
        """
        code = """
            def f1(*, x):
                x = 100
                print(x)

            def f2(*, x):
                x = 100
                if True:
                    print(x)
        """
        astroid = builder.parse(code)
        x_name1, x_name2 = (
            n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"
        )
        _, stmts1 = x_name1.lookup("x")
        self.assertEqual(len(stmts1), 1)
        self.assertEqual(stmts1[0].lineno, 3)

        _, stmts2 = x_name2.lookup("x")
        self.assertEqual(len(stmts2), 1)
        self.assertEqual(stmts2[0].lineno, 7)

    def test_assign_after_posonly_param(self):
        """When an assignment statement overwrites a function positional-only parameter,
        only the assignment is returned, even when the variable and assignment do
        not have the same parent.
        """
        code = """
            def f1(x, /):
                x = 100
                print(x)

            def f2(x, /):
                x = 100
                if True:
                    print(x)
        """
        astroid = builder.parse(code)
        x_name1, x_name2 = (
            n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x"
        )
        _, stmts1 = x_name1.lookup("x")
        self.assertEqual(len(stmts1), 1)
        self.assertEqual(stmts1[0].lineno, 3)

        _, stmts2 = x_name2.lookup("x")
        self.assertEqual(len(stmts2), 1)
        self.assertEqual(stmts2[0].lineno, 7)

    def test_assign_after_args_param(self) -> None:
        """When an assignment statement overwrites a function parameter, only the
        assignment is returned.
        """
        code = """
            def f(*args, **kwargs):
                args = [100]
                kwargs = {}
                if True:
                    print(args, kwargs)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "args")
        _, stmts1 = x_name.lookup("args")
        self.assertEqual(len(stmts1), 1)
        self.assertEqual(stmts1[0].lineno, 3)

        x_name = next(
            n for n in astroid.nodes_of_class(nodes.Name) if n.name == "kwargs"
        )
        _, stmts2 = x_name.lookup("kwargs")
        self.assertEqual(len(stmts2), 1)
        self.assertEqual(stmts2[0].lineno, 4)

    def test_except_var_in_block(self) -> None:
        """When the variable bound to an exception in an except clause, it is returned
        when that variable is used inside the except block.
        """
        code = """
            try:
                1 / 0
            except ZeroDivisionError as e:
                print(e)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "e")
        _, stmts = x_name.lookup("e")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 4)

    def test_except_var_in_block_overwrites(self) -> None:
        """When the variable bound to an exception in an except clause, it is returned
        when that variable is used inside the except block, and replaces any previous
        assignments.
        """
        code = """
            e = 0
            try:
                1 / 0
            except ZeroDivisionError as e:
                print(e)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "e")
        _, stmts = x_name.lookup("e")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 5)

    def test_except_var_in_multiple_blocks(self) -> None:
        """When multiple variables with the same name are bound to an exception
        in an except clause, and the variable is used inside the except block,
        only the assignment from the corresponding except clause is returned.
        """
        code = """
            e = 0
            try:
                1 / 0
            except ZeroDivisionError as e:
                print(e)
            except NameError as e:
                print(e)
        """
        astroid = builder.parse(code)
        x_names = [n for n in astroid.nodes_of_class(nodes.Name) if n.name == "e"]

        _, stmts1 = x_names[0].lookup("e")
        self.assertEqual(len(stmts1), 1)
        self.assertEqual(stmts1[0].lineno, 5)

        _, stmts2 = x_names[1].lookup("e")
        self.assertEqual(len(stmts2), 1)
        self.assertEqual(stmts2[0].lineno, 7)

    def test_except_var_after_block_single(self) -> None:
        """When the variable bound to an exception in an except clause, it is NOT returned
        when that variable is used after the except block.
        """
        code = """
            try:
                1 / 0
            except NameError as e:
                pass
            print(e)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "e")
        _, stmts = x_name.lookup("e")
        self.assertEqual(len(stmts), 0)

    def test_except_var_after_block_multiple(self) -> None:
        """When the variable bound to an exception in multiple except clauses, it is NOT returned
        when that variable is used after the except blocks.
        """
        code = """
            try:
                1 / 0
            except NameError as e:
                pass
            except ZeroDivisionError as e:
                pass
            print(e)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "e")
        _, stmts = x_name.lookup("e")
        self.assertEqual(len(stmts), 0)

    def test_except_assign_in_block(self) -> None:
        """When a variable is assigned in an except block, it is returned
        when that variable is used in the except block.
        """
        code = """
            try:
                1 / 0
            except ZeroDivisionError as e:
                x = 10
                print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 5)

    def test_except_assign_in_block_multiple(self) -> None:
        """When a variable is assigned in multiple except blocks, and the variable is
        used in one of the blocks, only the assignments in that block are returned.
        """
        code = """
            try:
                1 / 0
            except ZeroDivisionError:
                x = 10
            except NameError:
                x = 100
                print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 7)

    def test_except_assign_after_block(self) -> None:
        """When a variable is assigned in an except clause, it is returned
        when that variable is used after the except block.
        """
        code = """
            try:
                1 / 0
            except ZeroDivisionError:
                x = 10
            except NameError:
                x = 100
            print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 2)
        self.assertCountEqual([stmt.lineno for stmt in stmts], [5, 7])

    def test_except_assign_after_block_overwritten(self) -> None:
        """When a variable is assigned in an except clause, it is not returned
        when it is reassigned and used after the except block.
        """
        code = """
            try:
                1 / 0
            except ZeroDivisionError:
                x = 10
            except NameError:
                x = 100
            x = 1000
            print(x)
        """
        astroid = builder.parse(code)
        x_name = next(n for n in astroid.nodes_of_class(nodes.Name) if n.name == "x")
        _, stmts = x_name.lookup("x")
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].lineno, 8)
