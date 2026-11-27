# Regression test for https://github.com/pylint-dev/astroid/issues/3191
class A(metaclass=sum):
    pass
A | None  # inferred: Uninferable
