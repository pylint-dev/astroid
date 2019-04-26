# Copyright (c) 2018-2019 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Different utilities for the numpy brains"""


import astroid


def infer_numpy_member(src, node, context=None):
    node = astroid.extract_node(src)
    return node.infer(context=context)


def looks_like_numpy_member(member_name, node):
    return (
        isinstance(node, astroid.Attribute)
        and node.attrname == member_name
        and node.expr.inferred()[0].name.startswith("numpy")
    )
