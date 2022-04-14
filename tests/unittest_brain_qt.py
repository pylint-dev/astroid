# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from importlib.util import find_spec

import pytest

from astroid import Uninferable, extract_node
from astroid.bases import UnboundMethod
from astroid.manager import AstroidManager
from astroid.nodes import FunctionDef

HAS_PYQT6 = find_spec("PyQt6")


@pytest.mark.skipif(HAS_PYQT6 is None, reason="This test requires the PyQt6 library.")
class TestBrainQt:
    @staticmethod
    def test_value_of_lambda_instance_attrs_is_list():
        """Regression test for https://github.com/PyCQA/pylint/issues/6221

        A crash occurred in pylint when a nodes.FunctionDef was iterated directly,
        giving items like "self" instead of iterating a one-element list containing
        the wanted nodes.FunctionDef.
        """
        src = """
        from PyQt6 import QtPrintSupport as printsupport
        printsupport.QPrintPreviewDialog.paintRequested  #@
        """
        AstroidManager.brain["extension_package_whitelist"] = {"PyQt6.QtPrintSupport"}
        node = extract_node(src)
        attribute_node = node.inferred()[0]
        if attribute_node is Uninferable:
            pytest.skip("PyQt6 C bindings may not be installed?")
        assert isinstance(attribute_node, UnboundMethod)
        # scoped_nodes.Lambda.instance_attrs is typed as Dict[str, List[NodeNG]]
        assert isinstance(attribute_node.instance_attrs["connect"][0], FunctionDef)
