# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder


@pytest.mark.skipif(HAS_NUMPY is False, reason="This test requires the numpy library.")
class TestBrainNumpyMa:
    """Test the numpy ma brain module."""

    def _assert_maskedarray(self, code):
        node = builder.extract_node(code)
        cls_node = node.inferred()[0]
        assert cls_node.pytype() == "numpy.ma.core.MaskedArray"

    @pytest.mark.parametrize("alias_import", [True, False])
    @pytest.mark.parametrize("ma_function", ["masked_invalid", "masked_where"])
    def test_numpy_ma_returns_maskedarray(self, alias_import, ma_function):
        """
        Test that calls to numpy ma functions return a MaskedArray object.

        The `ma_function` node is an Attribute or a Name
        """
        import_str = (
            "import numpy as np"
            if alias_import
            else f"from numpy.ma import {ma_function}"
        )
        func = f"np.ma.{ma_function}" if alias_import else ma_function

        src = f"""
        {import_str}
        data = np.ndarray((1,2))
        {func}([1, 0, 0], data)
        """
        self._assert_maskedarray(src)
