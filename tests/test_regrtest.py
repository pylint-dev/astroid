# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import platform
import sys
import textwrap
import unittest
from importlib.metadata import PackageNotFoundError, version
from unittest import mock

import pytest

from astroid import MANAGER, Instance, bases, manager, nodes, parse, test_utils
from astroid.builder import AstroidBuilder, _extract_single_node, extract_node
from astroid.const import PY312_PLUS, PY315_PLUS
from astroid.context import InferenceContext
from astroid.exceptions import AstroidSyntaxError, InferenceError
from astroid.manager import AstroidManager
from astroid.raw_building import build_module
from astroid.util import Uninferable

from . import resources

try:
    import numpy  # pylint: disable=unused-import
except ImportError:
    HAS_NUMPY = False
else:
    HAS_NUMPY = True

try:
    # numpy.distutils was removed in NumPy 2.0. Read the version from the
    # installed metadata so the deprecated module is never imported here
    HAS_NUMPY_DISTUTILS = int(version("numpy").split(".")[0]) < 2
except (PackageNotFoundError, ValueError):
    HAS_NUMPY_DISTUTILS = False


class NonRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, resources.find("data"))
        MANAGER.always_load_extensions = True
        self.addCleanup(MANAGER.clear_cache)

    def tearDown(self) -> None:
        MANAGER.always_load_extensions = False
        sys.path.pop(0)
        sys.path_importer_cache.pop(resources.find("data"), None)

    def test_manager_instance_attributes_reference_global_MANAGER(self) -> None:
        for expected in (True, False):
            with mock.patch.dict(
                manager.AstroidManager.brain,
                values={"always_load_extensions": expected},
            ):
                assert (
                    MANAGER.always_load_extensions
                    == manager.AstroidManager.brain["always_load_extensions"]
                )
            with mock.patch.dict(
                manager.AstroidManager.brain,
                values={"optimize_ast": expected},
            ):
                assert (
                    MANAGER.optimize_ast == manager.AstroidManager.brain["optimize_ast"]
                )

    def test_module_path(self) -> None:
        man = test_utils.brainless_manager()
        mod = man.ast_from_module_name("package.import_package_subpackage_module")
        package = next(mod.igetattr("package"))
        self.assertEqual(package.name, "package")
        subpackage = next(package.igetattr("subpackage"))
        self.assertIsInstance(subpackage, nodes.Module)
        self.assertTrue(subpackage.package)
        self.assertEqual(subpackage.name, "package.subpackage")
        module = next(subpackage.igetattr("module"))
        self.assertEqual(module.name, "package.subpackage.module")

    def test_package_sidepackage(self) -> None:
        brainless_manager = test_utils.brainless_manager()
        assert "package.sidepackage" not in MANAGER.astroid_cache
        package = brainless_manager.ast_from_module_name("absimp")
        self.assertIsInstance(package, nodes.Module)
        self.assertTrue(package.package)
        subpackage = next(package.getattr("sidepackage")[0].infer())
        self.assertIsInstance(subpackage, nodes.Module)
        self.assertTrue(subpackage.package)
        self.assertEqual(subpackage.name, "absimp.sidepackage")

    def test_living_property(self) -> None:
        builder = AstroidBuilder(AstroidManager())
        builder._done = {}
        builder._module = sys.modules[__name__]
        builder.object_build(build_module("module_name", ""), Whatever)

    @unittest.skipIf(not HAS_NUMPY, "Needs numpy")
    def test_numpy_crash(self):
        """Test don't crash on numpy."""
        # a crash occurred somewhere in the past, and an
        # InferenceError instead of a crash was better, but now we even infer!
        builder = AstroidBuilder(AstroidManager())
        data = """
from numpy import multiply

multiply([1, 2], [3, 4])
"""
        astroid = builder.string_build(data, __name__, __file__)
        callfunc = astroid.body[1].value.func
        inferred = callfunc.inferred()
        self.assertEqual(len(inferred), 1)

    @unittest.skipUnless(
        HAS_NUMPY and HAS_NUMPY_DISTUTILS and not PY312_PLUS,
        "Needs numpy.distutils (removed in numpy 2.0) and < Python 3.12",
    )
    def test_numpy_distutils(self):
        """Special handling of virtualenv's patching of distutils shouldn't interfere
        with numpy.distutils.
        """
        node = extract_node("""
from numpy.distutils.misc_util import is_sequence
is_sequence("ABC") #@
""")
        inferred = node.inferred()
        self.assertIsInstance(inferred[0], nodes.Const)

    def test_nameconstant(self) -> None:
        # used to fail for Python 3.4
        builder = AstroidBuilder(AstroidManager())
        astroid = builder.string_build("def test(x=True): pass")
        default = astroid.body[0].args.args[0]
        self.assertEqual(default.name, "x")
        self.assertEqual(next(default.infer()).value, True)

    def test_recursion_regression_issue25(self) -> None:
        builder = AstroidBuilder(AstroidManager())
        data = """
import recursion as base

_real_Base = base.Base

class Derived(_real_Base):
    pass

def run():
    base.Base = Derived
"""
        astroid = builder.string_build(data, __name__, __file__)
        # Used to crash in _is_metaclass, due to wrong
        # ancestors chain
        classes = astroid.nodes_of_class(nodes.ClassDef)
        for klass in classes:
            # triggers the _is_metaclass call
            klass.type  # pylint: disable=pointless-statement  # noqa: B018

    def test_decorator_callchain_issue42(self) -> None:
        builder = AstroidBuilder(AstroidManager())
        data = """

def test():
    def factory(func):
        def newfunc():
            func()
        return newfunc
    return factory

@test()
def crash():
    pass
"""
        astroid = builder.string_build(data, __name__, __file__)
        self.assertEqual(astroid["crash"].type, "function")

    def test_filter_stmts_scoping(self) -> None:
        builder = AstroidBuilder(AstroidManager())
        data = """
def test():
    compiler = int()
    class B(compiler.__class__):
        pass
    compiler = B()
    return compiler
"""
        astroid = builder.string_build(data, __name__, __file__)
        test = astroid["test"]
        result = next(test.infer_call_result(astroid))
        self.assertIsInstance(result, Instance)
        base = next(result._proxied.bases[0].infer())
        self.assertEqual(base.name, "int")

    def test_filter_stmts_nested_if(self) -> None:
        builder = AstroidBuilder(AstroidManager())
        data = """
def test(val):
    variable = None

    if val == 1:
        variable = "value"
        if variable := "value":
            pass

    elif val == 2:
        variable = "value_two"
        variable = "value_two"

    return variable
"""
        module = builder.string_build(data, __name__, __file__)
        test_func = module["test"]
        result = list(test_func.infer_call_result(module))
        assert len(result) == 3
        assert isinstance(result[0], nodes.Const)
        assert result[0].value is None
        assert result[0].lineno == 3
        assert isinstance(result[1], nodes.Const)
        assert result[1].value == "value"
        assert result[1].lineno == 7
        assert isinstance(result[1], nodes.Const)
        assert result[2].value == "value_two"
        assert result[2].lineno == 12

    def test_ancestors_patching_class_recursion(self) -> None:
        node = AstroidBuilder(AstroidManager()).string_build(textwrap.dedent("""
        import string
        Template = string.Template

        class A(Template):
            pass

        class B(A):
            pass

        def test(x=False):
            if x:
                string.Template = A
            else:
                string.Template = B
        """))
        klass = node["A"]
        ancestors = list(klass.ancestors())
        self.assertEqual(ancestors[0].qname(), "string.Template")

    @unittest.skipUnless(PY312_PLUS, "Uses 3.12 type param syntax")
    def test_decorator_names_type_param(self) -> None:
        node = extract_node("""
        class Basket[T]:
            @T
            def apple(self): #@
                pass
        """)

        self.assertEqual(node.decoratornames(), {"typing.TypeVar"})
        self.assertIs(next(node.infer()), node)

    def test_decorator_names_slice(self) -> None:
        node = extract_node("""
        @slice(0)
        def f(): #@
            pass
        """)

        self.assertEqual(node.decoratornames(), {"builtins.slice"})
        self.assertIs(next(node.infer()), node)


