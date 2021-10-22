import pytest
from _pytest.recwarn import WarningsRecorder

import astroid.decorators


class SomeClass:
    @astroid.decorators.deprecate_default_argument_values(name="str")
    def __init__(self, name=None, lineno=None):
        ...

    @astroid.decorators.deprecate_default_argument_values("3.2", name="str", var="int")
    def func(self, name=None, var=None, type_annotation=None):
        ...


class SomeOtherClass:
    @astroid.decorators.deprecate_arguments(
        "arg1", "arg2", hint="pass to `func2` instead"
    )
    def func(self, arg1=None, arg2=None, arg3=None):
        ...


class TestDeprecationDecorators:
    @staticmethod
    def test_deprecated_default_argument_values_one_arg() -> None:
        with pytest.warns(DeprecationWarning) as records:
            # No argument passed for 'name'
            SomeClass()
            assert len(records) == 1
            assert "name" in records[0].message.args[0]
            assert "'SomeClass.__init__'" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            # 'None' passed as argument for 'name'
            SomeClass(None)
            assert len(records) == 1
            assert "name" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            # 'None' passed as keyword argument for 'name'
            SomeClass(name=None)
            assert len(records) == 1
            assert "name" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            # No value passed for 'name'
            SomeClass(lineno=42)
            assert len(records) == 1
            assert "name" in records[0].message.args[0]

    @staticmethod
    def test_deprecated_default_argument_values_two_args() -> None:
        instance = SomeClass(name="")

        # No value of 'None' passed for both arguments
        with pytest.warns(DeprecationWarning) as records:
            instance.func()
            assert len(records) == 2
            assert "'SomeClass.func'" in records[0].message.args[0]
            assert "astroid 3.2" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            instance.func(None)
            assert len(records) == 2

        with pytest.warns(DeprecationWarning) as records:
            instance.func(name=None)
            assert len(records) == 2

        with pytest.warns(DeprecationWarning) as records:
            instance.func(var=None)
            assert len(records) == 2

        with pytest.warns(DeprecationWarning) as records:
            instance.func(name=None, var=None)
            assert len(records) == 2

        with pytest.warns(DeprecationWarning) as records:
            instance.func(type_annotation="")
            assert len(records) == 2

        # No value of 'None' for one argument
        with pytest.warns(DeprecationWarning) as records:
            instance.func(42)
            assert len(records) == 1
            assert "var" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            instance.func(name="")
            assert len(records) == 1
            assert "var" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            instance.func(var=42)
            assert len(records) == 1
            assert "name" in records[0].message.args[0]

    @staticmethod
    def test_deprecated_default_argument_values_ok(recwarn: WarningsRecorder) -> None:
        """No DeprecationWarning should be emitted
        if all arguments are passed with not None values.
        """
        instance = SomeClass(name="some_name")
        instance.func(name="", var=42)
        assert len(recwarn) == 0

    @staticmethod
    def test_deprecated_argument_pass_by_position() -> None:
        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(1, 2, 3)
            assert len(records) == 2
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]
            assert "arg2" in records[1].message.args[0]
            assert "'SomeOtherClass.func'" in records[1].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(1, 2)
            assert len(records) == 2
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]
            assert "arg2" in records[1].message.args[0]
            assert "'SomeOtherClass.func'" in records[1].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(1)
            assert len(records) == 1
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(1, baz=3)
            assert len(records) == 1
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]

        with pytest.warns(None) as records:
            SomeOtherClass().func(baz=3)
            assert len(records) == 0

    @staticmethod
    def test_deprecated_argument_pass_by_name() -> None:
        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(arg1=1, arg2=2, baz=3)
            assert len(records) == 2
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]
            assert "arg2" in records[1].message.args[0]
            assert "'SomeOtherClass.func'" in records[1].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(arg1=1, arg2=2)
            assert len(records) == 2
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]
            assert "arg2" in records[1].message.args[0]
            assert "'SomeOtherClass.func'" in records[1].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(arg1=1)
            assert len(records) == 1
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(arg2=1)
            assert len(records) == 1
            assert "arg2" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]

        with pytest.warns(DeprecationWarning) as records:
            SomeOtherClass().func(1, baz=3)
            assert len(records) == 1
            assert "arg1" in records[0].message.args[0]
            assert "'SomeOtherClass.func'" in records[0].message.args[0]

        with pytest.warns(None) as records:
            SomeOtherClass().func(baz=3)
            assert len(records) == 0
