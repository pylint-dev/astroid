# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import unittest
import xml

import pytest

import astroid
from astroid import bases, builder, nodes, util
from astroid.exceptions import AttributeInferenceError, InferenceError

try:
    import six  # type: ignore[import]  # pylint: disable=unused-import

    HAS_SIX = True
except ImportError:
    HAS_SIX = False


class InstanceModelTest(unittest.TestCase):
    def test_instance_special_model(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class A:
            "test"
            def __init__(self):
                self.a = 42
        a = A()
        a.__class__ #@
        a.__module__ #@
        a.__doc__ #@
        a.__dict__ #@
        """,
            module_name="fake_module",
        )
        assert isinstance(ast_nodes, list)
        cls = next(ast_nodes[0].infer())
        self.assertIsInstance(cls, nodes.ClassDef)
        self.assertEqual(cls.name, "A")

        module = next(ast_nodes[1].infer())
        self.assertIsInstance(module, nodes.Const)
        self.assertEqual(module.value, "fake_module")

        doc = next(ast_nodes[2].infer())
        self.assertIsInstance(doc, nodes.Const)
        self.assertEqual(doc.value, "test")

        dunder_dict = next(ast_nodes[3].infer())
        self.assertIsInstance(dunder_dict, nodes.Dict)
        attr = next(dunder_dict.getitem(nodes.Const("a")).infer())
        self.assertIsInstance(attr, nodes.Const)
        self.assertEqual(attr.value, 42)

    @pytest.mark.xfail(reason="Instance lookup cannot override object model")
    def test_instance_local_attributes_overrides_object_model(self):
        # The instance lookup needs to be changed in order for this to work.
        ast_node = builder.extract_node("""
        class A:
            @property
            def __dict__(self):
                  return []
        A().__dict__
        """)
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.List)
        self.assertEqual(inferred.elts, [])


class UnboundMethodModelTest(unittest.TestCase):
    def test_unbound_method_model(self) -> None:
        ast_nodes = builder.extract_node("""
        class A:
            def test(self): pass
        t = A.test
        t.__class__ #@
        t.__func__ #@
        t.__self__ #@
        t.im_class #@
        t.im_func #@
        t.im_self #@
        t.__doc__ #@
        """)
        assert isinstance(ast_nodes, list)
        cls = next(ast_nodes[0].infer())
        self.assertIsInstance(cls, nodes.ClassDef)
        unbound_name = "function"

        self.assertEqual(cls.name, unbound_name)

        func = next(ast_nodes[1].infer())
        self.assertIsInstance(func, nodes.FunctionDef)
        self.assertEqual(func.name, "test")

        self_ = next(ast_nodes[2].infer())
        self.assertIsInstance(self_, nodes.Const)
        self.assertIsNone(self_.value)

        self.assertEqual(cls.name, next(ast_nodes[3].infer()).name)
        self.assertEqual(func, next(ast_nodes[4].infer()))
        self.assertIsNone(next(ast_nodes[5].infer()).value)

        doc = next(ast_nodes[6].infer())
        self.assertIsInstance(doc, nodes.Const)
        self.assertIsNone(doc.value)


class ClassModelTest(unittest.TestCase):

    def test_class_dunder_new_with_unknown_ancestor(self) -> None:
        """``super().__new__(cls)`` falls back to the object model when an
        ancestor cannot be inferred; the explicit class must fill the first
        parameter and extra arguments must be accepted.

        Regression test for https://github.com/pylint-dev/pylint/issues/8325
        """
        ast_nodes = builder.extract_node("""
        from missing import Base

        class A(Base):
            def __new__(cls, value):
                super().__new__ #@
                return super().__new__(cls)

        class B(Base):
            @classmethod
            def make(cls):
                return cls.__new__(cls)

        B.__new__ #@
        A(1) #@
        B.make() #@
        """)
        assert isinstance(ast_nodes, list)
        for node in ast_nodes[:2]:
            dunder_new = next(node.infer())
            self.assertIsInstance(dunder_new, astroid.BoundMethod)
            self.assertEqual(dunder_new.implicit_parameters(), 0)
            self.assertEqual(dunder_new.argnames(), ["cls", "args", "kwargs"])

        for node, name in zip(ast_nodes[2:], ["A", "B"]):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, astroid.Instance)
            self.assertEqual(inferred.name, name)

    def test_class_model(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class A(object):
            "test"

        class B(A): pass
        class C(A): pass

        A.__module__ #@
        A.__name__ #@
        A.__qualname__ #@
        A.__doc__ #@
        A.__mro__ #@
        A.mro() #@
        A.__bases__ #@
        A.__class__ #@
        A.__dict__ #@
        A.__subclasses__() #@
        """,
            module_name="fake_module",
        )
        assert isinstance(ast_nodes, list)
        module = next(ast_nodes[0].infer())
        self.assertIsInstance(module, nodes.Const)
        self.assertEqual(module.value, "fake_module")

        name = next(ast_nodes[1].infer())
        self.assertIsInstance(name, nodes.Const)
        self.assertEqual(name.value, "A")

        qualname = next(ast_nodes[2].infer())
        self.assertIsInstance(qualname, nodes.Const)
        self.assertEqual(qualname.value, "fake_module.A")

        doc = next(ast_nodes[3].infer())
        self.assertIsInstance(doc, nodes.Const)
        self.assertEqual(doc.value, "test")

        mro = next(ast_nodes[4].infer())
        self.assertIsInstance(mro, nodes.Tuple)
        self.assertEqual([cls.name for cls in mro.elts], ["A", "object"])

        called_mro = next(ast_nodes[5].infer())
        self.assertEqual(called_mro.elts, mro.elts)

        base_nodes = next(ast_nodes[6].infer())
        self.assertIsInstance(base_nodes, nodes.Tuple)
        self.assertEqual([cls.name for cls in base_nodes.elts], ["object"])
        self.assertIsInstance(base_nodes.parent, nodes.ClassDef)
        self.assertEqual(base_nodes.root().name, "fake_module")

        cls = next(ast_nodes[7].infer())
        self.assertIsInstance(cls, nodes.ClassDef)
        self.assertEqual(cls.name, "type")

        cls_dict = next(ast_nodes[8].infer())
        self.assertIsInstance(cls_dict, nodes.Dict)

        subclasses = next(ast_nodes[9].infer())
        self.assertIsInstance(subclasses, nodes.List)
        self.assertEqual([cls.name for cls in subclasses.elts], ["B", "C"])


