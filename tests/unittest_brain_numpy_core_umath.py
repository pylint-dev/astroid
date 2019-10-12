# -*- encoding=utf-8 -*-
# Copyright (c) 2017-2018 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER
import unittest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder
from astroid import nodes


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class NumpyBrainCoreUmathTest(unittest.TestCase):
    """
    Test of all members of numpy.core.umath module
    """

    no_arg_ufunc = ("geterrobj",)

    one_arg_ufunc_spec = ("seterrobj",)

    one_arg_ufunc = (
        "arccos",
        "arccosh",
        "arcsin",
        "arcsinh",
        "arctan",
        "arctanh",
        "cbrt",
        "conj",
        "conjugate",
        "cosh",
        "deg2rad",
        "degrees",
        "exp2",
        "expm1",
        "fabs",
        "frexp",
        "isfinite",
        "isinf",
        "log",
        "log1p",
        "log2",
        "logical_not",
        "modf",
        "negative",
        "rad2deg",
        "radians",
        "reciprocal",
        "rint",
        "sign",
        "signbit",
        "spacing",
        "square",
        "tan",
        "tanh",
        "trunc",
    )

    two_args_ufunc = (
        "bitwise_and",
        "bitwise_or",
        "bitwise_xor",
        "copysign",
        "divide",
        "equal",
        "floor_divide",
        "fmax",
        "fmin",
        "fmod",
        "greater",
        "hypot",
        "ldexp",
        "left_shift",
        "less",
        "logaddexp",
        "logaddexp2",
        "logical_and",
        "logical_or",
        "logical_xor",
        "maximum",
        "minimum",
        "nextafter",
        "not_equal",
        "power",
        "remainder",
        "right_shift",
        "subtract",
        "true_divide",
    )

    all_ufunc = no_arg_ufunc + one_arg_ufunc_spec + one_arg_ufunc + two_args_ufunc

    constants = ("e", "euler_gamma")

    def _inferred_numpy_attribute(self, func_name):
        node = builder.extract_node(
            """
        import numpy.core.umath as tested_module
        func = tested_module.{:s}
        func""".format(
                func_name
            )
        )
        return next(node.infer())

    def test_numpy_core_umath_constants(self):
        """
        Test that constants have Const type.
        """
        for const in self.constants:
            with self.subTest(const=const):
                inferred = self._inferred_numpy_attribute(const)
                self.assertIsInstance(inferred, nodes.Const)

    def test_numpy_core_umath_constants_values(self):
        """
        Test the values of the constants.
        """
        exact_values = {"e": 2.718281828459045, "euler_gamma": 0.5772156649015329}
        for const in self.constants:
            with self.subTest(const=const):
                inferred = self._inferred_numpy_attribute(const)
                self.assertEqual(inferred.value, exact_values[const])

    def test_numpy_core_umath_functions(self):
        """
        Test that functions have FunctionDef type.
        """
        for func in self.all_ufunc:
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                self.assertIsInstance(inferred, nodes.FunctionDef)

    def test_numpy_core_umath_functions_no_arg(self):
        """
        Test that functions with no arguments have really no arguments.
        """
        for func in self.no_arg_ufunc:
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                self.assertFalse(inferred.argnames())

    def test_numpy_core_umath_functions_one_arg_spec(self):
        """
        Test the arguments names of functions.
        """
        exact_arg_names = ["errobj"]
        for func in self.one_arg_ufunc_spec:
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                self.assertEqual(inferred.argnames(), exact_arg_names)

    def test_numpy_core_umath_functions_one_arg(self):
        """
        Test the arguments names of functions.
        """
        exact_arg_names = ["x", "out", "where", "casting", "order", "dtype", "subok"]
        for func in self.one_arg_ufunc:
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                self.assertEqual(inferred.argnames(), exact_arg_names)

    def test_numpy_core_umath_functions_two_args(self):
        """
        Test the arguments names of functions.
        """
        exact_arg_names = [
            "x1",
            "x2",
            "out",
            "where",
            "casting",
            "order",
            "dtype",
            "subok",
        ]
        for func in self.two_args_ufunc:
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                self.assertEqual(inferred.argnames(), exact_arg_names)

    def test_numpy_core_umath_functions_kwargs_default_values(self):
        """
        Test the default values for keyword arguments.
        """
        exact_kwargs_default_values = [None, True, "same_kind", "K", None, True]
        for func in self.one_arg_ufunc + self.two_args_ufunc:
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                default_args_values = [
                    default.value for default in inferred.args.defaults
                ]
                self.assertEqual(default_args_values, exact_kwargs_default_values)

    def _inferred_numpy_func_call(self, func_name, *func_args):
        node = builder.extract_node(
            """
        import numpy as np
        func = np.{:s}
        func()
        """.format(
                func_name
            )
        )
        return node.infer()

    def test_numpy_core_umath_functions_return_type(self):
        """
        Test that functions which should return a ndarray do return it
        """
        ndarray_returning_func = [
            f
            for f in self.all_ufunc
            if f not in ("geterrobj", "seterrobj", "frexp", "modf")
        ]
        licit_array_types = (".ndarray",)
        for func_ in ndarray_returning_func:
            with self.subTest(typ=func_):
                inferred_values = list(self._inferred_numpy_func_call(func_))
                self.assertTrue(
                    len(inferred_values) == 1,
                    msg="Too much inferred value for {:s}".format(func_),
                )
                self.assertTrue(
                    inferred_values[-1].pytype() in licit_array_types,
                    msg="Illicit type for {:s} ({})".format(
                        func_, inferred_values[-1].pytype()
                    ),
                )


if __name__ == "__main__":
    unittest.main()
