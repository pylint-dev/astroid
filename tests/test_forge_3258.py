"""Regression test for AttributeError: 'TypeVar' object has no attribute 'getattr'.

When a class uses a type parameter named ``__slots__`` (PEP 695), astroid
should not crash when computing slots.
"""

import astroid
from astroid import builder


def test_slots_with_typevar_named_slots() -> None:
    """A class with a type parameter named ``__slots__`` should not crash on slots()."""
    code = """
class C[__slots__]:
    def __init__(self):
        self.a = 1
"""
    module = builder.parse(code)
    cls = module.body[0]
    # This should not raise AttributeError
    result = cls.slots()
    # The type parameter __slots__ is not a real __slots__ definition,
    # so slots() should return None (no actual slots defined).
    assert result is None