class ModuleModelTest(unittest.TestCase):
    def test_priority_to_local_defined_values(self) -> None:
        ast_node = astroid.parse("""
        __file__ = "mine"
        """)
        file_value = next(ast_node.igetattr("__file__"))
        self.assertIsInstance(file_value, nodes.Const)
        self.assertEqual(file_value.value, "mine")

    def test_module_model(self) -> None:
        ast_nodes = builder.extract_node("""
        import xml
        xml.__path__ #@
        xml.__name__ #@
        xml.__doc__ #@
        xml.__file__ #@
        xml.__spec__ #@
        xml.__loader__ #@
        xml.__cached__ #@
        xml.__package__ #@
        xml.__dict__ #@
        xml.__init__ #@
        xml.__new__ #@

        xml.__subclasshook__ #@
        xml.__str__ #@
        xml.__sizeof__ #@
        xml.__repr__ #@
        xml.__reduce__ #@

        xml.__setattr__ #@
        xml.__reduce_ex__ #@
        xml.__lt__ #@
        xml.__le__ #@
        xml.__eq__ #@
        xml.__ne__ #@
        xml.__ge__ #@
        xml.__gt__ #@
        xml.__format__ #@
        xml.__delattr__ #@
        xml.__getattribute__ #@
        xml.__hash__ #@
        xml.__dir__ #@
        xml.__call__ #@
        xml.__closure__ #@
        """)
        assert isinstance(ast_nodes, list)
        path = next(ast_nodes[0].infer())
        self.assertIsInstance(path, nodes.List)
        self.assertIsInstance(path.elts[0], nodes.Const)
        self.assertEqual(path.elts[0].value, xml.__path__[0])

        name = next(ast_nodes[1].infer())
        self.assertIsInstance(name, nodes.Const)
        self.assertEqual(name.value, "xml")

        doc = next(ast_nodes[2].infer())
        self.assertIsInstance(doc, nodes.Const)
        self.assertEqual(doc.value, xml.__doc__)

        file_ = next(ast_nodes[3].infer())
        self.assertIsInstance(file_, nodes.Const)
        self.assertEqual(file_.value, xml.__file__.replace(".pyc", ".py"))

        for ast_node in ast_nodes[4:7]:
            inferred = next(ast_node.infer())
            self.assertIs(inferred, astroid.Uninferable)

        package = next(ast_nodes[7].infer())
        self.assertIsInstance(package, nodes.Const)
        self.assertEqual(package.value, "xml")

        dict_ = next(ast_nodes[8].infer())
        self.assertIsInstance(dict_, nodes.Dict)

        init_ = next(ast_nodes[9].infer())
        assert isinstance(init_, bases.BoundMethod)
        init_result = next(
            init_.infer_call_result(
                nodes.Call(
                    parent=None,
                    lineno=None,
                    col_offset=None,
                    end_lineno=None,
                    end_col_offset=None,
                )
            )
        )
        assert isinstance(init_result, nodes.Const)
        assert init_result.value is None

        new_ = next(ast_nodes[10].infer())
        assert isinstance(new_, bases.BoundMethod)

        # Inherited attributes return Uninferable.
        for ast_node in ast_nodes[11:29]:
            inferred = next(ast_node.infer())
            self.assertIs(inferred, astroid.Uninferable)

        # Attributes that don't exist on modules raise InferenceError.
        for ast_node in ast_nodes[29:31]:
            with pytest.raises(InferenceError):
                next(ast_node.infer())


