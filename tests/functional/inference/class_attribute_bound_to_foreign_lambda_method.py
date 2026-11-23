# A class attribute bound to another class' lambda "method" infers to a
# bound method instead of raising: the method reaching ``_is_property``
# proxies a ``Lambda`` node, which has no ``decoratornames``.
class A:
    f = lambda self: 42

class B:
    g = A().f

# +1: inferred: BoundMethod(class_attribute_bound_to_foreign_lambda_method.A.<lambda>)
getattr(B(), "g")
B().g  # inferred: BoundMethod(class_attribute_bound_to_foreign_lambda_method.A.<lambda>)
