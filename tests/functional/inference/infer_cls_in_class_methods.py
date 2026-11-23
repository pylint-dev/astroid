class A(type):
    def __call__(cls):
        cls  # inferred: ClassDef(infer_cls_in_class_methods.A)
class B(object):
    def __call__(cls):
        cls  # inferred: Instance(infer_cls_in_class_methods.B)
