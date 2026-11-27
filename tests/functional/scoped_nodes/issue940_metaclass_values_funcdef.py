class BaseMeta(type):
    def __members__(cls):
        return ['a', 'func']
class Parent(metaclass=BaseMeta):
    pass
Parent.__members__()  # inferred: List(['a', 'func'])
