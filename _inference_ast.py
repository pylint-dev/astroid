from logilab.astng import nodes
from logilab.astng import MANAGER

nodes.Num.__bases__ += (nodes.Instance,)
nodes.Num._proxied = None
nodes.Num.has_dynamic_getattr = lambda x: False
def _Num_value_proxy(node):
    if node._proxied is None:
        node._proxied = MANAGER.astng_from_class(node.n.__class__)
    return node._proxied
nodes.Num._value_proxy = _Num_value_proxy


nodes.Str.__bases__ += (nodes.Instance,)
nodes.Str._proxied = None
nodes.Str.has_dynamic_getattr = lambda x: False
def _Str_value_proxy(node):
    if node._proxied is None:
        node._proxied = MANAGER.astng_from_class(node.s.__class__)
    return node._proxied
nodes.Str._value_proxy = _Str_value_proxy


def Const___getattr__(node, name):
    #if node.value is None:
    #    raise AttributeError(name)
    return getattr(node._value_proxy(), name)
nodes.Str.__getattr__ = Const___getattr__
nodes.Num.__getattr__ = Const___getattr__

def Const_getattr(node, name, context=None, lookupclass=None):
    #if node.value is None:
    #    raise NotFoundError(name)
    return node._value_proxy().getattr(name, context)
nodes.Str.getattr = Const_getattr
nodes.Num.getattr = Const_getattr

def Const_pytype(node):
    return node._value_proxy().qname()
nodes.Num.pytype = Const_pytype
nodes.Str.pytype = Const_pytype


nodes.Num.infer = nodes.infer_end
nodes.Str.infer = nodes.infer_end
