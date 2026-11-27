class A(type):
    def test(cls):
        return cls

class C:
    pass

import six
class B(six.with_metaclass(A, C)):
    pass

B  # inferred: ClassDef(with_metaclass_subclasses_inheritance.B)  # inferred.ancestors(): with_metaclass_subclasses_inheritance.C, builtins.object  # inferred.ancestors().name: 'C' | 'object'  # inferred.bases[0]: Call(six.with_metaclass(A, C))
