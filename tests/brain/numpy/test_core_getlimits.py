# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

try:
    import numpy

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder, nodes
from astroid.bases import Instance
from astroid.brain.brain_numpy_core_getlimits import (
    FINFO_CONSTANTS,
    _add_finfo_constants,
)


def test_finfo_constants_defined_in_source_are_kept() -> None:
    """NumPy before 2.4 assigns some constants in Python: they are left alone."""
    finfo = builder.extract_node("""
    class finfo:
        def _init(self, dtype):
            self.eps = 1.0

        @property
        def smallest_normal(self):
            return 2.0
    """)
    eps = finfo.instance_attrs["eps"]
    _add_finfo_constants(finfo)
    assert finfo.instance_attrs["eps"] == eps
    assert "smallest_normal" not in finfo.instance_attrs
    for name in set(FINFO_CONSTANTS) - {"eps", "smallest_normal"}:
        assert isinstance(finfo.instance_attrs[name][0], nodes.EmptyNode)


@pytest.mark.skipif(not HAS_NUMPY, reason="This test requires the numpy library.")
class TestBrainNumpyCoreGetlimits:
    """Test the numpy getlimits brain module."""

    @pytest.mark.parametrize("name", FINFO_CONSTANTS)
    def test_finfo_constant_is_known(self, name: str) -> None:
        node = builder.extract_node(f"""
        import numpy as np
        np.finfo(np.float32).{name} #@
        """)
        finfo = node.expr.inferred()
        assert len(finfo) == 1
        assert isinstance(finfo[0], Instance)
        assert finfo[0].getattr(name)

    @pytest.mark.skipif(
        HAS_NUMPY and numpy.lib.NumpyVersion(numpy.__version__) < "2.4.0",
        reason="NumPy sets the finfo constants in C since 2.4.",
    )
    def test_brain_covers_every_constant_numpy_sets(self) -> None:
        """The public attributes of a finfo instance are known to astroid."""
        node = builder.extract_node("""
        import numpy as np
        np.finfo(np.float64) #@
        """)
        finfo = node.inferred()[0]
        for name in vars(numpy.finfo(numpy.float64)):
            if not name.startswith("_"):
                assert finfo.getattr(name), name
