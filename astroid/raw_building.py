# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.
"""this module contains a set of functions to create astroid trees from scratch
(build_* functions) or from living object (object_build_* functions)
"""

import collections
import inspect
import itertools
import operator
import os
import sys
import types
import warnings

# This is a useful function for introspecting class attributes in
# inspect that is for some reason not exported.
from inspect import classify_class_attrs as _classify_class_attrs

try:
    from functools import singledispatch as _singledispatch
except ImportError:
    from singledispatch import singledispatch as _singledispatch

try:
    from inspect import (signature as _signature, Parameter as
                         _Parameter, Signature as _Signature)
except ImportError:
    from funcsigs import (signature as _signature, Parameter as
                          _Parameter, Signature as _Signature)

import six

from astroid import bases
from astroid import manager
from astroid import node_classes
from astroid import nodes
from astroid import scoped_nodes
from astroid import util

# This is a type used for some unbound methods implemented in C on
# CPython and all unbound special methods on Jython.  Bound methods
# corresponding to unbound methods of this type have the type
# types.BuiltinMethodType on CPython and Jython.  On PyPy all builtin
# and Python-defined methods share the same type.
MethodDescriptorType = type(object.__format__)

# This is another type used for some unbound methods implemented in C
# on CPython.  The repr of objects of this type describe it as "slot
# wrapper", but the repr of the type itself calls it
# "wrapper_descriptor".
WrapperDescriptorType = type(object.__getattribute__)

# Both the reprs, for objects of this type and the type itself, refer
# to this type as "method-wrapper".  It's used for bound methods
# corresponding to unbound methods with the wrapper_descriptor type on
# CPython.
MethodWrapperType = type(object().__getattribute__)

MANAGER = manager.AstroidManager()
_BUILTINS = vars(six.moves.builtins)


def _io_discrepancy(member):
    # _io module names itself `io`: http://bugs.python.org/issue18602
    member_self = getattr(member, '__self__', None)
    return (member_self and
            inspect.ismodule(member_self) and
            member_self.__name__ == '_io' and
            member.__module__ == 'io')

def _attach_local_node(parent, node, name):
    node.name = name # needed by add_local_node
    parent.add_local_node(node)


def _add_dunder_class(func, member):
    """Add a __class__ member to the given func node, if we can determine it."""
    python_cls = member.__class__
    cls_name = getattr(python_cls, '__name__', None)
    if not cls_name:
        return
    bases = [ancestor.__name__ for ancestor in python_cls.__bases__]
    ast_klass = build_class(cls_name, bases, python_cls.__doc__)
    func.instance_attrs['__class__'] = [ast_klass]


def attach_const_node(node, name, value):
    """create a Const node and register it in the locals of the given
    node with the specified name
    """
    if name not in node.special_attributes:
        _attach_local_node(node, nodes.const_factory(value), name)

def attach_import_node(node, modname, membername):
    """create a ImportFrom node and register it in the locals of the given
    node with the specified name
    """
    from_node = nodes.ImportFrom(modname, [(membername, None)])
    _attach_local_node(node, from_node, membername)


def build_module(name, doc=None, modclass=nodes.Module):
    """create and initialize a astroid Module node"""
    util.rename_warning(('build_module', 'nodes.Module'))
    return nodes.Module(name=name, doc=doc, package=False, pure_python=False)


def build_class(name, basenames=(), doc=None):
    """create and initialize a astroid ClassDef node"""
    node = nodes.ClassDef(name, doc)
    node.postinit(bases=[nodes.Name(b, node) for b in basenames],
                  body=(), decorators=())
    return node


Parameter = collections.namedtuple('Parameter', 'name default annotation kind')
DEFAULT_PARAMETER = Parameter(None, None, None, None)

