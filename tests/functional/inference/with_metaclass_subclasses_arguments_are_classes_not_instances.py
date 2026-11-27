class A(type):
    def test(cls):
        return cls
import six
class B(six.with_metaclass(A)):
    pass

B.test()  # inferred: ClassDef(with_metaclass_subclasses_arguments_are_classes_not_instances.B)
