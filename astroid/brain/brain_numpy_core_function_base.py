# Copyright (c) 2019-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/LICENSE


"""Astroid hooks for numpy.core.function_base module."""

import functools

import astroid

from .brain_numpy_utils import infer_numpy_member, looks_like_numpy_member

METHODS_TO_BE_INFERRED = {
    "linspace": """def linspace(start, stop, num=50, endpoint=True, retstep=False, dtype=None, axis=0):
            return numpy.ndarray([0, 0])""",
    "logspace": """def logspace(start, stop, num=50, endpoint=True, base=10.0, dtype=None, axis=0):
            return numpy.ndarray([0, 0])""",
    "geomspace": """def geomspace(start, stop, num=50, endpoint=True, dtype=None, axis=0):
            return numpy.ndarray([0, 0])""",
}

for func_name, func_src in METHODS_TO_BE_INFERRED.items():
    inference_function = functools.partial(infer_numpy_member, func_src)
    astroid.MANAGER.register_transform(
        astroid.Attribute,
        astroid.inference_tip(inference_function),
        functools.partial(looks_like_numpy_member, func_name),
    )