def build_function(name, args=(), defaults=(), annotations=(),
                   kwonlyargs=(), kwonly_defaults=(),
                   kwonly_annotations=(), vararg=None,
                   varargannotation=None, kwarg=None, kwargannotation=None,
                   returns=None, doc=None, parent=None):
    """create and initialize an astroid FunctionDef node"""
    func = nodes.FunctionDef(name=name, doc=doc, parent=parent)
    args_node = nodes.Arguments(vararg=vararg, kwarg=kwarg, parent=func)
    args = [nodes.Name(name=a.name, parent=args_node) for n in args]
    kwonlyargs = [nodes.Name(name=a.name, parent=args_node) for a in kw_only]
    args_node.postinit(args, defaults, kwonlyargs, kw_defaults,
                      annotations, kwonly_annotations,
                      varargannotation, kwargannotation)
    func.postinit(args=args_node, body=[], returns=returns)
    return func


def build_from_import(fromname, names):
    """create and initialize an astroid ImportFrom import statement"""
    return nodes.ImportFrom(fromname, [(name, None) for name in names])


def object_build_class(node, member, localname):
    """create astroid for a living class object"""
    basenames = [base.__name__ for base in member.__bases__]
    return _base_class_object_build(node, member, basenames,
                                    localname=localname)


def object_build_function(parent, func, localname):
    """create astroid for a living function object"""
    signature = _signature(func)
    parameters = {k: tuple(g) for k, g in
                  itertools.groupby(signature.parameters.values(),
                                    operator.attrgetter('kind'))}
    # This ignores POSITIONAL_ONLY args, because they only appear in
    # functions implemented in C and can't be mimicked by any Python
    # function.
    node = build_function(getattr(func, '__name__', None) or localname,
                          parameters.get(_Parameter.POSITIONAL_OR_KEYWORD, ()),
                          parameters.get(_Parameter.KEYWORD_ONLY, ()),
                          parameters.get(_Parameter.VAR_POSITIONAL, None),
                          parameters.get(_Parameter.VAR_KEYWORD, None),
                          signature.return_annotation,
                          func.__doc__,
                          parent)
    return node


def object_build_datadescriptor(node, member, name):
    """create astroid for a living data descriptor object"""
    return _base_class_object_build(node, member, [], name)


def object_build_methoddescriptor(node, member, localname):
    """create astroid for a living method descriptor object"""
    # FIXME get arguments ?
    func = build_function(getattr(member, '__name__', None) or localname,
                          doc=member.__doc__)
    # set node's arguments to None to notice that we have no information, not
    # and empty argument list
    func.args.args = None
    node.add_local_node(func, localname)
    # _add_dunder_class(func, member)


def _base_class_object_build(node, member, basenames, name=None, localname=None):
    """create astroid for a living class object, with a given set of base names
    (e.g. ancestors)
    """
    klass = build_class(name or getattr(member, '__name__', None) or localname,
                        basenames, member.__doc__)
    klass._newstyle = isinstance(member, type)
    node.add_local_node(klass, localname)
    return klass


def _build_from_function(parent, name, member, module):
    # verify this is not an imported function
    try:
        code = six.get_function_code(member)
    except AttributeError:
        # Some implementations don't provide the code object,
        # such as Jython.
        code = None
    filename = getattr(code, 'co_filename', None)
    if filename is None:
        assert isinstance(member, object)
        return object_build_methoddescriptor(parent, member, name)
    elif filename != getattr(module, '__file__', None):
        return nodes.EmptyNode(name=name, object_=member, parent=parent)
    else:
        return object_build_function(parent, member, name)


def ast_from_object(object_, name=None):
    built_objects = {}
    module = inspect.getmodule(object_)
    return _ast_from_object(object_, built_objects, module, name)


