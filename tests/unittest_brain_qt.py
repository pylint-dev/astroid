# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from importlib.util import find_spec

import pytest

from astroid import Uninferable, extract_node
from astroid.bases import UnboundMethod
from astroid.manager import AstroidManager
from astroid.nodes import FunctionDef

HAS_PYQT5 = find_spec("PyQt5")
HAS_PYSIDE2 = find_spec("PySide2")
HAS_PYQT6 = find_spec("PyQt6")
HAS_PYSIDE6 = find_spec("PySide6")


@pytest.mark.skipif(
    HAS_PYSIDE6 is None,
    reason="These tests require the PyQt6 library.",
)
class TestBrainQt:
    AstroidManager.brain["extension_package_whitelist"] = {
        "PyQt6",
    }

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
        node = extract_node(src)
        attribute_node = node.inferred()[0]
        if attribute_node is Uninferable:
            pytest.skip("PyQt6 C bindings may not be installed?")
        assert isinstance(attribute_node, UnboundMethod)
        # scoped_nodes.Lambda.instance_attrs is typed as Dict[str, List[NodeNG]]
        assert isinstance(attribute_node.instance_attrs["connect"][0], FunctionDef)

    @staticmethod
    def test_implicit_parameters() -> None:
        """Regression test for https://github.com/PyCQA/pylint/issues/6464"""
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

        See https://github.com/PyCQA/astroid/pull/1531#issuecomment-1111963792
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


@pytest.mark.skipif(
    any(
        (
            HAS_PYQT5 is None,
            HAS_PYSIDE2 is None,
            HAS_PYQT6 is None,
            HAS_PYSIDE6 is None,
        ),
    ),
    reason="These tests require the PyQt5, PySide2, PyQt6, and PySide6 libraries.",
)
class TestBrainQt_ConnectSignalMember:
    AstroidManager.brain["extension_package_whitelist"] = {
        "PyQt5",
        "PySide2",
        "PyQt6",
        "PySide6",
    }

    @staticmethod
    @pytest.mark.parametrize("qt_binding", ["PyQt5", "PySide2", "PyQt6", "PySide6"])
    def test_connect_signal_detected(
        qt_binding: str,
    ) -> None:
        """Test signals have .connect() signal.

        This is a regression test for:
            - https://github.com/PyCQA/pylint/issues/4040
            - https://github.com/PyCQA/pylint/issues/5378

        See PR: https://github.com/PyCQA/astroid/pull/1654

        Args:
            qt_binding(str): Python Qt binding (one of PyQt5, PySide2, PyQt6, or PySide6)
        """
        if qt_binding == "PyQt5":
            src = """
            from PyQt5 import QtWidgets
            app = QtWidgets.QApplication([])
            app.focusChanged  #@
            """
        elif qt_binding == "PySide2":
            src = """
            from PySide2 import QtWidgets
            app = QtWidgets.QApplication([])
            app.focusChanged  #@
            """
        elif qt_binding == "PyQt6":
            src = """
            from PyQt6 import QtWidgets
            app = QtWidgets.QApplication([])
            app.focusChanged  #@
            """
        elif qt_binding == "PySide6":
            src = """
            from PySide6 import QtWidgets
            app = QtWidgets.QApplication([])
            app.focusChanged  #@
            """
        else:
            pytest.skip(f"{qt_binding} is not a Python Qt library.")

        node = extract_node(src)
        attribute_node = node.inferred()[0]
        if attribute_node is Uninferable:
            pytest.skip(f"{qt_binding} C bindings may not be installed?")
        assert isinstance(attribute_node.instance_attrs["connect"][0], FunctionDef)
