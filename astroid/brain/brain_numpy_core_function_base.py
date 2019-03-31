# Copyright (c) 2018-2019 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy.core.function_base module."""

import functools
import astroid


def infer_numpy_core_function_base_linspace(node, context=None):
    src = """
    def linspace(start, stop, num=50, endpoint=True, retstep=False, dtype=None, axis=0):
        return numpy.ndarray([0, 0])
    """
    node = astroid.extract_node(src)
    return node.infer(context=context)


def looks_like_numpy_core_function_base_member(member_name, node):
    return (isinstance(node, astroid.Attribute)
            and node.attrname == member_name
            and node.expr.inferred()[-1].name == 'numpy')


astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_core_function_base_linspace),
    functools.partial(looks_like_numpy_core_function_base_member, "linspace")
)