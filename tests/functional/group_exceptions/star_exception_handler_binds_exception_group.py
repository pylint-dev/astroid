# Regression test for https://github.com/pylint-dev/astroid/issues/2400.
#
# In ``except* TypeError as eg``, the bound name ``eg`` is the
# ``ExceptionGroup`` wrapping the caught exceptions, not a ``TypeError``
# instance. astroid used to infer it as the exception type listed on the
# handler.
try:
    raise ExceptionGroup("group", [TypeError("x")])
except* TypeError as eg:
    eg  # inferred: ExceptionInstance(builtins.ExceptionGroup)