@_singledispatch
def _ast_from_object(object_, built_objects, module, name=None, parent=None):
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    empty_node = nodes.EmptyNode(name=name, object_=object_, parent=parent)
    if name:
        parent.postinit(targets=[name_node], value=empty_node)
        node = parent
    else:
        node = empty_node
    return node


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(types.ModuleType)
def ast_from_module(module, built_objects, parent_module, name=None, parent=None):
    if module is not parent_module:
        # This module has been imported into another.
        return nodes.Import([[getattr(module, '__name__', None), name]],
                            parent=parent)
    if module in built_objects:
        return built_objects[module]
    try:
        source_file = inspect.getsourcefile(module)
    except TypeError:
        # inspect.getsourcefile raises TypeError for built-in modules.
        source_file = None
    # inspect.getdoc returns None for modules without docstrings like
    # Jython Java modules.
    module_node = nodes.Module(name=name or module.__name__,
                               doc=inspect.getdoc(module),
                               source_file=source_file,
                               package=hasattr(module, '__path__'),
                               # Assume that if inspect couldn't find a
                               # Python source file, it's probably not
                               # implemented in pure Python.
                               pure_python=bool(source_file))
    built_objects[module] = module_node
    MANAGER.cache_module(module_node)
    module_node.postinit(body=[_ast_from_object(m, built_objects, module,
                                                n, module_node)
                               for n, m in inspect.getmembers(module)])
    return module_node


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(type)
@_ast_from_object.register(types.GetSetDescriptorType)
@_ast_from_object.register(types.MemberDescriptorType)
def ast_from_class(cls, built_objects, module, name=None, parent=None):
    # print(cls)
    inspected_module = inspect.getmodule(cls)
    if inspected_module is not None and inspected_module is not module:
        return nodes.ImportFrom(fromname=
                                getattr(inspected_module, '__name__', None),
                                names=[[cls.__name__, name]],
                                parent=parent)
    if cls in built_objects:
        return built_objects[cls]
    class_node = nodes.ClassDef(name=cls.__name__ or name, doc=inspect.getdoc(cls))
    built_objects[cls] = class_node
    try:
        bases = [nodes.Name(name=b.__name__, parent=class_node)
                 for b in inspect.getmro(cls)[1:]]
        body = [_ast_from_object(a.object, built_objects, module, a.name, parent=class_node)
                for a in _classify_class_attrs(cls) if a.defining_class is cls]
    except AttributeError:
        bases = ()
        body = [_ast_from_object(m, built_objects, module, n, parent=class_node)
                for n, m in inspect.getmembers(cls)]
    class_node.postinit(bases=bases, body=body, decorators=(),
                        newstyle=isinstance(cls, type))
    return class_node
# Old-style classes
if six.PY2:
    _ast_from_object.register(types.ClassType, ast_from_class)


# pylint: disable=unused-variable; doesn't understand singledispatch