class Whatever:
    a = property(lambda x: x, lambda x: x)  # type: ignore[misc]


def test_crash_in_dunder_inference_prevented() -> None:
    code = """
    class MyClass():
        def fu(self, objects):
            delitem = dict.__delitem__.__get__(self, dict)
            delitem #@
    """
    inferred = next(extract_node(code).infer())
    assert inferred.qname() == "builtins.dict.__delitem__"


def test_regression_crash_classmethod() -> None:
    """Regression test for a crash reported in
    https://github.com/pylint-dev/pylint/issues/4982.
    """
    code = """
    class Base:
        @classmethod
        def get_first_subclass(cls):
            for subclass in cls.__subclasses__():
                return subclass
            return object


    subclass = Base.get_first_subclass()


    class Another(subclass):
        pass
    """
    parse(code)


def test_max_inferred_for_complicated_class_hierarchy() -> None:
    """Regression test for a crash reported in
    https://github.com/pylint-dev/pylint/issues/5679.

    The class hierarchy of 'sqlalchemy' is so intricate that it becomes uninferable with
    the standard max_inferred of 100. We used to crash when this happened.
    """
    # Create module and get relevant nodes
    module = resources.build_file(
        str(resources.RESOURCE_PATH / "max_inferable_limit_for_classes" / "main.py")
    )
    init_attr_node = module.body[-1].body[0].body[0].value.func
    init_object_node = module.body[-1].mro()[-1]["__init__"]
    super_node = next(init_attr_node.expr.infer())

    # Arbitrarily limit the max number of inferred nodes per context
    InferenceContext.max_inferred = -1
    context = InferenceContext()

    # Try to infer 'object.__init__' > because of limit is impossible
    for inferred in bases._infer_stmts([init_object_node], context, frame=super):
        assert inferred == Uninferable

    # Reset inference limit
    InferenceContext.max_inferred = 100
    # Check that we don't crash on a previously uninferable node
    assert super_node.getattr("__init__", context=context)[0] == Uninferable


