from logilab.astng import nodes
from logilab.astng import MANAGER

nodes.Num.__bases__ += (nodes.Instance,)
nodes.Num._proxied = None
nodes.Num.has_dynamic_getattr = lambda x: False
nodes.Num._proxied = MANAGER.astng_from_class(int) # XXX long/complex

nodes.Str.__bases__ += (nodes.Instance,)
nodes.Str._proxied = None
nodes.Str.has_dynamic_getattr = lambda x: False
nodes.Str._proxied = MANAGER.astng_from_class(unicode) # XXX str


def Const___getattr__(node, name):
    #if node.value is None:
    #    raise AttributeError(name)
    return getattr(node._proxied, name)
nodes.Str.__getattr__ = Const___getattr__
nodes.Num.__getattr__ = Const___getattr__

def Const_getattr(node, name, context=None, lookupclass=None):
    #if node.value is None:
    #    raise NotFoundError(name)
    return node._proxied.getattr(name, context)
nodes.Str.getattr = Const_getattr
nodes.Num.getattr = Const_getattr
