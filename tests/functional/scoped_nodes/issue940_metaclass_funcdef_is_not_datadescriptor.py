class BaseMeta(type):
    def __members__(cls):
        return ['a', 'property']
class Parent(metaclass=BaseMeta):
    @property
    def __members__(cls):
        return BaseMeta.__members__()
class Derived(Parent):
    pass
# +1: inferred: Property(issue940_metaclass_funcdef_is_not_datadescriptor.Parent.__members__)
Derived.__members__
