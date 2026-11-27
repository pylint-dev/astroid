# https://github.com/PyCQA/astroid/issues/1828
class Base:
    def return_type(self):
        return type(self)()
class A(Base):
    def method(self):
        return self.return_type()
class B(Base):
    def method(self):
        return self.return_type()
A().method()  # inferred: Instance(inference_context_consideration.A)
B().method()  # inferred: Instance(inference_context_consideration.B)
