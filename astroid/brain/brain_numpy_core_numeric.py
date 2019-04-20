# Copyright (c) 2018-2019 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy.core.numeric module."""

import functools
import astroid


def numpy_core_numeric_transform():
    return astroid.parse(
        """
    # different functions defined in numeric.py
    import numpy
    def zeros_like(a, dtype=None, order='K', subok=True): return numpy.ndarray((0, 0))
    def ones_like(a, dtype=None, order='K', subok=True): return numpy.ndarray((0, 0))
    def full_like(a, fill_value, dtype=None, order='K', subok=True): return numpy.ndarray((0, 0))
        """
        )

astroid.register_module_extender(
    astroid.MANAGER, "numpy.core.numeric", numpy_core_numeric_transform
)

def infer_numpy_core_numeric_ones(node, context=None):
    src = """
    def ones(shape, dtype=None, order='C'):
        return numpy.ndarray([0, 0])
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)

def looks_like_numpy_core_numeric_member(member_name, node):
    return (isinstance(node, astroid.Attribute)
            and node.attrname == member_name
            and node.expr.inferred()[-1].name == 'numpy')


astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_numeric_ones),
    functools.partial(looks_like_numpy_core_numeric_member, "ones")
)