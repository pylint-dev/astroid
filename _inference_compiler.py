
from logilab.astng import nodes
from logilab.astng import MANAGER, YES, ASTNGError, InferenceError, \
     NotFoundError, Instance, path_wrapper

nodes.Const.__bases__ += (Instance,)
nodes.Const._proxied = None
def Const___getattr__(self, name):
    if self.value is None:
        raise AttributeError(name)
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return getattr(self._proxied, name)
nodes.Const.__getattr__ = Const___getattr__
def Const_getattr(self, name, context=None, lookupclass=None):
    if self.value is None:
        raise NotFoundError(name)
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return self._proxied.getattr(name, context)
nodes.Const.getattr = Const_getattr
nodes.Const.has_dynamic_getattr = lambda x: False

def Const_pytype(self):
    if self.value is None:
        return '__builtin__.NoneType'
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return self._proxied.qname()
nodes.Const.pytype = Const_pytype


nodes.Const.infer = nodes.infer_end

