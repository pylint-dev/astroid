# Stop inherited __call__ method from incorrectly returning wrong class.
#
# See https://github.com/pylint-dev/pylint/issues/2199
class Base:
    def __call__(self):
        return self

class Sub(Base):
    pass
obj = Sub()
val = obj()
val  # inferred: Instance(call_on_instance_with_inherited_dunder_call_method.Sub)
