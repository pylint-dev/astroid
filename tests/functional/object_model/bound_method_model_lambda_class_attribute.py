# A lambda assigned as a class attribute is proxied directly too.
class A:
    test = lambda self: 1
a = A()
a.test.__func__  # inferred: Lambda(bound_method_model_lambda_class_attribute.A.<lambda>)
# +1: inferred: Lambda(bound_method_model_lambda_class_attribute.A.<lambda>)
getattr(a.test, "__func__")