class FunctionModelTest(unittest.TestCase):

    @pytest.mark.xfail(reason="Descriptors cannot infer what self is")
    def test_descriptor_not_inferrring_self(self):
        # We can't infer __get__(X, Y)() when the bounded function
        # uses self, because of the tree's parent not being propagating good enough.
        result = builder.extract_node("""
        class A(object):
            x = 42
        def test(self): return self.x
        f = test.__get__(A(), A)
        f() #@
        """)
        result = next(result.infer())
        self.assertIsInstance(result, nodes.Const)
        self.assertEqual(result.value, 42)

    def test_function_model(self) -> None:
        ast_nodes = builder.extract_node(
            '''
        def func(a=1, b=2):
            """test"""
        func.__name__ #@
        func.__doc__ #@
        func.__qualname__ #@
        func.__module__  #@
        func.__defaults__ #@
        func.__dict__ #@
        func.__globals__ #@
        func.__code__ #@
        func.__closure__ #@
        func.__init__ #@
        func.__new__ #@

        func.__subclasshook__ #@
        func.__str__ #@
        func.__sizeof__ #@
        func.__repr__ #@
        func.__reduce__ #@

        func.__reduce_ex__ #@
        func.__lt__ #@
        func.__le__ #@
        func.__eq__ #@
        func.__ne__ #@
        func.__ge__ #@
        func.__gt__ #@
        func.__format__ #@
        func.__delattr__ #@
        func.__getattribute__ #@
        func.__hash__ #@
        func.__dir__ #@
        func.__class__ #@

        func.__setattr__ #@
        func.__builtins__ #@
        func.__getstate__ #@
        func.__init_subclass__ #@
        func.__type_params__ #@
        ''',
            module_name="fake_module",
        )
        assert isinstance(ast_nodes, list)
        name = next(ast_nodes[0].infer())
        self.assertIsInstance(name, nodes.Const)
        self.assertEqual(name.value, "func")

        doc = next(ast_nodes[1].infer())
        self.assertIsInstance(doc, nodes.Const)
        self.assertEqual(doc.value, "test")

        qualname = next(ast_nodes[2].infer())
        self.assertIsInstance(qualname, nodes.Const)
        self.assertEqual(qualname.value, "fake_module.func")

        module = next(ast_nodes[3].infer())
        self.assertIsInstance(module, nodes.Const)
        self.assertEqual(module.value, "fake_module")

        defaults = next(ast_nodes[4].infer())
        self.assertIsInstance(defaults, nodes.Tuple)
        self.assertEqual([default.value for default in defaults.elts], [1, 2])

        dict_ = next(ast_nodes[5].infer())
        self.assertIsInstance(dict_, nodes.Dict)

        globals_ = next(ast_nodes[6].infer())
        self.assertIsInstance(globals_, nodes.Dict)

        for ast_node in ast_nodes[7:9]:
            self.assertIs(next(ast_node.infer()), astroid.Uninferable)

        init_ = next(ast_nodes[9].infer())
        assert isinstance(init_, bases.BoundMethod)
        init_result = next(
            init_.infer_call_result(
                nodes.Call(
                    parent=None,
                    lineno=None,
                    col_offset=None,
                    end_lineno=None,
                    end_col_offset=None,
                )
            )
        )
        assert isinstance(init_result, nodes.Const)
        assert init_result.value is None

        new_ = next(ast_nodes[10].infer())
        assert isinstance(new_, bases.BoundMethod)

        # Remaining attributes return Uninferable.
        for ast_node in ast_nodes[11:34]:
            inferred = next(ast_node.infer())
            assert inferred is util.Uninferable

    def test_annotations_kwdefaults(self) -> None:
        ast_node = builder.extract_node("""
        def test(a: 1, *args: 2, f:4='lala', **kwarg:3)->2: pass
        test.__annotations__ #@
        test.__kwdefaults__ #@
        """)
        annotations = next(ast_node[0].infer())
        self.assertIsInstance(annotations, nodes.Dict)
        self.assertIsInstance(annotations.getitem(nodes.Const("return")), nodes.Const)
        self.assertEqual(annotations.getitem(nodes.Const("return")).value, 2)
        self.assertIsInstance(annotations.getitem(nodes.Const("a")), nodes.Const)
        self.assertEqual(annotations.getitem(nodes.Const("a")).value, 1)
        self.assertEqual(annotations.getitem(nodes.Const("args")).value, 2)
        self.assertEqual(annotations.getitem(nodes.Const("kwarg")).value, 3)

        self.assertEqual(annotations.getitem(nodes.Const("f")).value, 4)

        kwdefaults = next(ast_node[1].infer())
        self.assertIsInstance(kwdefaults, nodes.Dict)
        # self.assertEqual(kwdefaults.getitem('f').value, 'lala')

    def test_annotation_positional_only(self):
        ast_node = builder.extract_node("""
        def test(a: 1, b: 2, /, c: 3): pass
        test.__annotations__ #@
        """)
        annotations = next(ast_node.infer())
        self.assertIsInstance(annotations, nodes.Dict)

        self.assertIsInstance(annotations.getitem(nodes.Const("a")), nodes.Const)
        self.assertEqual(annotations.getitem(nodes.Const("a")).value, 1)
        self.assertEqual(annotations.getitem(nodes.Const("b")).value, 2)
        self.assertEqual(annotations.getitem(nodes.Const("c")).value, 3)


