# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import unittest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder, nodes
from astroid.brain.brain_numpy_utils import (
    NUMPY_VERSION_TYPE_HINTS_SUPPORT,
    numpy_supports_type_hints,
)


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class NumpyBrainNdarrayTest(unittest.TestCase):
    """Test that calls to numpy functions returning arrays are correctly inferred."""

    ndarray_returning_ndarray_methods = (
        "__abs__",
        "__add__",
        "__and__",
        "__array__",
        "__array_wrap__",
        "__copy__",
        "__deepcopy__",
        "__eq__",
        "__floordiv__",
        "__ge__",
        "__gt__",
        "__iadd__",
        "__iand__",
        "__ifloordiv__",
        "__ilshift__",
        "__imod__",
        "__imul__",
        "__invert__",
        "__ior__",
        "__ipow__",
        "__irshift__",
        "__isub__",
        "__itruediv__",
        "__ixor__",
        "__le__",
        "__lshift__",
        "__lt__",
        "__matmul__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__neg__",
        "__or__",
        "__pos__",
        "__pow__",
        "__rshift__",
        "__sub__",
        "__truediv__",
        "__xor__",
        "all",
        "any",
        "argmax",
        "argmin",
        "argpartition",
        "argsort",
        "astype",
        "byteswap",
        "choose",
        "clip",
        "compress",
        "conj",
        "conjugate",
        "copy",
        "cumprod",
        "cumsum",
        "diagonal",
        "dot",
        "flatten",
        "getfield",
        "max",
        "mean",
        "min",
        "newbyteorder",
        "prod",
        "ptp",
        "ravel",
        "repeat",
        "reshape",
        "round",
        "searchsorted",
        "squeeze",
        "std",
        "sum",
        "swapaxes",
        "take",
        "trace",
        "transpose",
        "var",
        "view",
    )

    def _inferred_ndarray_method_call(self, func_name):
        node = builder.extract_node(
            f"""
        import numpy as np
        test_array = np.ndarray((2, 2))
        test_array.{func_name:s}()
        """
        )
        return node.infer()

    def _inferred_ndarray_attribute(self, attr_name):
        node = builder.extract_node(
            f"""
        import numpy as np
        test_array = np.ndarray((2, 2))
        test_array.{attr_name:s}
        """
        )
        return node.infer()

    def test_numpy_function_calls_inferred_as_ndarray(self):
        """Test that some calls to numpy functions are inferred as numpy.ndarray."""
        licit_array_types = ".ndarray"
        for func_ in self.ndarray_returning_ndarray_methods:
            with self.subTest(typ=func_):
                inferred_values = list(self._inferred_ndarray_method_call(func_))
                self.assertTrue(
                    len(inferred_values) == 1,
                    msg=f"Too much inferred value for {func_:s}",
                )
                self.assertTrue(
                    inferred_values[-1].pytype() in licit_array_types,
                    msg=f"Illicit type for {func_:s} ({inferred_values[-1].pytype()})",
                )

    def test_numpy_ndarray_attribute_inferred_as_ndarray(self):
        """Test that some numpy ndarray attributes are inferred as numpy.ndarray."""
        licit_array_types = ".ndarray"
        for attr_ in ("real", "imag", "shape", "T"):
            with self.subTest(typ=attr_):
                inferred_values = list(self._inferred_ndarray_attribute(attr_))
                self.assertTrue(
                    len(inferred_values) == 1,
                    msg=f"Too much inferred value for {attr_:s}",
                )
                self.assertTrue(
                    inferred_values[-1].pytype() in licit_array_types,
                    msg=f"Illicit type for {attr_:s} ({inferred_values[-1].pytype()})",
                )

    @unittest.skipUnless(
        HAS_NUMPY and numpy_supports_type_hints(),
        f"This test requires the numpy library with a version above {NUMPY_VERSION_TYPE_HINTS_SUPPORT}",
    )
    def test_numpy_ndarray_class_support_type_indexing(self):
        """Test that numpy ndarray class can be subscripted (type hints)."""
        src = """
        import numpy as np
        np.ndarray[int]
        """
        node = builder.extract_node(src)
        cls_node = node.inferred()[0]
        self.assertIsInstance(cls_node, nodes.ClassDef)
        self.assertEqual(cls_node.name, "ndarray")
