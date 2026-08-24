# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Unit Tests for the builtins brain module."""

import unittest

import pytest

from astroid import bases, nodes, objects, util
from astroid.builder import _extract_single_node, extract_node


class BuiltinsTest(unittest.TestCase):
    def test_infer_property(self):
        property_assign = _extract_single_node("""
        class Something:
            def getter():
                return 5
            asd = property(getter) #@
        """)
        inferred_property = next(iter(property_assign.value.infer()))
        self.assertTrue(isinstance(inferred_property, objects.Property))
        class_parent = property_assign.scope()
        self.assertIsInstance(class_parent, nodes.ClassDef)
        self.assertFalse(
            any(
                isinstance(def_, objects.Property)
                for def_list in class_parent.locals.values()
                for def_ in def_list
            )
        )
        self.assertTrue(hasattr(inferred_property, "args"))


class TestStringNodes:
    @pytest.mark.parametrize(
        "format_string",
        [
            pytest.param(
                """"My name is {}, I'm {}".format("Daniel", 12)""", id="empty-indexes"
            ),
            pytest.param(
                """"My name is {0}, I'm {1}".format("Daniel", 12)""",
                id="numbered-indexes",
            ),
            pytest.param(
                """"My name is {fname}, I'm {age}".format(fname = "Daniel", age = 12)""",
                id="named-indexes",
            ),
            pytest.param(
                """
        name = "Daniel"
        age = 12
        "My name is {0}, I'm {1}".format(name, age)
        """,
                id="numbered-indexes-from-positional",
            ),
            pytest.param(
                """
        name = "Daniel"
        age = 12
        "My name is {fname}, I'm {age}".format(fname = name, age = age)
        """,
                id="named-indexes-from-keyword",
            ),
            pytest.param(
                """
        name = "Daniel"
        age = 12
        "My name is {0}, I'm {age}".format(name, age = age)
        """,
                id="mixed-indexes-from-mixed",
            ),
            pytest.param(
                """
        string = "My name is {}, I'm {}"
        string.format("Daniel", 12)
        """,
                id="empty-indexes-on-variable",
            ),
        ],
    )
    def test_string_format(self, format_string: str) -> None:
        node: nodes.Call = _extract_single_node(format_string)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "My name is Daniel, I'm 12"

    @pytest.mark.parametrize(
        "format_string",
        [
            """
            from missing import Unknown
            name = Unknown
            age = 12
            "My name is {fname}, I'm {age}".format(fname = name, age = age)
            """,
            """
            from missing import Unknown
            age = 12
            "My name is {fname}, I'm {age}".format(fname = Unknown, age = age)
            """,
            """
            from missing import Unknown
            "My name is {}, I'm {}".format(Unknown, 12)
            """,
            """"I am {}".format()""",
            """
            "My name is {fname}, I'm {age}".format(fsname = "Daniel", age = 12)
            """,
            """
            "My unicode character is {:c}".format(None)
            """,
            """
            "My hex format is {:4x}".format('1')
            """,
            """
            daniel_age = 12
            "My name is {0.name}".format(daniel_age)
            """,
            pytest.param(""""{:>2000000000}".format("x")""", id="oversized-width"),
            pytest.param(""""{:.2000000000f}".format(1.0)""", id="oversized-precision"),
            pytest.param(
                """"{:>{}}".format("x", 2000000000)""", id="oversized-nested-width"
            ),
        ],
    )
    def test_string_format_uninferable(self, format_string: str) -> None:
        node: nodes.Call = _extract_single_node(format_string)
        inferred = next(node.infer())
        assert inferred is util.Uninferable

    def test_string_format_with_specs(self) -> None:
        node: nodes.Call = _extract_single_node(
            """"My name is {}, I'm {:.2f}".format("Daniel", 12)"""
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "My name is Daniel, I'm 12.00"

    def test_string_format_in_dataclass_pylint8109(self) -> None:
        """https://github.com/pylint-dev/pylint/issues/8109"""
        function_def = extract_node("""
from dataclasses import dataclass

@dataclass
class Number:
    amount: int | float
    round: int = 2

    def __str__(self): #@
        number_format = "{:,.%sf}" % self.round
        return number_format.format(self.amount).rstrip("0").rstrip(".")
""")
        inferit = function_def.infer_call_result(function_def, context=None)
        assert [a.name for a in inferit] == [util.Uninferable]


class TestShadowedBuiltins:
    """A name shadowing a builtin must not be inferred as that builtin.

    The transforms registered by ``register_builtin_transform`` are selected on
    the identifier alone, so every one of them used to fire on a shadowing name.
    """

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param(
                """
                def bool(x):
                    return "shadowed"
                bool(1) #@
                """,
                id="bool",
            ),
            pytest.param(
                """
                def int(x):
                    return "shadowed"
                int("1") #@
                """,
                id="int",
            ),
            pytest.param(
                """
                def isinstance(obj, cls):
                    return "shadowed"
                isinstance(1, int) #@
                """,
                id="isinstance",
            ),
            pytest.param(
                """
                def len(x):
                    return "shadowed"
                len([1, 2, 3]) #@
                """,
                id="len",
            ),
            pytest.param(
                """
                def list(x):
                    return "shadowed"
                list("ab") #@
                """,
                id="list",
            ),
            pytest.param(
                """
                def str(x):
                    return "shadowed"
                str(42) #@
                """,
                id="str",
            ),
            pytest.param(
                """
                def type(x):
                    return "shadowed"
                type(1) #@
                """,
                id="type",
            ),
            pytest.param(
                """
                len = lambda x: "shadowed"
                len([1, 2, 3]) #@
                """,
                id="assignment-instead-of-def",
            ),
            pytest.param(
                """
                class dict:
                    @staticmethod
                    def fromkeys(keys):
                        return "shadowed"
                dict.fromkeys("ab") #@
                """,
                id="dict.fromkeys",
            ),
        ],
    )
    def test_shadowed_builtin_call(self, code: str) -> None:
        node: nodes.Call = _extract_single_node(code)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "shadowed"

    def test_shadowed_by_a_parameter_pylint10994(self) -> None:
        """https://github.com/pylint-dev/pylint/issues/10994"""
        node: nodes.Call = _extract_single_node("""
        def convert_type(x, type):
            return type(x)

        convert_type(12.34, str) #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.pytype() == "builtins.str"

    @pytest.mark.parametrize(
        "code,expected",
        [
            pytest.param("bool(0) #@", nodes.Const, id="bool"),
            pytest.param("callable(len) #@", nodes.Const, id="callable"),
            pytest.param("dict(a=1) #@", nodes.Dict, id="dict"),
            pytest.param("dict.fromkeys(['a']) #@", nodes.Dict, id="dict.fromkeys"),
            pytest.param("frozenset([1]) #@", objects.FrozenSet, id="frozenset"),
            pytest.param("int('42') #@", nodes.Const, id="int"),
            pytest.param("isinstance(1, int) #@", nodes.Const, id="isinstance"),
            pytest.param("issubclass(bool, int) #@", nodes.Const, id="issubclass"),
            pytest.param("len([1, 2, 3]) #@", nodes.Const, id="len"),
            pytest.param("list((1, 2)) #@", nodes.List, id="list"),
            pytest.param("set([1]) #@", nodes.Set, id="set"),
            pytest.param("slice(1, 2) #@", nodes.Slice, id="slice"),
            pytest.param("str(42) #@", nodes.Const, id="str"),
            pytest.param("tuple([1, 2]) #@", nodes.Tuple, id="tuple"),
            pytest.param("type(1) #@", nodes.ClassDef, id="type"),
            pytest.param(
                'getattr("apple", "upper") #@', bases.BoundMethod, id="getattr"
            ),
            pytest.param('hasattr("apple", "upper") #@', nodes.Const, id="hasattr"),
            pytest.param(
                "property(lambda self: 1) #@", objects.Property, id="property"
            ),
            pytest.param(
                """
                class Animal:
                    def speak(self):
                        return "generic"

                class Cat(Animal):
                    def speak(self):
                        super() #@
                """,
                objects.Super,
                id="super",
            ),
            pytest.param(
                """
                from builtins import str
                str(42) #@
                """,
                nodes.Const,
                id="from-builtins-import",
            ),
            pytest.param(
                """
                from builtins import *
                str(42) #@
                """,
                nodes.Const,
                id="from-builtins-star-import",
            ),
            pytest.param(
                """
                class Fruit:
                    size = len("apple")  #@
                    def len(self):
                        return 0
                """,
                nodes.Const,
                id="class-body-before-method-shadow",
            ),
            pytest.param(
                """
                len([1, 2, 3])  #@
                def len(x):
                    return "shadowed"
                """,
                nodes.Const,
                id="module-use-before-def",
            ),
        ],
    )
    def test_unshadowed_builtin_call(self, code: str, expected: type) -> None:
        """The brains must keep firing when the builtin is not shadowed."""
        node = _extract_single_node(code)
        if isinstance(node, nodes.Assign):
            node = node.value
        assert isinstance(node, nodes.Call)
        inferred = next(node.infer())
        assert isinstance(inferred, expected)

    def test_default_arg_uses_enclosing_builtin(self) -> None:
        """Defaults are evaluated in the enclosing scope, not the function body."""
        func: nodes.FunctionDef = extract_node("""
            def h(x, len=len([1, 2, 3])):
                return x
            """)
        call = next(d for d in func.args.defaults if isinstance(d, nodes.Call))
        inferred = next(call.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 3

    def test_kwonly_default_uses_enclosing_builtin(self) -> None:
        func: nodes.FunctionDef = extract_node("""
            def h(x, *, len=len([1, 2, 3])):
                return x
            """)
        call = next(
            d for d in (func.args.kw_defaults or ()) if isinstance(d, nodes.Call)
        )
        inferred = next(call.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 3

    @pytest.mark.parametrize(
        "default",
        [
            pytest.param("[len(y) for y in ([1, 2, 3],)]", id="comprehension"),
            pytest.param("lambda: len([1, 2, 3])", id="lambda"),
        ],
    )
    def test_nested_scope_in_default_uses_enclosing_builtin(self, default: str) -> None:
        """A comprehension or lambda in a default is still in the enclosing scope."""
        func: nodes.FunctionDef = extract_node(f"""
            def h(x, len={default}):
                return x
            """)
        call = next(func.args.defaults[0].nodes_of_class(nodes.Call))
        inferred = next(call.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 3

    def test_shadowing_in_another_scope_is_ignored(self) -> None:
        node: nodes.Call = _extract_single_node("""
        def takes_a_len(len):
            return len

        len([1, 2, 3]) #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 3

    def test_builtins_import_under_another_builtin_name(self) -> None:
        """``str`` here is really ``builtins.int``, so it must not infer as ``str``.

        ``lookup()`` already guarantees the binding is called ``str``; what is
        left to check is *what* was imported under that name.
        """
        node: nodes.Call = _extract_single_node("""
        from builtins import int as str
        str(42) #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.pytype() == "builtins.int"

    def test_annotation_uses_enclosing_builtin(self) -> None:
        """Annotations are evaluated in the enclosing scope, like defaults."""
        func: nodes.FunctionDef = extract_node("""
            def h(x: str("apple") = 1, str=None):
                return x
            """)
        inferred = next(func.args.annotations[0].infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "apple"

    @pytest.mark.parametrize(
        "signature",
        [
            pytest.param('*args: str("apple"), str=None', id="vararg"),
            pytest.param('str=None, **kwargs: str("apple")', id="kwarg"),
            pytest.param('x: str("apple") = 1, /, *, str=None', id="posonly"),
            pytest.param('*, x: str("apple") = 1, str=None', id="kwonly"),
        ],
    )
    def test_every_annotation_uses_enclosing_builtin(self, signature: str) -> None:
        func: nodes.FunctionDef = extract_node(f"""
            def h({signature}):
                return 1
            """)
        call = next(func.args.nodes_of_class(nodes.Call))
        inferred = next(call.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "apple"

    def test_return_annotation_uses_enclosing_builtin(self) -> None:
        func: nodes.FunctionDef = extract_node("""
            def h(x, str=None) -> str("apple"):
                return x
            """)
        inferred = next(func.returns.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "apple"
