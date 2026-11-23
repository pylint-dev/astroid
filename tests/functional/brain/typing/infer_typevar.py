# Regression test for: https://github.com/pylint-dev/pylint/issues/8802
#
# Test that an inferred `typing.TypeVar()` call produces a `nodes.ClassDef`
# node.
from typing import TypeVar
TypeVar('My.Type')  # inferred: ClassDef(.My.Type)
