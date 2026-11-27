# Test that super().method() infers the leaf type in a 3-level chain.
#
# Regression test for:
# https://github.com/pylint-dev/pylint/issues/10807
# https://github.com/pylint-dev/astroid/issues/2852
import typing

class A:
    def method(self) -> typing.Self:
        return self

class B(A):
    def method(self) -> typing.Self:
        return super().method()

class C(B):
    clsattr = 1

# +2: inferred: Instance(super_method_three_level_chain_return_type.C)
# +1: inferred._proxied.name: 'C'
C().method()
