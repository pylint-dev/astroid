class Ala(object):
     def static(self):  # extra_decorators: [Call(staticmethod(static))]
         pass
     def class_method(self):  # extra_decorators: [Call(classmethod(class_method))]
         pass
     class_method = classmethod(class_method)
     static = staticmethod(static)
