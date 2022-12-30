# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import pytest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder

parametrize = pytest.mark.parametrize("alias_import", [True, False])


@pytest.mark.skipif(HAS_NUMPY is False, reason="This test requires the numpy library.")
class TestBrainNumpyMa:
    """
    Test the numpy ma brain module
    """

    def _assert_maskedarray(self, code):
        node = builder.extract_node(code)
        cls_node = node.inferred()[0]
        assert cls_node.pytype() == "numpy.ma.core.MaskedArray"

    @parametrize
    def test_numpy_ma_masked_where_returns_maskedarray(self, alias_import):
        """
        Test that calls to numpy ma masked_where returns a MaskedArray object.

        The "masked_where" node is an Attribute
        """
        import_str = (
            "import numpy as np"
            if alias_import
            else "from numpy.ma import masked_where"
        )
        func_call = "np.ma.masked_where" if alias_import else "masked_where"

        src = f"""
        {import_str}
        data = np.ndarray((1,2))
        {func_call}([1, 0, 0], data)
        """
        self._assert_maskedarray(src)

    @parametrize
    def test_numpy_ma_masked_invalid_returns_maskedarray(self, alias_import):
        """
        Test that calls to numpy ma masked_invalid returns a MaskedArray object.

        The "masked_invalid" node is an Attribute
        """
        import_str = (
            "import numpy as np"
            if alias_import
            else "from numpy.ma import masked_invalid"
        )
        func_call = "np.ma.masked_invalid" if alias_import else "masked_invalid"

        src = f"""
        {import_str}
        data = np.ndarray((1,2))
        {func_call}([1, 0, 0], data)
        """
        self._assert_maskedarray(src)