# These two types are the same on CPython but not necessarily the same
# on other implementations.
@_ast_from_object.register(types.BuiltinFunctionType)
@_ast_from_object.register(types.BuiltinMethodType)
# Methods implemented in C on CPython.
@_ast_from_object.register(MethodDescriptorType)
@_ast_from_object.register(WrapperDescriptorType)
@_ast_from_object.register(MethodWrapperType)
# types defines a LambdaType but on all existing Python
# implementations it's equivalent to FunctionType.
@_ast_from_object.register(types.FunctionType)
@_ast_from_object.register(types.MethodType)
def ast_from_function(func, built_objects, module, name=None, parent=None):
    inspected_module = inspect.getmodule(func)
    if inspected_module is not None and inspected_module is not module:
        return nodes.ImportFrom(fromname=getattr(inspected_module, '__name__', None),
                                names=[[func.__name__, name]],
                                parent=parent)
    if func in built_objects:
        return built_objects[func]
    func_node = nodes.FunctionDef(name=name or func.__name__,
                              doc=inspect.getdoc(func),
                              parent=parent)
    try:
        signature = _signature(func)
    except (ValueError, TypeError):
        # FIXME: temporary hack
        signature = _Signature()
    parameters = {k: tuple(g) for k, g in
                  itertools.groupby(signature.parameters.values(),
                                    operator.attrgetter('kind'))}

    def extract_args(parameters, parent):
        '''Takes an iterator over Parameter objects and returns three
        sequences, arg names, default values, and annotations.

        '''
        names = []
        defaults = []
        annotations = []
        for parameter in parameters:
            names.append(parameter.name)
            if parameter.default is not _Parameter.empty:
                defaults.append(_ast_from_object(parameter.default, built_objects, module, parent=parent))
            if parameter.annotation is not _Parameter.empty:
                annotations.append(_ast_from_object(parameter.annotation, built_objects, module, parent=parent))
            else:
                annotations.append(None)
        return names, defaults, annotations

    def extract_vararg(parameter):
        '''Takes a single-element iterator possibly containing a Parameter and
        returns a name and an annotation.

        '''
        try:
            return parameter[0].name
        except IndexError:
            return None

    vararg = parameters.get(_Parameter.VAR_POSITIONAL, ())
    kwarg = parameters.get(_Parameter.VAR_KEYWORD, ())
    vararg_name = extract_vararg(vararg)
    kwarg_name = extract_vararg(kwarg)
    args_node = nodes.Arguments(vararg=vararg_name, kwarg=kwarg_name, parent=func_node)

    # This ignores POSITIONAL_ONLY args, because they only appear in
    # functions implemented in C and can't be mimicked by any Python
    # function.
    names, defaults, annotations = extract_args(parameters.get(_Parameter.POSITIONAL_OR_KEYWORD, ()), args_node)
    kwonlynames, kw_defaults, kwonly_annotations = extract_args(parameters.get(_Parameter.KEYWORD_ONLY, ()), args_node)
    args = [nodes.Name(name=n, parent=args_node) for n in names]
    kwonlyargs = [nodes.Name(name=n, parent=args_node) for n in kwonlynames]
    if vararg_name and vararg[0].annotation is not _Parameter.empty:
        varargannotation = vararg.annotation
    else:
        varargannotation = None
    if kwarg_name and kwarg[0].annotation is not _Parameter.empty:
        kwargannotation = kwarg.annotation
    else:
        kwargannotation = None
    if signature.return_annotation is not _Parameter.empty:
        returns=_ast_from_object(signature_return_annotation,
                                 built_objects,
                                 module,
                                 parent=func_node)
    args_node.postinit(args, defaults, kwonlyargs, kw_defaults,
                       annotations, kwonly_annotations,
                       varargannotation, kwargannotation)
    func_node.postinit(args=args_node, body=[])
    built_objects[func] = func_node
    return func_node


BUILTIN_CONTAINERS = {list: nodes.List, set: nodes.Set, frozenset:
                      nodes.Set, tuple: nodes.Tuple}

# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(list)
@_ast_from_object.register(set)
@_ast_from_object.register(frozenset)
@_ast_from_object.register(tuple)
def ast_from_builtin_container(container, built_objects, module, name=None,
                               parent=None):
    '''Handles builtin containers that have their own AST nodes, like list
    but not range.

    '''
    if (container in built_objects and
        built_objects[container].targets[0].name == name):
        return built_objects[container]
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    container_node = BUILTIN_CONTAINERS[type(container)](parent=parent)
    if name:
        node = parent
    else:
        node = container_node
    built_objects[container] = node
    container_node.postinit(
        elts=[_ast_from_object(i, built_objects, module, parent=node)
              for i in container])
    if name:
        parent.postinit(targets=[name_node], value=container_node)
    return node


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(dict)
def ast_from_dict(dictionary, built_objects, module, name=None,
                               parent=None):
    if (dictionary in built_objects and
        built_objects[dictionary].targets[0].name == name):
        return built_objects[dictionary]
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    dict_node = nodes.Dict(parent=parent)
    if name:
        node = parent
    else:
        node = dict_node
    built_objects[dictionary] = node
    dict_node.postinit(items=[
        (_ast_from_object(k, built_objects, module, parent=node),
         _ast_from_object(v, built_objects, module, parent=node))
        for k, v in dictionary.items()])
    if name:
        parent.postinit(targets=[name_node], value=dict_node)
    return node

if six.PY2:
    _ast_from_object.register(types.DictProxyType, ast_from_dict)
else:
    _ast_from_object.register(types.MappingProxyType, ast_from_dict)


