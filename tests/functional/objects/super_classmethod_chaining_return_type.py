# Test that super().classmethod() correctly infers child type.
#
# Regression test for: https://github.com/pylint-dev/astroid/issues/457
class Parent:
    @classmethod
    def create(cls) -> "Parent":
        return cls()

class Child(Parent):
    @classmethod
    def create(cls) -> "Child":
        return super().create()

    def extra(self) -> "Child":
        return self

# +2: inferred: Instance(super_classmethod_chaining_return_type.Child)
# +1: inferred._proxied.name: 'Child'
Child.create().extra()
