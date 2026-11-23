class Grandparent:
    @property
    def __members__(self):
        return ['a', 'property']
class Parent(Grandparent):
    pass
class Child(Parent):
    pass
Child().__members__  # inferred: List(['a', 'property'])
