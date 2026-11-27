# Test that super().classmethod() infers the leaf type in a 3-level chain.
#
# Regression test for:
# https://github.com/pylint-dev/pylint/issues/9159
# https://github.com/pylint-dev/astroid/issues/2852
import typing

class C:
    @classmethod
    def from_nothing(cls) -> typing.Self:
        return cls()

class D(C):
    @classmethod
    def from_nothing(cls) -> typing.Self:
        return super().from_nothing()

class E(D):
    clsattr = 1

# +2: inferred: Instance(super_classmethod_three_level_chain_return_type.E)
# +1: inferred._proxied.name: 'E'
E.from_nothing()
