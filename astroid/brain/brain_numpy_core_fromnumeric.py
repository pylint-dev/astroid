# Copyright (c) 2018-2019 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy.core.fromnumeric module."""

import functools
import astroid
from brain_numpy_utils import infer_numpy_member


def looks_like_out_name_in_numpy_sum(member_name: str, node: astroid.node_classes.NodeNG) -> bool:
    if (isinstance(node, astroid.Name)
        and node.name == "out"
        and node.frame().name == "sum"
        and node.frame().parent.name.startswith('numpy')):
        return True
    return False

inference_function = functools.partial(infer_numpy_member, "out = np.ndarray([0, 0])")
astroid.MANAGER.register_transform(
    astroid.Name,
    astroid.inference_tip(inference_function),
    functools.partial(looks_like_out_name_in_numpy_sum, "out"),
)
