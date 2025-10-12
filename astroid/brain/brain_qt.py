# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for the Qt Python bindings (PyQt/PySide)."""

from astroid import nodes
from astroid.brain.helpers import register_module_extender
from astroid.builder import AstroidBuilder, parse
from astroid.manager import AstroidManager

_PYQT_ROOTS = {"PyQt5", "PyQt6"}

_PYQT_SIGNAL_QNAMES = {
    "PyQt5.QtCore.pyqtSignal",
    "PyQt6.QtCore.pyqtSignal",
}

_PYSIDE_ROOTS = {"PySide", "PySide2", "PySide6"}

_PYSIDE_SIGNAL_QNAMES = {
    "PySide.QtCore.Signal",
    "PySide2.QtCore.Signal",
    "PySide6.QtCore.Signal",
}

_PYQT_SIGNAL_TEMPLATE = parse(
    """
_UNSET = object()

class _PyQtSignalTemplate(object):
    def connect(self, slot, type=None, no_receiver_check=False):
        pass
    def disconnect(self, slot=_UNSET):
        pass
    def emit(self, *args):
        pass
"""
)["_PyQtSignalTemplate"]

_PYSIDE_SIGNAL_TEMPLATE = parse(
    """
class _PySideSignalTemplate(object):
    def connect(self, receiver, type=None):
        pass
    def disconnect(self, receiver=None):
        pass
    def emit(self, *args):
        pass
"""
)["_PySideSignalTemplate"]


def _attach_signal_instance_attrs(node: nodes.NodeNG, template: nodes.ClassDef) -> None:
    node.instance_attrs["connect"] = [template["connect"]]
    node.instance_attrs["disconnect"] = [template["disconnect"]]
    node.instance_attrs["emit"] = [template["emit"]]


def _transform_signal_on_functiondef(node: nodes.FunctionDef) -> None:
    root = node.qname().partition(".")[0]
    if root in _PYQT_ROOTS:
        template = _PYQT_SIGNAL_TEMPLATE
    else:
        template = _PYSIDE_SIGNAL_TEMPLATE  # pragma: no cover
    _attach_signal_instance_attrs(node, template)


def _transform_pyqt_signal_class(node: nodes.ClassDef) -> None:
    _attach_signal_instance_attrs(node, _PYQT_SIGNAL_TEMPLATE)


def _transform_pyside_signal_class(node: nodes.ClassDef) -> None:
    _attach_signal_instance_attrs(node, _PYSIDE_SIGNAL_TEMPLATE)  # pragma: no cover


def _is_pyside_signal_classdef(n: nodes.ClassDef) -> bool:
    return n.qname() in _PYSIDE_SIGNAL_QNAMES


def _is_pyqt_signal_classdef(n: nodes.ClassDef) -> bool:
    return n.qname() in _PYQT_SIGNAL_QNAMES


def _is_qt_signal_functiondef(n: nodes.FunctionDef) -> bool:
    root = n.qname().partition(".")[0]
    if root not in _PYQT_ROOTS | _PYSIDE_ROOTS:
        return False

    klasses = n.instance_attrs.get("__class__", [])
    for cls in klasses:
        name = getattr(cls, "name", "")
        if name == "pyqtSignal" and root in _PYQT_ROOTS:
            return True
        if name == "Signal" and root in _PYSIDE_ROOTS:
            return True  # pragma: no cover
        qname = getattr(cls, "qname", None)
        if callable(qname):
            qualified = qname()
            if qualified and qualified.rsplit(".", 1)[-1] == "Signal":
                return True  # pragma: no cover
    return False


def _pyqt4_qtcore_transform():
    return AstroidBuilder(AstroidManager()).string_build(
        """

def SIGNAL(signal_name): pass

class QObject(object):
    def emit(self, signal): pass
"""
    )


def register(manager: AstroidManager) -> None:
    # PyQt4 legacy shim
    register_module_extender(manager, "PyQt4.QtCore", _pyqt4_qtcore_transform)

    # PyQt function style
    manager.register_transform(
        nodes.FunctionDef, _transform_signal_on_functiondef, _is_qt_signal_functiondef
    )

    # PyQt class style
    manager.register_transform(
        nodes.ClassDef, _transform_pyqt_signal_class, _is_pyqt_signal_classdef
    )

    # PySide class style
    manager.register_transform(
        nodes.ClassDef, _transform_pyside_signal_class, _is_pyside_signal_classdef
    )
