# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for the PyQT library."""

from astroid import nodes, parse
from astroid.brain.helpers import register_module_extender
from astroid.builder import AstroidBuilder
from astroid.manager import AstroidManager


def _looks_like_signal(node, signal_name="pyqtSignal"):
    if "__class__" in node.instance_attrs:
        try:
            cls = node.instance_attrs["__class__"][0]
            return cls.name == signal_name
        except AttributeError:
            # return False if the cls does not have a name attribute
            pass
    return False


def transform_pyqt_signal(node):
    module = parse(
        """
    class pyqtSignal(object):
        def connect(self, slot, type=None, no_receiver_check=False):
            pass
        def disconnect(self, slot):
            pass
        def emit(self, *args):
            pass
    """
    )
    signal_cls = module["pyqtSignal"]
    node.instance_attrs["emit"] = signal_cls["emit"]
    node.instance_attrs["disconnect"] = signal_cls["disconnect"]
    node.instance_attrs["connect"] = signal_cls["connect"]


def transform_pyside_signal(node):
    module = parse(
        """
    class NotPySideSignal(object):
        def connect(self, receiver, type=None):
            pass
        def disconnect(self, receiver):
            pass
        def emit(self, *args):
            pass
    """
    )
    signal_cls = module["NotPySideSignal"]
    node.instance_attrs["connect"] = signal_cls["connect"]
    node.instance_attrs["disconnect"] = signal_cls["disconnect"]
    node.instance_attrs["emit"] = signal_cls["emit"]


def pyqt4_qtcore_transform():
    return AstroidBuilder(AstroidManager()).string_build(
        """

def SIGNAL(signal_name): pass

class QObject(object):
    def emit(self, signal): pass
"""
    )


register_module_extender(AstroidManager(), "PyQt4.QtCore", pyqt4_qtcore_transform)
AstroidManager().register_transform(
    nodes.FunctionDef, transform_pyqt_signal, _looks_like_signal
)
AstroidManager().register_transform(
    nodes.ClassDef,
    transform_pyside_signal,
    lambda node: node.qname() in {"PySide.QtCore.Signal", "PySide2.QtCore.Signal"},
)
