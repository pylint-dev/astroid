class A(type):
    def test(cls):
        return cls
from six import with_metaclass
class B(with_metaclass(A)):
    pass

B.test()  # inferred: ClassDef(with_metaclass_with_partial_imported_name.B)
