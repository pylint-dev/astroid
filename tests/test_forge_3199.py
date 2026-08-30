"""Regression test for IndexError when inferring namedtuple with a format-string typename.

Bug: ``a = namedtuple('{0}', '')`` triggers
``IndexError: Replacement index 0 out of range for positional args tuple``
inside ``AstroidError.__str__`` because the error message contains ``{0}``
which ``str.format`` tries to interpolate.
"""

import pytest

from astroid import extract_node
from astroid.exceptions import (
    AstroidError,
    UseInferenceDefault,
)


def test_namedtuple_with_format_string_typename_no_crash():
    """Inferring ``namedtuple('{0}', '')`` should not raise IndexError."""
    code = "import collections\na = collections.namedtuple('{0}', '')"
    node = extract_node(code)
    call_node = node.value  # the Call node for collections.namedtuple(...)

    # The brain raises UseInferenceDefault (a non-AstroidError) when it can't
    # infer the namedtuple.  The bug is that str()ing the AstroidValueError
    # inside that path raises IndexError.  We just need to make sure no
    # IndexError (or any AstroidError) leaks out.
    try:
        list(call_node.infer())
    except UseInferenceDefault:
        # This is the expected, non-crashing path
        pass
    except AstroidError as exc:
        # If we get an AstroidError, calling str() on it must not raise
        # IndexError (the original bug).
        pytest.fail(
            f"Inference raised AstroidError and str(exc) crashes: {exc!r}"
        )
    except IndexError:
        pytest.fail("Inference raised IndexError (the original bug)")