@_ast_from_object.register(str)
@_ast_from_object.register(bytes)
@_ast_from_object.register(int)
@_ast_from_object.register(float)
@_ast_from_object.register(complex)
@_ast_from_object.register(type(None))
@_ast_from_object.register(type(NotImplemented))
def ast_from_scalar(scalar, built_objects, module, name=None, parent=None):
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    scalar_node = nodes.Const(value=scalar, parent=parent)
    if name:
        parent.postinit(targets=[name_node], value=scalar_node)
        node = parent
    else:
        node = scalar_node
    return node

if six.PY2:
    _ast_from_object.register(unicode, ast_from_scalar)
    _ast_from_object.register(long, ast_from_scalar)


@_ast_from_object.register(type(Ellipsis))
def ast_from_ellipsis(ellipsis, built_objects, module, name=None, parent=None):
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    ellipsis_node = nodes.Ellipsis(parent=parent)
    if name:
        parent.postinit(targets=[name_node], value=ellipsis_node)
        node = parent
    else:
        node = ellipsis_node
    return node



class InspectBuilder(object):
    """class for building nodes from living object

    this is actually a really minimal representation, including only Module,
    FunctionDef and ClassDef nodes and some others as guessed.
    """

    # astroid from living objects ###############################################

    def __init__(self):
        self._done = {}
        self._module = None

    def inspect_build(self, module, modname=None, node_class=nodes.Module,
                      path=None):
        """build astroid from a living module (i.e. using inspect)
        this is used when there is no python source code available (either
        because it's a built-in module or because the .py is not available)
        """
        self._module = module
        if modname is None:
            modname = module.__name__
        # In Jython, Java modules have no __doc__ (see #109562)
        doc = module.__doc__ if hasattr(module, '__doc__') else None
        try:
            source_file = inspect.getsourcefile(module)
        except TypeError:
            # inspect.getsourcefile raises TypeError for builtins.
            source_file = None
        module_node = node_class(name=modname, doc=doc, source_file=source_file,
                               package=hasattr(module

    , '__path__'),
                               # Assume that if inspect can't find a
                               # Python source file, it's probably not
                               # implemented in pure Python.
                               pure_python=bool(source_file))
        MANAGER.cache_module(module_node)
        self._done = {}
        module_node.postinit(body=self.object_build(module_node, module))
        return module_node

    def object_build(self, node, obj):
        """recursive method which create a partial ast from real objects
         (only function, class, and method are handled)
        """
        if obj in self._done:
            return self._done[obj]
        self._done[obj] = node
        members = []
        for name, member in inspect.getmembers(obj):
            if inspect.ismethod(member):
                member = six.get_method_function(member)
            if inspect.isfunction(member):
                members.append(_build_from_function(node, name, member, self._module))
            elif inspect.isbuiltin(member):
                if (not _io_discrepancy(member) and
                        self.imported_member(node, member, name)):
                    continue
                members.append(object_build_methoddescriptor(node, member, name))
            elif inspect.isclass(member):
                if self.imported_member(node, member, name):
                    continue
                if member in self._done:
                    class_node = self._done[member]
                    if class_node not in set(node.get_children()):
                    # if class_node not in node.locals.get(name, ()):
                        members.append(node.add_local_node(class_node, name))
                else:
                    class_node = object_build_class(node, member, name)
                    # recursion
                    members.append(self.object_build(class_node, member))
                if name == '__class__' and class_node.parent is None:
                    class_node.parent = self._done[self._module]
            elif inspect.ismethoddescriptor(member):
                assert isinstance(member, object)
                members.append(object_build_methoddescriptor(node, member, name))
            elif inspect.isdatadescriptor(member):
                assert isinstance(member, object)
                members.append(object_build_datadescriptor(node, member, name))
            elif isinstance(member, _CONSTANTS):
                members.append(attach_const_node(node, name, member))
            elif inspect.isroutine(member):
                # This should be called for Jython, where some builtin
                # methods aren't catched by isbuiltin branch.
                members.append(_build_from_function(node, name, member, self._module))
            else:
                # create an empty node so that the name is actually defined
                members.append(nodes.EmptyNode(parent=node, name=name,
                                               object_=member))
        return members

    def imported_member(self, node, member, name):
        """verify this is not an imported class or handle it"""
        # /!\ some classes like ExtensionClass doesn't have a __module__
        # attribute ! Also, this may trigger an exception on badly built module
        # (see http://www.logilab.org/ticket/57299 for instance)
        try:
            modname = getattr(member, '__module__', None)
        except: # pylint: disable=bare-except
            warnings.warn('Unexpected error while building an AST from an '
                          'imported class.', RuntimeWarning, stacklevel=2)
            modname = None
        if modname is None:
            if (name in ('__new__', '__subclasshook__')
                    or (name in _BUILTINS and util.JYTHON)):
                # Python 2.5.1 (r251:54863, Sep  1 2010, 22:03:14)
                # >>> print object.__new__.__module__
                # None
                modname = six.moves.builtins.__name__
            else:
                nodes.EmptyNode(parent=node, name=name, object_=member)
                return True

        real_name = {
            'gtk': 'gtk_gtk',
            '_io': 'io',
        }.get(modname, modname)

        if real_name != self._module.__name__:
            # check if it sounds valid and then add an import node, else use a
            # dummy node
            try:
                getattr(sys.modules[modname], name)
            except (KeyError, AttributeError):
                attach_dummy_node(node, name, member)
            else:
                attach_import_node(node, modname, name)
            return True
        return False


