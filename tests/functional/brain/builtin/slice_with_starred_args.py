# Regression test for https://github.com/pylint-dev/astroid/issues/186.
#
# The builtin arg-count check used to refuse to infer when ``Call.args``
# contained a ``Starred`` node, e.g. ``slice(*(1, 2, 3))``.
slice(*(1, 2, 3))  # inferred: Instance(builtins.slice)
