# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

OPS: list[list[str]] = [
    ["Lambda"],  # lambda x: x + 1
    ["IfExp"],  # 1 if True else 2
    ["or"],
    ["and"],
    ["not"],
    ["Compare"],  # in, not in, is, is not, <, <=, >, >=, !=, ==
    ["|"],
    ["^"],
    ["&"],
    ["<<", ">>"],
    ["+", "-"],
    ["*", "@", "/", "//", "%"],
    ["UnaryOp"],  # +, -, ~
    ["**"],
    ["Await"],
]

OP_PRECEDENCE: dict[str, int] = {
    op: precedence for precedence, ops in enumerate(OPS) for op in ops
}
