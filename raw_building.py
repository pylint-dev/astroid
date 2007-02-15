# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""this module contains a set of functions to create astng trees from scratch
(build_* functions) or from living object (object_build_* functions)

:author:    Sylvain Thenault
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2007 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

__docformat__ = "restructuredtext en"

import sys
from inspect import getargspec

from logilab.astng import nodes

def attach___dict__(node):
    """attach the __dict__ attribute to Class and Module objects"""
    dictn = nodes.Dict([])
    dictn.parent = node
    node.locals['__dict__'] = [dictn]

_marker = object()

def attach_dummy_node(node, name, object=_marker):
    """create a dummy node and register it in the locals of the given
    node with the specified name
    """
    enode = nodes.EmptyNode()
    enode.object = object
    _attach_local_node(node, enode, name)

nodes.EmptyNode.has_underlying_object = lambda self: self.object is not _marker

def attach_const_node(node, name, value):
    """create a Const node and register it in the locals of the given
    node with the specified name
    """
    _attach_local_node(node, nodes.Const(value), name)

if sys.version_info < (2, 5):
    def attach_import_node(node, modname, membername):
        """create a From node and register it in the locals of the given
        node with the specified name
        """
        _attach_local_node(node,
                           nodes.From(modname, ( (membername, None), ) ),
                           membername)
else:
    def attach_import_node(node, modname, membername):
        """create a From node and register it in the locals of the given
        node with the specified name
        """
        _attach_local_node(node,
                           nodes.From(modname, ( (membername, None), ), 0),
                           membername)
    
def _attach_local_node(parent, node, name):
    node.name = name # needed by add_local_node
    node.parent = parent
    node.lineno = 1
    parent.add_local_node(node)


def build_module(name, doc=None):
    """create and initialize a astng Module node"""
    node = nodes.Module(doc, nodes.Stmt([]))
    node.node.parent = node
    node.name = name
    node.pure_python = False
    node.package = False
    node.parent = None
    node.globals = node.locals = {}
    return node

def build_class(name, basenames=None, doc=None):
    """create and initialize a astng Class node"""
    klass = nodes.Class(name, [], doc, nodes.Stmt([]))
    bases = [nodes.Name(base) for base in basenames]
    for base in bases:
        base.parent = klass
    klass.basenames = basenames
    klass.bases = bases
    klass.code.parent = klass
    klass.locals = {}
    klass.instance_attrs = {}
    for name, value in ( ('__name__', name),
                         #('__module__', node.root().name),
                         ):
        const = nodes.Const(value)
        const.parent = klass
        klass.locals[name] = [const]
    return klass

# introduction of decorators has changed the Function initializer arguments
if sys.version_info >= (2, 4):
    try:
        from compiler.ast import Decorators as BaseDecorators
        class Decorators(BaseDecorators):
            def __init__(self):
                BaseDecorators.__init__(self, [], 0)
    except ImportError:
        Decorators = list
        
    def build_function(name, args=None, defaults=None, flag=0, doc=None):
        """create and initialize a astng Function node"""
        args, defaults = args or [], defaults or []
        # first argument is now a list of decorators
        func = nodes.Function(Decorators(), name, args, defaults, flag, doc,
                              nodes.Stmt([]))
        func.code.parent = func
        func.locals = {}
        if args:
            register_arguments(func, args)
        return func
    
else:    
    def build_function(name, args=None, defaults=None, flag=0, doc=None):
        """create and initialize a astng Function node"""
        args, defaults = args or [], defaults or []
        func = nodes.Function(name, args, defaults, flag, doc, nodes.Stmt([]))
        func.code.parent = func
        func.locals = {}
        if args:
            register_arguments(func, args)
        return func


def build_name_assign(name, value):
    """create and initialize an astng Assign for a name assignment"""
    return nodes.Assign([nodes.AssName(name, 'OP_ASSIGN')], nodes.Const(value))

def build_attr_assign(name, value, attr='self'):
    """create and initialize an astng Assign for an attribute assignment"""
    return nodes.Assign([nodes.AssAttr(nodes.Name(attr), name, 'OP_ASSIGN')],
                        nodes.Const(value))

if sys.version_info < (2, 5):
    def build_from_import(fromname, names):
        """create and intialize an astng From import statement"""
        return nodes.From(fromname, [(name, None) for name in names])
else:
    def build_from_import(fromname, names):
        """create and intialize an astng From import statement"""
        return nodes.From(fromname, [(name, None) for name in names], 0)

def register_arguments(node, args):
    """add given arguments to local
    
    args is a list that may contains nested lists
    (i.e. def func(a, (b, c, d)): ...)
    """
    for arg in args:
        if type(arg) is type(''):
            node.set_local(arg, node)
        else:
            register_arguments(node, arg)


def object_build_class(node, member):
    """create astng for a living class object"""
    basenames = [base.__name__ for base in member.__bases__]
    return _base_class_object_build(node, member, basenames)

def object_build_function(node, member):
    """create astng for a living function object"""
    args, varargs, varkw, defaults = getargspec(member)
    if varargs is not None:
        args.append(varargs)
    if varkw is not None:
        args.append(varkw)
    func = build_function(member.__name__, args, defaults,
                          member.func_code.co_flags, member.__doc__)
    node.add_local_node(func)

def object_build_datadescriptor(node, member, name):
    """create astng for a living data descriptor object"""
    return _base_class_object_build(node, member, [], name)

def object_build_methoddescriptor(node, member):
    """create astng for a living method descriptor object"""
    # FIXME get arguments ?
    func = build_function(member.__name__, doc=member.__doc__)
    # set argnames to None to notice that we have no information, not
    # and empty argument list
    func.argnames = None 
    node.add_local_node(func)

def _base_class_object_build(node, member, basenames, name=None):
    """create astng for a living class object, with a given set of base names
    (e.g. ancestors)
    """
    klass = build_class(name or member.__name__, basenames, member.__doc__)
    klass._newstyle = isinstance(member, type)
    node.add_local_node(klass)
    try:
        # limit the instantiation trick since it's too dangerous
        # (such as infinite test execution...)
        # this at least resolves common case such as Exception.args,
        # OSError.errno
        if issubclass(member, Exception):
            instdict = member().__dict__
        else:
            raise TypeError
    except:
        pass
    else:
        for name, obj in instdict.items():
            valnode = nodes.EmptyNode()
            valnode.object = obj
            valnode.parent = klass
            valnode.lineno = 1
            klass.instance_attrs[name] = [valnode]
    return klass


__all__ = ('register_arguments',  'build_module', 
           'object_build_class', 'object_build_function', 
           'object_build_datadescriptor', 'object_build_methoddescriptor',
           'attach___dict__', 'attach_dummy_node',
           'attach_const_node', 'attach_import_node')
