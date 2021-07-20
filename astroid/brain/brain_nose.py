# Copyright (c) 2015-2016, 2018, 2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE


"""Hooks for nose library."""

import re
import textwrap

import astroid.builder
from astroid.brain.helpers import register_module_extender
from astroid.exceptions import InferenceError
from astroid.manager import AstroidManager

_BUILDER = astroid.builder.AstroidBuilder(AstroidManager())


CAPITALS = re.compile("([A-Z])")


def _pep8(name, caps=CAPITALS):
    return caps.sub(lambda m: "_" + m.groups()[0].lower(), name)


def _nose_tools_functions():
    """Get an iterator of names and bound methods."""
    module = _BUILDER.string_build(
        textwrap.dedent(
            """
    import unittest

    class Test(unittest.TestCase):
        pass
    a = Test()
    """
        )
    )
    try:
        case = next(module["a"].infer())
    except (InferenceError, StopIteration):
        return
    for method in case.methods():
        if method.name.startswith("assert") and "_" not in method.name:
            pep8_name = _pep8(method.name)
            yield pep8_name, astroid.BoundMethod(method, case)
        if method.name == "assertEqual":
            # nose also exports assert_equals.
            yield "assert_equals", astroid.BoundMethod(method, case)


def _nose_tools_transform(node):
    for method_name, method in _nose_tools_functions():
        node.locals[method_name] = [method]


def _nose_tools_trivial_transform():
    """Custom transform for the nose.tools module."""
    stub = _BUILDER.string_build("""__all__ = []""")
    all_entries = ["ok_", "eq_"]

    for pep8_name, method in _nose_tools_functions():
        all_entries.append(pep8_name)
        stub[pep8_name] = method

    # Update the __all__ variable, since nose.tools
    # does this manually with .append.
    all_assign = stub["__all__"].parent
    all_object = astroid.List(all_entries)
    all_object.parent = all_assign
    all_assign.value = all_object
    return stub


register_module_extender(
    AstroidManager(), "nose.tools.trivial", _nose_tools_trivial_transform
)
AstroidManager().register_transform(
    astroid.Module, _nose_tools_transform, lambda n: n.name == "nose.tools"
)
