# A classmethod accessed on its class proxies the function directly.
#
# Reported in https://github.com/pylint-dev/pylint/issues/11198, where
# ``getattr()`` on ``__func__`` aborted the whole pylint run.
class A:
    @classmethod
    def test(cls): pass
A.test.__func__  # inferred: FunctionDef(bound_method_model_classmethod_on_class.A.test)
getattr(A.test, "__func__")  # inferred: FunctionDef(bound_method_model_classmethod_on_class.A.test)
A.test.__self__  # inferred: ClassDef(bound_method_model_classmethod_on_class.A)