### astroid bootstrapping ######################################################
Astroid_BUILDER = InspectBuilder()

# class Builtins(nodes.Module):
#     pass

_CONST_PROXY = {}
def _astroid_bootstrapping(astroid_builtin=None):
    """astroid boot strapping the builtins module"""
    # this boot strapping is necessary since we need the Const nodes to
    # inspect_build builtins, and then we can proxy Const
    if astroid_builtin is None:
        from six.moves import builtins
        astroid_builtin = Astroid_BUILDER.inspect_build(builtins) #, node_class=Builtins

    for cls, node_cls in node_classes.CONST_CLS.items():
        if cls is type(None):
            proxy = build_class('NoneType')
            proxy.parent = astroid_builtin
        elif cls is type(NotImplemented):
            proxy = build_class('NotImplementedType')
            proxy.parent = astroid_builtin
        else:
            proxy = astroid_builtin.getattr(cls.__name__)[0]
        if cls in (dict, list, set, tuple):
            node_cls._proxied = proxy
        else:
            _CONST_PROXY[cls] = proxy

# _astroid_bootstrapping()


# @scoped_nodes.get_locals.register(Builtins)
# def scoped_node(node):
#     locals_ = collections.defaultdict(list)
#     for name in ('Ellipsis', 'False', 'None', 'NotImplemented',
#                  'True', '__debug__', '__package__', '__spec__', 'copyright',
#                  'credits', 'exit', 'help', 'license', 'quit'):
#         for child in (n for n in node.body if
#                      isinstance(n, (nodes.Const, nodes.EmptyNode))):
#             if child.name == name:
#                 locals_[name].append(child)
#     for n in node.get_children():
#         scoped_nodes._get_locals(n, locals_)
#     return locals_


# TODO : find a nicer way to handle this situation;
# However __proxied introduced an
# infinite recursion (see https://bugs.launchpad.net/pylint/+bug/456870)
# def _set_proxied(const):
#     return _CONST_PROXY[const.value.__class__]
# nodes.Const._proxied = property(_set_proxied)

astroid_builtin = ast_from_object(six.moves.builtins)

# _GeneratorType = nodes.ClassDef(types.GeneratorType.__name__, types.GeneratorType.__doc__)
# _GeneratorType.parent = MANAGER.astroid_cache[six.moves.builtins.__name__]
# bases.Generator._proxied = _GeneratorType
# Astroid_BUILDER.object_build(bases.Generator._proxied, types.GeneratorType)
