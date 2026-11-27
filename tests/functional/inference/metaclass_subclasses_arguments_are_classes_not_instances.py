class A(type):
    def test(cls):
        return cls
class B(object, metaclass=A):
    pass

B.test()  # inferred: ClassDef(metaclass_subclasses_arguments_are_classes_not_instances.B)
