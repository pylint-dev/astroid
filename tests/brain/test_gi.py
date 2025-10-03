# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import warnings
from importlib.util import find_spec

import pytest

from astroid import Uninferable, extract_node
from astroid.bases import BoundMethod
from astroid.manager import AstroidManager

HAS_GI = find_spec("gi")


@pytest.mark.skipif(HAS_GI is None, reason="These tests require the gi library.")
class TestBrainGi:
    AstroidManager.brain["extension_package_whitelist"] = {"gi"}  # noqa: RUF012

    @staticmethod
    def test_import() -> None:
        """Regression test for https://github.com/pylint-dev/astroid/issues/2190"""
        src = """
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk

        cell = Gtk.CellRendererText()
        cell.props.xalign = 1.0

        Gtk.Builder().connect_signals
        """
        with warnings.catch_warnings():
            # gi uses pkgutil.get_loader
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            node = extract_node(src)
        attribute_node = node.inferred()[0]
        if attribute_node is Uninferable:
            pytest.skip("Gtk3 may not be installed?")
        assert isinstance(attribute_node, BoundMethod)
