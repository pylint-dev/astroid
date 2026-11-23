# Test the fact that a method which is a lambda built from
# a factory is well inferred as a bound method (bug pylint 2594).
def lambda_factory():
    return lambda self: print("Hello world")

# +2: inferred: ClassDef(instance_bound_method_lambdas_2.MyClass)
# +1: inferred.igetattr(f2): Lambda(instance_bound_method_lambdas_2.lambda_factory.<lambda>)
class MyClass(object):
    f2 = lambda_factory()

# +2: inferred: Instance(instance_bound_method_lambdas_2.MyClass)
# +1: inferred.igetattr(f2): BoundMethod(instance_bound_method_lambdas_2.lambda_factory.<lambda>)
MyClass()
