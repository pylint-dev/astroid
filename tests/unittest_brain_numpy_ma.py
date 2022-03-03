# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/graphs/contributors
import pytest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder


@pytest.mark.skipif(HAS_NUMPY is False, reason="This test requires the numpy library.")
class TestBrainNumpyMa:
    """
    Test the numpy ma brain module
    """

    @staticmethod
    def test_numpy_ma_masked_where_returns_maskedarray():
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
        assert cls_node.pytype() == "numpy.ma.core.MaskedArray"

    @staticmethod
    def test_numpy_ma_masked_where_returns_maskedarray_bis():
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
        assert cls_node.pytype() == "numpy.ma.core.MaskedArray"
