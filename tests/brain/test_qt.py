# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from importlib.util import find_spec

import pytest

from astroid import Uninferable, extract_node
from astroid.bases import UnboundMethod
from astroid.const import PY312_PLUS
from astroid.manager import AstroidManager
from astroid.nodes import FunctionDef

HAS_PYQT6 = find_spec("PyQt6")


@pytest.mark.skipif(HAS_PYQT6 is None, reason="These tests require the PyQt6 library.")
# TODO: enable for Python 3.12 as soon as PyQt6 release is compatible
@pytest.mark.skipif(PY312_PLUS, reason="This test was segfaulting with Python 3.12.")
class TestBrainQt:
    AstroidManager.brain["extension_package_whitelist"] = {"PyQt6"}  # noqa: RUF012

    @staticmethod
    def test_value_of_lambda_instance_attrs_is_list():
        """Regression test for https://github.com/pylint-dev/pylint/issues/6221.

        A crash occurred in pylint when a nodes.FunctionDef was iterated directly,
        giving items like "self" instead of iterating a one-element list containing
        the wanted nodes.FunctionDef.
        """
        src = """
        from PyQt6 import QtPrintSupport as printsupport
        printsupport.QPrintPreviewDialog.paintRequested  #@
        """
        node = extract_node(src)
        attribute_node = node.inferred()[0]
        if attribute_node is Uninferable:
            pytest.skip("PyQt6 C bindings may not be installed?")
        assert isinstance(attribute_node, UnboundMethod)
        # scoped_nodes.Lambda.instance_attrs is typed as Dict[str, List[NodeNG]]
        assert isinstance(attribute_node.instance_attrs["connect"][0], FunctionDef)

    @staticmethod
    def test_implicit_parameters() -> None:
        """Regression test for https://github.com/pylint-dev/pylint/issues/6464."""
        src = """
        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect  #@
        """
        node = extract_node(src)
        attribute_node = node.inferred()[0]
        if attribute_node is Uninferable:
            pytest.skip("PyQt6 C bindings may not be installed?")
        assert isinstance(attribute_node, FunctionDef)
        assert attribute_node.implicit_parameters() == 1

    @staticmethod
    def test_slot_disconnect_no_args() -> None:
        """Test calling .disconnect() on a signal.

        See https://github.com/pylint-dev/astroid/pull/1531#issuecomment-1111963792
        """
        src = """
        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.timeout.disconnect  #@
        """
        node = extract_node(src)
        attribute_node = node.inferred()[0]
        if attribute_node is Uninferable:
            pytest.skip("PyQt6 C bindings may not be installed?")
        assert isinstance(attribute_node, FunctionDef)
        assert attribute_node.args.defaults
