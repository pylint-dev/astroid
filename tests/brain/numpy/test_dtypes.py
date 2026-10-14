# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

try:
    import numpy  # pylint: disable=unused-import
    import numpy.dtypes

    HAS_NUMPY_DTYPES = True
except ImportError:
    HAS_NUMPY_DTYPES = False

from astroid import builder, nodes
from astroid.bases import Instance
from astroid.brain.brain_numpy_dtypes import DTYPE_CLASS_NAMES


@pytest.mark.skipif(
    not HAS_NUMPY_DTYPES, reason="This test requires numpy 1.25+ (numpy.dtypes)."
)
class TestBrainNumpyDtypes:
    """Test the numpy.dtypes brain module."""

    @pytest.mark.parametrize("name", DTYPE_CLASS_NAMES)
    def test_dtype_class_is_inferred_as_a_class(self, name: str) -> None:
        node = builder.extract_node(f"""
        import numpy as np
        np.dtypes.{name} #@
        """)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.ClassDef)
        assert inferred[0].name == name
        assert "dtype" in [base.name for base in inferred[0].ancestors()]

    def test_dtype_class_from_import(self) -> None:
        node = builder.extract_node("""
        from numpy.dtypes import StringDType
        StringDType() #@
        """)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], Instance)
        assert inferred[0].pytype() == "numpy.dtypes.StringDType"

    def test_brain_covers_every_class_numpy_exposes(self) -> None:
        """Every DType class the installed numpy puts in ``numpy.dtypes`` is covered.

        ``__all__`` also lists functions (``register_dlpack_dtype`` in 2.5), so
        only classes are compared.
        """
        exposed = {
            name
            for name in numpy.dtypes.__all__
            if isinstance(getattr(numpy.dtypes, name), type)
        }
        assert not exposed - set(DTYPE_CLASS_NAMES)

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("Float64DType", []),
            ("ObjectDType", []),
            ("BytesDType", ["size"]),
            ("StrDType", ["size"]),
            ("VoidDType", ["length"]),
            ("DateTime64DType", ["unit"]),
            ("TimeDelta64DType", ["unit"]),
        ],
    )
    def test_dtype_class_has_its_own_constructor(
        self, name: str, expected: list[str]
    ) -> None:
        """The DType classes do not inherit ``numpy.dtype(obj, align, copy)``."""
        node = builder.extract_node(f"""
        import numpy as np
        np.dtypes.{name} #@
        """)
        init = next(node.infer()).local_attr("__init__")[0]
        assert init.parent.name == name
        positional = [arg.name for arg in init.args.posonlyargs + init.args.args]
        assert positional == ["self", *expected]
        assert not init.args.kwonlyargs
        if expected:
            assert [arg.name for arg in init.args.posonlyargs] == ["self", *expected]

    def test_string_dtype_constructor_is_keyword_only(self) -> None:
        node = builder.extract_node("""
        import numpy as np
        np.dtypes.StringDType #@
        """)
        init = next(node.infer()).local_attr("__init__")[0]
        assert [arg.name for arg in init.args.kwonlyargs] == ["na_object", "coerce"]
        assert [arg.name for arg in init.args.args] == ["self"]

    @pytest.mark.parametrize("attribute", ["na_object", "coerce"])
    def test_string_dtype_instance_attributes_are_inferred(
        self, attribute: str
    ) -> None:
        node = builder.extract_node(f"""
        import numpy as np
        np.dtypes.StringDType(na_object=None).{attribute} #@
        """)
        assert node.inferred()
