# Regression test for https://github.com/pylint-dev/astroid/issues/483
# Make sure issue where referring to the same variable
# in the same inferred expression caused an uninferable result.
b = 1
a = b + b
a  # inferred: Const(2)
