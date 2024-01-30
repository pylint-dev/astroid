# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest
from _pytest.recwarn import WarningsRecorder

from astroid.decorators import deprecate_default_argument_values


class SomeClass:
    @deprecate_default_argument_values(name="str")
    def __init__(self, name=None, lineno=None): ...

    @deprecate_default_argument_values("3.2", name="str", var="int")
    def func(self, name=None, var=None, type_annotation=None): ...


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
