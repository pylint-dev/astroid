# -*- encoding=utf-8 -*-
# Copyright (c) 2017-2018 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2017 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER
import unittest
import contextlib

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder
from astroid import nodes
from astroid import node_classes
from astroid import bases
from astroid import util


class SubTestWrapper(unittest.TestCase):
    """
    A class for supporting all unittest version wether or not subTest is available
    """

    def subTest(self, msg=None, **params):
        try:
            # For python versions above 3.5 this should be ok
            return super(SubTestWrapper, self).subTest(msg, **params)
        except AttributeError:
            #  For python versions below 3.5
            return subTestMock(msg)


@contextlib.contextmanager
def subTestMock(msg=None):
    """
    A mock for subTest which do nothing
    """
    yield msg


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class NumpyBrainCoreNumericTypesTest(SubTestWrapper):
    """
    Test of all the missing types defined in numerictypes module.
    """

    all_types = [
        "uint16",
        "uint32",
        "uint64",
        "float16",
        "float32",
        "float64",
        "float96",
        "complex64",
        "complex128",
        "complex192",
        "timedelta64",
        "datetime64",
        "unicode_",
        "str_",
        "bool_",
        "bool8",
        "byte",
        "int8",
        "bytes0",
        "bytes_",
        "cdouble",
        "cfloat",
        "character",
        "clongdouble",
        "clongfloat",
        "complexfloating",
        "csingle",
        "double",
        "flexible",
        "floating",
        "half",
        "inexact",
        "int0",
        "longcomplex",
        "longdouble",
        "longfloat",
        "short",
        "signedinteger",
        "single",
        "singlecomplex",
        "str0",
        "ubyte",
        "uint",
        "uint0",
        "uintc",
        "uintp",
        "ulonglong",
        "unsignedinteger",
        "ushort",
        "void0",
    ]

    def _inferred_numpy_attribute(self, attrib):
        node = builder.extract_node(
            """
        import numpy.core.numerictypes as tested_module
        missing_type = tested_module.{:s}""".format(
                attrib
            )
        )
        return next(node.value.infer())

    def test_numpy_core_types(self):
        """
        Test that all defined types have ClassDef type.
        """
        for typ in self.all_types:
            with self.subTest(typ=typ):
                inferred = self._inferred_numpy_attribute(typ)
                self.assertIsInstance(inferred, nodes.ClassDef)

    def test_generic_types_have_methods(self):
        """
        Test that all generic derived types have specified methods
        """
        generic_methods = [
            "all",
            "any",
            "argmax",
            "argmin",
            "argsort",
            "astype",
            "base",
            "byteswap",
            "choose",
            "clip",
            "compress",
            "conj",
            "conjugate",
            "copy",
            "cumprod",
            "cumsum",
            "data",
            "diagonal",
            "dtype",
            "dump",
            "dumps",
            "fill",
            "flags",
            "flat",
            "flatten",
            "getfield",
            "imag",
            "item",
            "itemset",
            "itemsize",
            "max",
            "mean",
            "min",
            "nbytes",
            "ndim",
            "newbyteorder",
            "nonzero",
            "prod",
            "ptp",
            "put",
            "ravel",
            "real",
            "repeat",
            "reshape",
            "resize",
            "round",
            "searchsorted",
            "setfield",
            "setflags",
            "shape",
            "size",
            "sort",
            "squeeze",
            "std",
            "strides",
            "sum",
            "swapaxes",
            "take",
            "tobytes",
            "tofile",
            "tolist",
            "tostring",
            "trace",
            "transpose",
            "var",
            "view",
        ]

        for type_ in (
            "bool_",
            "bytes_",
            "character",
            "complex128",
            "complex192",
            "complex64",
            "complexfloating",
            "datetime64",
            "flexible",
            "float16",
            "float32",
            "float64",
            "float96",
            "floating",
            "generic",
            "inexact",
            "int16",
            "int32",
            "int32",
            "int64",
            "int8",
            "integer",
            "number",
            "signedinteger",
            "str_",
            "timedelta64",
            "uint16",
            "uint32",
            "uint32",
            "uint64",
            "uint8",
            "unsignedinteger",
            "void",
        ):
            with self.subTest(typ=type_):
                inferred = self._inferred_numpy_attribute(type_)
                for meth in generic_methods:
                    with self.subTest(meth=meth):
                        self.assertTrue(meth in {m.name for m in inferred.methods()})

    def test_generic_types_have_attributes(self):
        """
        Test that all generic derived types have specified attributes
        """
        generic_attr = [
            "base",
            "data",
            "dtype",
            "flags",
            "flat",
            "imag",
            "itemsize",
            "nbytes",
            "ndim",
            "real",
            "size",
            "strides",
        ]

        for type_ in (
            "bool_",
            "bytes_",
            "character",
            "complex128",
            "complex192",
            "complex64",
            "complexfloating",
            "datetime64",
            "flexible",
            "float16",
            "float32",
            "float64",
            "float96",
            "floating",
            "generic",
            "inexact",
            "int16",
            "int32",
            "int32",
            "int64",
            "int8",
            "integer",
            "number",
            "signedinteger",
            "str_",
            "timedelta64",
            "uint16",
            "uint32",
            "uint32",
            "uint64",
            "uint8",
            "unsignedinteger",
            "void",
        ):
            with self.subTest(typ=type_):
                inferred = self._inferred_numpy_attribute(type_)
                for attr in generic_attr:
                    with self.subTest(attr=attr):
                        self.assertNotEqual(len(inferred.getattr(attr)), 0)

    def test_number_types_have_unary_operators(self):
        """
        Test that number types have unary operators
        """
        unary_ops = ("__neg__",)

        for type_ in (
            "float64",
            "float96",
            "floating",
            "int16",
            "int32",
            "int32",
            "int64",
            "int8",
            "integer",
            "number",
            "signedinteger",
            "uint16",
            "uint32",
            "uint32",
            "uint64",
            "uint8",
            "unsignedinteger",
        ):
            with self.subTest(typ=type_):
                inferred = self._inferred_numpy_attribute(type_)
                for attr in unary_ops:
                    with self.subTest(attr=attr):
                        self.assertNotEqual(len(inferred.getattr(attr)), 0)

    def test_array_types_have_unary_operators(self):
        """
        Test that array types have unary operators
        """
        unary_ops = ("__neg__", "__invert__")

        for type_ in ("ndarray",):
            with self.subTest(typ=type_):
                inferred = self._inferred_numpy_attribute(type_)
                for attr in unary_ops:
                    with self.subTest(attr=attr):
                        self.assertNotEqual(len(inferred.getattr(attr)), 0)


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class NumpyBrainFunctionReturningArrayTest(SubTestWrapper):
    """
    Test that calls to numpy functions returning arrays are correctly inferred
    """
    numpy_functions = (("array", "[1, 2]"),
                       ("linspace", "1, 100"),
                       ('zeros_like', "[1, 2]"),
                       ('full_like', "[1, 2]", '4'),
                       ('empty_like', "[1, 2]"),
                       ('ones_like', "[1, 2]"),
                       ('logical_or', "[1, 2]", "[1, 2]"),
                       ('logical_xor', "[1, 2]", "[1, 2]"),
                       ('logical_and', "[1, 2]", "[1, 2]"),
                       ('dot', "[1, 2]", "[1, 2]"),
                       ('vdot', "[1, 2]", "[1, 2]"),
                       ('concatenate', "([1, 2], [1, 2])"),
                       ('inner', "[1, 2]", "[1, 2]"),
                       ('where', '[True, False]', "[1, 2]", "[2, 1]"),
                       ('sum', '[[1, 2], [2, 1]]', "axis=0")
                       )

    def _inferred_numpy_func_call(self, func_name, *func_args):
        node = builder.extract_node(
            """
        import numpy as np
        func = np.{:s}
        func({:s})
        """.format(
                func_name, ",".join(func_args)
            )
        )
        return node.infer()

    def test_numpy_function_calls_inferred_as_ndarray(self):
        """
        Test that some calls to numpy functions are inferred as numpy.ndarray
        """
        licit_array_types = ('.ndarray', 'numpy.core.records.recarray')
        for func_ in self.numpy_functions:
            with self.subTest(typ=func_):
                inferred_values = list(self._inferred_numpy_func_call(*func_))
                self.assertTrue(len(inferred_values) == 1,
                                msg="Too much inferred value for {:s}".format(func_[0]))
                self.assertTrue(inferred_values[-1].pytype() in licit_array_types,
                                msg="Illicit type for {:s} ({})".format(func_[0], inferred_values[-1].pytype()))

if __name__ == "__main__":
    unittest.main()
