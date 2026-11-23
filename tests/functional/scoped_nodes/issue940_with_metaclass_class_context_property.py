class BaseMeta(type):
    pass
class Parent(metaclass=BaseMeta):
    @property
    def __members__(self):
        return ['a', 'property']
class Derived(Parent):
    pass
# +1: inferred: Property(issue940_with_metaclass_class_context_property.Parent.__members__)
Derived.__members__
