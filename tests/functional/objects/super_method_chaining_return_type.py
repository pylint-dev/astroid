# Test that super().method() correctly infers child type.
#
# Regression test for: https://github.com/pylint-dev/astroid/issues/457
class Parent:
    def method(self) -> "Parent":
        return self

class Child(Parent):
    def method(self) -> "Child":
        return super().method()

    def extra(self) -> "Child":
        return self

# +2: inferred: Instance(super_method_chaining_return_type.Child)
# +1: inferred._proxied.name: 'Child'
Child().method().extra()
