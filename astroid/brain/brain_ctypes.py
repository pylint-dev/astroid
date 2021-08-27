"""
Astroid hooks for ctypes module.

Inside the ctypes module, the value class is defined inside
the C coded module _ctypes.
Thus astroid doesn't know that the value member is a bultin type
among float, int, bytes or str.
"""
from astroid.util import Uninferable
from astroid.context import InferenceContext
from astroid.exceptions import InferenceError
from astroid.inference_tip import inference_tip
from astroid.builder import extract_node
from astroid.manager import AstroidManager
from astroid.nodes.node_classes import Attribute, Name, NodeNG
from astroid.bases import Instance


def looks_like_value_attribute(node: NodeNG) -> bool:
    """
    Returns True if the node is a "value" attribute

    :note: it would be better to have a test that is more strict 
           in order to target specifically ctypes members but for
           now no solution arised.
    """
    return (isinstance(node, Attribute) and node.attrname == "value")


def infer_value_attribute(node: Attribute, context: InferenceContext = None) -> Instance:
    """
    Infer the value attribute of a type in the ctypes module
    """
    c_class_to_type = {
        "c_bool": 'bool',
        "c_wchar": 'str',
        "c_buffer": 'bytes',
        "c_char": 'bytes',
        "c_double": 'float',
        "c_float": 'float',
        "c_longdouble": 'float',
        "c_byte": 'int',
        "c_int": 'int',
        "c_int16": 'int',
        "c_int32": 'int',
        "c_int64": 'int',
        "c_int8": 'int',
        "c_long": 'int',
        "c_longlong": 'int',
        "c_short": 'int',
        "c_size_t": 'int',
        "c_ssize_t": 'int',
        "c_ubyte": 'int',
        "c_uint": 'int',
        "c_uint16": 'int',
        "c_uint32": 'int',
        "c_uint64": 'int',
        "c_uint8": 'int',
        "c_ulong": 'int',
        "c_ulonglong": 'int',
        "c_ushort": 'int',
    }
    owner = next(node.expr.infer()).pytype()
    if owner is Uninferable or not owner.startswith('ctypes.c_'):
        raise InferenceError(node=node, context=context)
    c_class = owner.split('.')[-1]
    builtin_type = c_class_to_type[c_class]
    new_node = extract_node(f"""
        {builtin_type}(0.)
    """)
    return new_node.infer(context=context)


AstroidManager().register_transform(
    Attribute,
    inference_tip(infer_value_attribute),
    looks_like_value_attribute
)