@pytest.mark.parametrize("func_def", ["def", "async def"])
def test_generator_has_no_descriptor_get(func_def: str) -> None:
    node = builder.extract_node(f"""
    {func_def} func():
        yield
    func() #@
    """)
    generator = next(node.infer())
    assert isinstance(generator, bases.Generator)
    with pytest.raises(AttributeInferenceError):
        generator.getattr("__get__")
    with pytest.raises(InferenceError):
        list(generator.igetattr("__get__"))


class ExceptionModelTest(unittest.TestCase):
    @staticmethod
    def test_valueerror_py3() -> None:
        ast_nodes = builder.extract_node("""
        try:
            x[42]
        except ValueError as err:
           err.args #@
           err.__traceback__ #@

           err.message #@
        """)
        assert isinstance(ast_nodes, list)
        args = next(ast_nodes[0].infer())
        assert isinstance(args, astroid.Instance)
        assert args.qname() == "builtins.tuple"
        tb = next(ast_nodes[1].infer())
        # If 'contextlib' is loaded, '__traceback__' could be set inside
        # '__exit__' method in which case 'err.__traceback__' will be 'Uninferable'
        if tb is not util.Uninferable:
            assert isinstance(tb, astroid.Instance)
            assert tb.name == "traceback"

        with pytest.raises(InferenceError):
            next(ast_nodes[2].infer())

    @unittest.skipIf(HAS_SIX, "This test fails if the six library is installed")
    def test_oserror(self) -> None:
        ast_nodes = builder.extract_node("""
        try:
            raise OSError("a")
        except OSError as err:
           err.filename #@
           err.filename2 #@
           err.errno #@
        """)
        expected_values = ["", "", 0]
        for node, value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            assert isinstance(inferred, nodes.Const)
            assert inferred.value == value


