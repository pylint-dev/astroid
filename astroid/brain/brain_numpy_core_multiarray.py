# Copyright (c) 2018-2019 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy.core.multiarray module."""

import functools
import astroid


def numpy_core_multiarray_transform():
    return astroid.parse(
        """
    # different functions defined in multiarray.py
    def inner(a, b):
        return numpy.ndarray([0, 0])

    def vdot(a, b):
        return numpy.ndarray([0, 0])
        """
    )


astroid.register_module_extender(
    astroid.MANAGER, "numpy.core.multiarray", numpy_core_multiarray_transform
)

def infer_numpy_core_multiarray_array(node, context=None):
    src = """
    def array(object, dtype=None, copy=True, order='K', subok=False, ndmin=0):
        return numpy.ndarray([0, 0])
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)


def infer_numpy_core_multiarray_concatenate(node, context=None):
    src = """
    def concatenate(arrays, axis=None, out=None):
        return numpy.ndarray((0, 0))
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)


def infer_numpy_core_multiarray_dot(node, context=None):
    src = """
    def dot(a, b, out=None):
        return numpy.ndarray([0, 0])
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)


def infer_numpy_core_multiarray_empty_like(node, context=None):
    src = """
    def empty_like(a, dtype=None, order='K', subok=True):
        return numpy.ndarray((0, 0))
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)


def infer_numpy_core_multiarray_where(node, context=None):
    src = """
    def where(condition, x=None, y=None):
        return numpy.ndarray([0, 0])
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)

def infer_numpy_core_multiarray_empty(node, context=None):
    src = """
    def empty(shape, dtype=float, order='C'):
        return numpy.ndarray([0, 0])
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)


def looks_like_numpy_core_multiarray_member(member_name, node):
    return (isinstance(node, astroid.Attribute)
            and node.attrname == member_name
            and node.expr.inferred()[-1].name == 'numpy')


astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_multiarray_array),
    functools.partial(looks_like_numpy_core_multiarray_member, "array")
)

astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_multiarray_dot),
    functools.partial(looks_like_numpy_core_multiarray_member, "dot")
)

astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_multiarray_empty_like),
    functools.partial(looks_like_numpy_core_multiarray_member, "empty_like")
)

astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_multiarray_concatenate),
    functools.partial(looks_like_numpy_core_multiarray_member, "concatenate")
)

astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_multiarray_where),
    functools.partial(looks_like_numpy_core_multiarray_member, "where")
)

astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_multiarray_empty),
    functools.partial(looks_like_numpy_core_multiarray_member, "empty")
)

