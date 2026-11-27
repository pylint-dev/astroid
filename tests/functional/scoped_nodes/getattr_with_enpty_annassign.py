class Parent:
    attr: int = 2

# +4: getattr(attr): AssignName(attr)
# +3: getattr(attr)[0]: AssignName(attr)
# +2: getattr(attr)[0].lineno: 2
# +1: getattr(attr)[0].name: 'attr'
class Child(Parent):
    attr: int
