import unittest
from textwrap import dedent

from astroid import extract_node
from astroid import nodes

class TestFunctionTypeComments(unittest.TestCase):

    def check_annotations(self, code, args=(), returns=None, vararg=None, kwarg=None, lines=()):
        func = extract_node(dedent(code))
        found_lines = []

        def check_name(node, value):
            if value:
                self.assertIsInstance(node, nodes.Name)
                self.assertEqual(node.name, value)
                found_lines.append(node.lineno)
            else:
                self.assertIsNone(node)

        # Check annotations
        annotations = func.args.annotations
        self.assertEqual(len(annotations), len(args))
        for i, arg in enumerate(args):
            check_name(annotations[i], arg)
        check_name(func.args.varargannotation, vararg)
        check_name(func.args.kwargannotation, kwarg)

        # Check returns
        check_name(func.returns, returns)

        # Check lines
        self.assertEquals(list(lines), found_lines)

    def test_unannotated(self):
        self.check_annotations("""
        def test(a, b):  #@
            return str(a)
        """, [None, None], None)

    def test_return(self):
        self.check_annotations("""
        def test():  #@
            # type: () -> str
            return str(a)
        """, [], 'str', lines=[3])

    def test_ellipsis(self):
        self.check_annotations("""
        def test(a, b):  #@
            # type: (...) -> str
            return str(a)
        """, [None, None], 'str', lines=[3])

    def test_simple_func(self):
        self.check_annotations("""
        def test(a, b):  #@
            # type: (int, str) -> str
            return str(a)
        """, ['int', 'str'], 'str', lines=[3, 3, 3])

    def test_simple_func_same_line(self):
        self.check_annotations("""
        def test(a, b):  # type: (int, str) -> str #@
            return str(a)
        """, ['int', 'str'], 'str', lines=[2, 2, 2])

    def test_split_lines(self):
        self.check_annotations("""
        def test( #@
            a,   # type: int
            b  # type: str
        ):
            # type: (...) -> str
            return str(a)
        """, ['int', 'str'], 'str', lines=[3, 4, 6])

    def test_class_method(self):
        self.check_annotations("""
        class Test(object):
            def test(self, a, b):  #@
                # type: (int, str) -> str
                return str(a)
        """, [None, 'int', 'str'], 'str', lines=[4, 4, 4])

    def test_class_method_split(self):
        self.check_annotations("""
        class Test(object):
            def test( #@
                self,
                a,  # type: int
                b   # type: str
            ):
                # type: (...) -> str
                return str(a)
        """, [None, 'int', 'str'], 'str', lines=[5, 6, 8])

    def test_class_method_self(self):
        self.check_annotations("""
        class Test(object):
            def test(self, a, b):  #@
                # type: (bytes, int, str) -> str
                return str(a)
        """, ['bytes', 'int', 'str'], 'str', lines=[4, 4, 4, 4])

    def test_vararg(self):
        self.check_annotations("""
        def test(a, b, *args):  #@
            # type: (int, str, *str) -> str
            return str(a)
        """, ['int', 'str'], vararg='str', returns='str', lines=[3, 3, 3, 3])

        self.check_annotations("""
        def test(a, # type: int #@
                 b, # type: str
                 *args # type: str
        ):
            # type: (...) -> str
            return str(a)
        """, ['int', 'str'], vararg='str', returns='str', lines=[2, 3, 4, 6])

    def test_kwarg(self):
        self.check_annotations("""
        def test(a, b, **kw):  #@
            # type: (int, str, **int) -> str
            return str(a)
        """, ['int', 'str'], kwarg='int', returns='str', lines=[3, 3, 3, 3])

        self.check_annotations("""
        def test(a, # type: int #@
                 b, # type: str
                 **kwargs # type: str
        ):
            # type: (...) -> str
            return str(a)
        """, ['int', 'str'], kwarg='str', returns='str', lines=[2, 3, 4, 6])

    def test_only_vararg(self):
        self.check_annotations("""
        def test(*args):  #@
            # type: (*str) -> str
            return str(a)
        """, [], vararg='str', returns='str', lines=[3, 3])

        self.check_annotations("""
        def test( #@
                *args # type: str
        ):
            # type: (...) -> str
            return str(a)
        """, [], vararg='str', returns='str', lines=[3, 5])

    def test_only_kwarg(self):
        self.check_annotations("""
        def test(**kw):  #@
            # type: (**int) -> str
            return str(a)
        """, [], kwarg='int', returns='str', lines=[3, 3])

        self.check_annotations("""
        def test( #@
                **args # type: str
        ):
            # type: (...) -> str
            return str(a)
        """, [], kwarg='str', returns='str', lines=[3, 5])

    def test_all_args(self):
        self.check_annotations("""
        def test(a, b, *args, **kw):  #@
            # type: (int, bytes, *str, **int) -> str
            return str(a)
        """, ['int', 'bytes'], vararg='str', kwarg='int', returns='str', lines=[3, 3, 3, 3, 3])

        self.check_annotations("""
        def test( #@
            a, # type: int
            b, # type: bytes
            *args,  # type: str
            **kw  # type: int
        ):
            # type: (...) -> str
            return str(a)
        """, ['int', 'bytes'], vararg='str', kwarg='int', returns='str', lines=[3, 4, 5, 6, 8])

    def test_all_args_with_defaults(self):
        self.check_annotations("""
        def test(a, b=None, *args, **kw):  #@
            # type: (int, bytes, *str, **int) -> str
            return str(a)
        """, ['int', 'bytes'], vararg='str', kwarg='int', returns='str', lines=[3, 3, 3, 3, 3])

        self.check_annotations("""
        def test( #@
            a, # type: int
            b=None, # type: bytes
            *args,  # type: str
            **kw  # type: int
        ):
            # type: (...) -> str
            return str(a)
        """, ['int', 'bytes'], vararg='str', kwarg='int', returns='str', lines=[3, 4, 5, 6, 8])

    def test_assignment(self):
        assign = extract_node(dedent("x = []  # type: List[Employee]"))
        self.assertIsInstance(assign, nodes.Assign)
        self.assertEqual(assign.type_comment.as_string(), 'List[Employee]')

    def test_multi_assignment(self):
        assign = extract_node(dedent("x, y, z = [], [], []  # type: List[int], List[int], List[str]"))
        self.assertIsInstance(assign, nodes.Assign)
        self.assertEqual(assign.type_comment.as_string(), '(List[int], List[int], List[str])')

    def not_passing_test_multi_assignment(self):
        assign = extract_node(dedent("""
        x = [
        1,
        2,
        ]  # type: List[int]
        """))
        self.assertIsInstance(assign, nodes.Assign)
        self.assertEqual(assign.type_comment.as_string(), '(List[int], List[int], List[str])')

    def test_with(self):
        _with = extract_node(dedent("""
        with frobnicate():  # type: int
            pass
        """))
        self.assertIsInstance(_with, nodes.With)
        self.assertEqual(_with.type_comment.as_string(), 'int')

    def test_for(self):
        _for = extract_node(dedent("""
        for x, y in points:  # type: float, float
           pass
        """))
        self.assertIsInstance(_for, nodes.For)
        self.assertEqual(_for.type_comment.as_string(), '(float, float)')
