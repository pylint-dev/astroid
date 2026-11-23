class my_classmethod(classmethod):
    pass

def factory():
    return my_classmethod

class SomeClass:  # locals['method'][0].type: 'classmethod'
    @factory()
    def method(cls):
        pass
