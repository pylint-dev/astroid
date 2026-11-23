class A(object):
    def test(self):
        pass
# +3: inferred: UnboundMethod(no_super_getattr.A.test)
# +2: inferred.getattr(__missssing__): AttributeInferenceError
# +1: inferred.getattr(__name__): Const('test')
meth = A.test
