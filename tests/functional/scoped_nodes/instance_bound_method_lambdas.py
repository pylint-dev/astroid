# +3: inferred: ClassDef(instance_bound_method_lambdas.Test)
# +2: inferred.igetattr(lam): Lambda(instance_bound_method_lambdas.Test.<lambda>)
# +1: inferred.igetattr(not_method): Lambda(instance_bound_method_lambdas.Test.<lambda>)
class Test(object):
    lam = lambda self: self
    not_method = lambda xargs: xargs
# +3: inferred: Instance(instance_bound_method_lambdas.Test)
# +2: inferred.igetattr(lam): BoundMethod(instance_bound_method_lambdas.Test.<lambda>)
# +1: inferred.igetattr(not_method): Lambda(instance_bound_method_lambdas.Test.<lambda>)
Test()
