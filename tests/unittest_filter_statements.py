# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import unittest

from astroid.builder import extract_node
from astroid.filter_statements import _filter_stmts
from astroid.nodes import EmptyNode


class FilterStatementsTest(unittest.TestCase):
    def test_empty_node(self) -> None:
        enum_mod = extract_node("import enum")
        empty = EmptyNode(parent=enum_mod)
        empty.is_statement = True
        filtered_statements = _filter_stmts(
            empty, [empty.statement(future=True)], empty.frame(future=True), 0
        )
        self.assertIs(filtered_statements[0], empty)
