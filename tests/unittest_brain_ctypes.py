import pytest
from astroid import extract_node


# The parameters of the test define a mapping between the ctypes redefined types 
# and the builtin types that the "value" member holds
@pytest.mark.parametrize("c_type,builtin_type", [("c_bool", 'bool'), 
                                                 ("c_wchar", 'str'),
                                                 pytest.param("c_buffer", 'bytes', marks=pytest.mark.xfail(reason="c_buffer is Uninferable but for now we do not know why")),  
                                                 ("c_char", 'bytes'),
                                                 ("c_double", 'float'),
                                                 ("c_float", 'float'),
                                                 ("c_longdouble", 'float'),
                                                 ("c_byte", 'int'),
                                                 ("c_int", 'int'),
                                                 ("c_int16", 'int'),
                                                 ("c_int32", 'int'),
                                                 ("c_int64", 'int'),
                                                 ("c_int8", 'int'),
                                                 ("c_long", 'int'),
                                                 ("c_longlong", 'int'),
                                                 ("c_short", 'int'),
                                                 ("c_size_t", 'int'),
                                                 ("c_ssize_t", 'int'),
                                                 ("c_ubyte", 'int'),
                                                 ("c_uint", 'int'),
                                                 ("c_uint16", 'int'),
                                                 ("c_uint32", 'int'),
                                                 ("c_uint64", 'int'),
                                                 ("c_uint8", 'int'),
                                                 ("c_ulong", 'int'),
                                                 ("c_ulonglong", 'int'),
                                                 ("c_ushort", 'int')])
def test_ctypes_redefined_types(c_type, builtin_type):
    """
    Test that the value member of each ctypes redefined types is correct
    """
    src = f"""
    import ctypes
    x=ctypes.{c_type}("toto")
    x.value
    """
    node=extract_node(src)
    ctypes_inst = next(node.expr.infer())
    val_class = ctypes_inst.getattr('value')[0]
    assert val_class.display_type() == "Class"
    assert val_class.root().name == '_ctypes' 

    node_inf = node.inferred()[0]
    assert node_inf.pytype() == f'builtins.{builtin_type}'
