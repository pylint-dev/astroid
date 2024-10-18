# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import unittest

from astroid.nodes.scoped_nodes.scoped_nodes import FunctionDef

from astroid import Uninferable, builder, extract_node, nodes
from astroid.exceptions import InferenceError


class TestLocals(unittest.TestCase):
    def test(self) -> None:
        module = builder.parse(
            """
            x1 = 1
            def f1():
                x2 = 2
                def f2():
                    global x1
                    nonlocal x2
                    x1 = 1
                    x2 = 2
                    x3 = 3
            """
        )
        x = module.locals["f1"][0].locals["f2"][0].locals
        pass
