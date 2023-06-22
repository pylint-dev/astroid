# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from astroid.builder import extract_node
from astroid.filter_statements import _filter_stmts
from astroid.nodes import EmptyNode


def test_empty_node() -> None:
    enum_mod = extract_node("import enum")
    empty = EmptyNode(parent=enum_mod)
    empty.is_statement = True
    filtered_statements = _filter_stmts(empty, [empty.statement()], empty.frame(), 0)
    assert filtered_statements[0] is empty
