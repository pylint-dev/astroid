class Metaclass(type):
    foo = lala

class B(object, metaclass=Metaclass): pass  # igetattr(foo): Uninferable
