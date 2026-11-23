from undefined import Undefined
class Meta(type):
    __call__ = Undefined
class A(metaclass=Meta):
    pass
A()  # inferred: Instance(metaclass_cannot_infer_call_yields_an_instance.A)
