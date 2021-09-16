# Copyright (c) 2021 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
import unittest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class BrainNumpyMaTest(unittest.TestCase):
    """
    Test the numpy ma brain module
    """

    def test_numpy_ma_masked_where_returns_maskedarray(self):
        """
        Test that calls to numpy ma masked_where returns a MaskedArray object.

        The "masked_where" node is an Attribute
        """
        src = """
        import numpy as np
        data = np.ndarray((1,2))
        np.ma.masked_where([1, 0, 0], data)
        """
        node = builder.extract_node(src)
        cls_node = node.inferred()[0]
        self.assertEqual(cls_node.pytype(), "numpy.ma.core.MaskedArray")

    def test_numpy_ma_masked_where_returns_maskedarray_bis(self):
        """
        Test that calls to numpy ma masked_where returns a MaskedArray object

        The "masked_where" node is a Name
        """
        src = """
        from numpy.ma import masked_where
        data = np.ndarray((1,2))
        masked_where([1, 0, 0], data)
        """
        node = builder.extract_node(src)
        cls_node = node.inferred()[0]
        self.assertEqual(cls_node.pytype(), "numpy.ma.core.MaskedArray")


if __name__ == "__main__":
    unittest.main()
