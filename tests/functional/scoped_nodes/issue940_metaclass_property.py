class BaseMeta(type):
    @property
    def __members__(cls):
        return ['a', 'property']
class Parent(metaclass=BaseMeta):
    pass
Parent.__members__  # inferred: List(['a', 'property'])