@pytest.mark.parametrize("parentheses", (True, False))
def test_lru_cache(parentheses) -> None:
    ast_nodes = builder.extract_node(f"""
        import functools
        class Foo(object):
            @functools.lru_cache{"()" if parentheses else ""}
            def foo():
                pass
        f = Foo()
        f.foo.cache_clear #@
        f.foo.__wrapped__ #@
        f.foo.cache_info() #@
        """)
    assert isinstance(ast_nodes, list)
    cache_clear = next(ast_nodes[0].infer())
    assert isinstance(cache_clear, astroid.BoundMethod)
    wrapped = next(ast_nodes[1].infer())
    assert isinstance(wrapped, nodes.FunctionDef)
    assert wrapped.name == "foo"
    cache_info = next(ast_nodes[2].infer())
    assert isinstance(cache_info, astroid.Instance)


def test_all_object_dunders_accessible() -> None:
    """Test that object dunders are accessible on classes and instances."""
    # Use actual dunders from object in the current Python version
    object_dunders = [attr for attr in dir(object) if attr.startswith("__")]

    cls, instance = builder.extract_node("""
        class MyClass:
            pass

        MyClass  #@
        MyClass()  #@
        """)
    cls = next(cls.infer())
    instance = next(instance.infer())

    for dunder in object_dunders:
        assert cls.getattr(dunder)
        assert instance.getattr(dunder)


def test_unbound_method_object_dunders_return_uninferable() -> None:
    """Test that ObjectModel-only dunders on unbound methods return Uninferable."""
    node = builder.extract_node("""
    class A:
        def test(self): pass
    A.test  #@
    """)
    unbound = next(node.infer())
    assert isinstance(unbound, bases.UnboundMethod)

    for dunder in (
        "__eq__",
        "__ne__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        "__repr__",
        "__str__",
        "__hash__",
    ):
        inferred = next(unbound.igetattr(dunder))
        assert inferred is util.Uninferable, f"{dunder} should be Uninferable"

        attrs = unbound.getattr(dunder)
        assert attrs, f"{dunder} getattr should return results"


@pytest.mark.parametrize(
    "attr",
    [
        "__get__",
        "__defaults__",
        "__annotations__",
        "__dict__",
        "__globals__",
        "__kwdefaults__",
    ],
)
def test_builtin_func_no_descriptor_attrs(attr: str) -> None:
    """Test builtin functions lack descriptor protocol attributes."""
    node = builder.extract_node(f"eval.{attr}")
    with pytest.raises(InferenceError):
        next(node.infer())