@mock.patch(
    "astroid.nodes.ImportFrom._infer",
    side_effect=RecursionError,
)
def test_recursion_during_inference(mocked) -> None:
    """Check that we don't crash if we hit the recursion limit during inference."""
    node: nodes.Call = _extract_single_node("""
    from module import something
    something()
    """)
    with pytest.raises(InferenceError) as error:
        next(node.infer())
    assert error.value.message.startswith("RecursionError raised")


def test_regression_missing_callcontext() -> None:
    node: nodes.Attribute = _extract_single_node(textwrap.dedent("""
        import functools

        class MockClass:
            def _get_option(self, option):
                return "mystr"

            enabled = property(functools.partial(_get_option, option='myopt'))

        MockClass().enabled
        """))
    assert node.inferred()[0].value == "mystr"


def test_regression_root_is_not_a_module() -> None:
    """Regression test for #2672."""
    node: nodes.ClassDef = _extract_single_node(textwrap.dedent("""
        a=eval.__get__(1).__gt__

        @a
        class c: ...
        """))
    assert node.name == "c"


def test_regression_eval_get_of_arg() -> None:
    """Regression test for #2743."""
    node = _extract_single_node("eval.__get__(1)")
    with pytest.raises(InferenceError):
        next(node.infer())


# On Python 3.15+ the parser emits a regular SyntaxError instead of a MemoryError for deeply nested
# parentheses, so the special-case test here is no longer needed.
@pytest.mark.skipif(PY315_PLUS, reason="No longer a MemoryError on Python 3.15+")
def test_regression_parse_deeply_nested_parentheses() -> None:
    """Regression test for issue #2643."""
    with pytest.raises(AstroidSyntaxError, match="Parsing Python code failed:") as ctx:
        extract_node(
            "A=((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((c,j=t"
        )
    expected = (
        SyntaxError if platform.python_implementation() == "PyPy" else MemoryError
    )
    assert isinstance(ctx.value.error, expected)


def test_relative_import_call_infers_to_target(tmp_path) -> None:
    """Regression test for https://github.com/pylint-dev/astroid/issues/850.

    A call to a name pulled in via ``from .lib import setup`` used to infer as
    ``Uninferable`` when the directory had no ``__init__.py``: the module was
    named after its file path, so the relative import had no parent package.
    """
    pkg = tmp_path / "pkg850"
    pkg.mkdir()
    (pkg / "lib.py").write_text("def setup():\n    pass\n")
    (pkg / "app.py").write_text(textwrap.dedent("""\
            from .lib import setup

            def f():
                setup()
        """))
    sys.path.insert(0, str(tmp_path))
    try:
        module = MANAGER.ast_from_file(str(pkg / "app.py"), source=True)
        call_node = module.body[1].body[0].value
        inferred = list(call_node.func.infer())
        assert Uninferable not in inferred
        assert any(
            isinstance(node, nodes.FunctionDef) and node.name == "setup"
            for node in inferred
        )
    finally:
        sys.path.remove(str(tmp_path))
        MANAGER.clear_cache()
