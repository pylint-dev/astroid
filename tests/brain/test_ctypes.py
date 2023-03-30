# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import sys

import pytest

from astroid import extract_node, nodes

pytestmark = pytest.mark.skipif(
    hasattr(sys, "pypy_version_info"),
    reason="pypy has its own implementation of _ctypes module which is different "
    "from the one of cpython",
)


# The parameters of the test define a mapping between the ctypes redefined types
# and the builtin types that the "value" member holds
@pytest.mark.parametrize(
    "c_type,builtin_type,type_code",
    [
        ("c_bool", "bool", "?"),
        ("c_byte", "int", "b"),
        ("c_char", "bytes", "c"),
        ("c_double", "float", "d"),
        pytest.param(
            "c_buffer",
            "bytes",
            "<class 'ctypes.c_char'>",
            marks=pytest.mark.xfail(
                reason="c_buffer is Uninferable but for now we do not know why"
            ),
        ),
        ("c_float", "float", "f"),
        ("c_int", "int", "i"),
        ("c_int16", "int", "h"),
        ("c_int32", "int", "i"),
        ("c_int64", "int", "l"),
        ("c_int8", "int", "b"),
        ("c_long", "int", "l"),
        ("c_longdouble", "float", "g"),
        ("c_longlong", "int", "l"),
        ("c_short", "int", "h"),
        ("c_size_t", "int", "L"),
        ("c_ssize_t", "int", "l"),
        ("c_ubyte", "int", "B"),
        ("c_uint", "int", "I"),
        ("c_uint16", "int", "H"),
        ("c_uint32", "int", "I"),
        ("c_uint64", "int", "L"),
        ("c_uint8", "int", "B"),
        ("c_ulong", "int", "L"),
        ("c_ulonglong", "int", "L"),
        ("c_ushort", "int", "H"),
        ("c_wchar", "str", "u"),
    ],
)
def test_ctypes_redefined_types_members(c_type, builtin_type, type_code):
    """Test that the "value" and "_type_" member of each redefined types are
    correct.
    """
    src = f"""
    import ctypes
    x=ctypes.{c_type}("toto")
    x.value
    """
    node = extract_node(src)
    assert isinstance(node, nodes.NodeNG)
    node_inf = node.inferred()[0]
    assert node_inf.pytype() == f"builtins.{builtin_type}"

    src = f"""
    import ctypes
    x=ctypes.{c_type}("toto")
    x._type_
    """
    node = extract_node(src)
    assert isinstance(node, nodes.NodeNG)
    node_inf = node.inferred()[0]
    assert isinstance(node_inf, nodes.Const)
    assert node_inf.value == type_code


def test_cdata_member_access() -> None:
    """
    Test that the base members are still accessible. Each redefined ctypes type
    inherits from _SimpleCData which itself inherits from _CData. Checks that
    _CData members are accessible.
    """
    src = """
    import ctypes
    x=ctypes.c_float(1.0)
    x._objects
    """
    node = extract_node(src)
    assert isinstance(node, nodes.NodeNG)
    node_inf = node.inferred()[0]
    assert node_inf.display_type() == "Class"
    assert node_inf.qname() == "_ctypes._SimpleCData._objects"


def test_other_ctypes_member_untouched() -> None:
    """
    Test that other ctypes members, which are not touched by the brain, are correctly
    inferred.
    """
    src = """
    import ctypes
    ctypes.ARRAY(3, 2)
    """
    node = extract_node(src)
    assert isinstance(node, nodes.NodeNG)
    node_inf = node.inferred()[0]
    assert isinstance(node_inf, nodes.Const)
    assert node_inf.value == 6
