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

# ChainMap was made available in Python 3, but a precursor lives in
# ConfigParser in 2.7.
try:
    from collections import ChainMap as _ChainMap
except ImportError:
    from ConfigParser import _Chainmap as _ChainMap

try:
    from functools import singledispatch as _singledispatch
except ImportError:
    from singledispatch import singledispatch as _singledispatch

try:
    from inspect import signature as _signature, Parameter as _Parameter
except ImportError:
    from funcsigs import signature as _signature, Parameter as _Parameter

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


# def _io_discrepancy(member):
#     # _io module names itself `io`: http://bugs.python.org/issue18602
#     member_self = getattr(member, '__self__', None)
#     return (member_self and
#             inspect.ismodule(member_self) and
#             member_self.__name__ == '_io' and
#             member.__module__ == 'io')

# def _add_dunder_class(func, member):
#     """Add a __class__ member to the given func node, if we can determine it."""
#     python_cls = member.__class__
#     cls_name = getattr(python_cls, '__name__', None)
#     if not cls_name:
#         return
#     bases = [ancestor.__name__ for ancestor in python_cls.__bases__]
#     ast_klass = build_class(cls_name, bases, python_cls.__doc__)
#     func.instance_attrs['__class__'] = [ast_klass]

# Parameter = collections.namedtuple('Parameter', 'name default annotation kind')
# DEFAULT_PARAMETER = Parameter(None, None, None, None)

# def build_function(name, args=(), defaults=(), annotations=(),
#                    kwonlyargs=(), kwonly_defaults=(),
#                    kwonly_annotations=(), vararg=None,
#                    varargannotation=None, kwarg=None, kwargannotation=None,
#                    returns=None, doc=None, parent=None):
#     """create and initialize an astroid FunctionDef node"""
#     func = nodes.FunctionDef(name=name, doc=doc, parent=parent)
#     args_node = nodes.Arguments(vararg=vararg, kwarg=kwarg, parent=func)
#     args = [nodes.Name(name=a.name, parent=args_node) for n in args]
#     kwonlyargs = [nodes.Name(name=a.name, parent=args_node) for a in kw_only]
#     args_node.postinit(args, defaults, kwonlyargs, kw_defaults,
#                       annotations, kwonly_annotations,
#                       varargannotation, kwargannotation)
#     func.postinit(args=args_node, body=[], returns=returns)
#     return func

# def object_build_function(parent, func, localname):
#     """create astroid for a living function object"""
#     signature = _signature(func)
#     parameters = {k: tuple(g) for k, g in
#                   itertools.groupby(signature.parameters.values(),
#                                     operator.attrgetter('kind'))}
#     # This ignores POSITIONAL_ONLY args, because they only appear in
#     # functions implemented in C and can't be mimicked by any Python
#     # function.
#     node = build_function(getattr(func, '__name__', None) or localname,
#                           parameters.get(_Parameter.POSITIONAL_OR_KEYWORD, ()),
#                           parameters.get(_Parameter.KEYWORD_ONLY, ()),
#                           parameters.get(_Parameter.VAR_POSITIONAL, None),
#                           parameters.get(_Parameter.VAR_KEYWORD, None),
#                           signature.return_annotation,
#                           func.__doc__,
#                           parent)
#     return node


def ast_from_object(object_, name=None):
    return _ast_from_object(object_, _ChainMap(),
                            inspect.getmodule(object_), name)


@_singledispatch
def _ast_from_object(object_, built_objects, module, name=None, parent=None):
    # if name:
    #     parent = nodes.Assign(parent=parent)
    #     name_node = nodes.AssignName(name, parent=parent)
    empty_node = nodes.EmptyNode(name=name, object_=object_, parent=parent)
    # if name:
    #     parent.postinit(targets=[name_node], value=empty_node)
    #     node = parent
    # else:
    node = empty_node
    return node


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(types.ModuleType)
def ast_from_module(module, built_objects, parent_module, name=None, parent=None):
    if module is not parent_module:
        # This module has been imported into another.
        return nodes.Import([[module.__name__, name]], parent=parent)
    if id(module) in built_objects:
        return nodes.Name(name=name or module.__name__, parent=parent_module)
    try:
        source_file = inspect.getsourcefile(module)
    except TypeError:
        # inspect.getsourcefile raises TypeError for built-in modules.
        source_file = None
    module_node = nodes.Module(name=name or module.__name__,
                               # inspect.getdoc returns None for
                               # modules without docstrings like
                               # Jython Java modules.
                               doc=inspect.getdoc(module),
                               source_file=source_file,
                               package=hasattr(module, '__path__'),
                               # Assume that if inspect couldn't find a
                               # Python source file, it's probably not
                               # implemented in pure Python.
                               pure_python=bool(source_file))
    built_objects[id(module)] = module_node
    built_objects = _ChainMap({}, *built_objects.maps)
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
    inspected_module = inspect.getmodule(cls)
    if inspected_module is not None and inspected_module is not module:
        return nodes.ImportFrom(fromname=
                                getattr(inspected_module, '__name__', None),
                                names=[[cls.__name__, name]],
                                parent=parent)
    if id(cls) in built_objects:
        # return built_objects[id(cls)]
        return nodes.Name(name=name or cls.__name__, parent=parent)
    class_node = nodes.ClassDef(name=name or cls.__name__, doc=inspect.getdoc(cls), parent=parent)
    built_objects[id(cls)] = class_node
    built_objects = _ChainMap({}, *built_objects.maps)
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
    if id(func) in built_objects:
        # return built_objects[id(func)]
        return nodes.Name(name=name or func.__name__, parent=parent)
    func_node = nodes.FunctionDef(name=name or func.__name__,
                                  doc=inspect.getdoc(func),
                                  parent=parent)
    built_objects[id(func)] = func_node
    built_objects = _ChainMap({}, *built_objects.maps)
    try:
        signature = _signature(func)
    except (ValueError, TypeError):
        # signature() raises these errors for non-introspectable
        # callables.
        func_node.postinit(args=nodes.Unknown(parent=func_node), body=[])
        return func_node
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
    args = [nodes.AssignName(name=n, parent=args_node) for n in names]
    kwonlyargs = [nodes.AssignName(name=n, parent=args_node) for n in kwonlynames]
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
    if (id(container) in built_objects and
        built_objects[id(container)].targets[0].name == name):
        # return built_objects[id(container)]
        return nodes.Name(name=name, parent=parent)
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    try:
        container_node = BUILTIN_CONTAINERS[type(container)](parent=parent)
    except KeyError:
        for container_type in BUILTIN_CONTAINERS:
            if isinstance(container, container_type):
                container_node = BUILTIN_CONTAINERS[container_type](parent=parent)
    if name:
        node = parent
    else:
        node = container_node
    built_objects[id(container)] = node
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
    if (id(dictionary) in built_objects and
        built_objects[id(dictionary)].targets[0].name == name):
        # return built_objects[id(dictionary)]
        return nodes.Name(name=name, parent=parent)
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    dict_node = nodes.Dict(parent=parent)
    if name:
        node = parent
    else:
        node = dict_node
    built_objects[id(dictionary)] = node
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
def ast_from_builtin_number_text_binary(builtin_number_text_binary, built_objects, module, name=None, parent=None):
    if name:
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name, parent=parent)
    builtin_number_text_binary_node = nodes.Const(value=builtin_number_text_binary, parent=parent)
    if name:
        parent.postinit(targets=[name_node], value=builtin_number_text_binary_node)
        node = parent
    else:
        node = builtin_number_text_binary_node
    return node

if six.PY2:
    _ast_from_object.register(unicode, ast_from_builtin_number_text_binary)
    _ast_from_object.register(long, ast_from_builtin_number_text_binary)


@_ast_from_object.register(type(None))
@_ast_from_object.register(type(NotImplemented))
@_ast_from_object.register(bool)
def ast_from_builtin_singleton(builtin_singleton, built_objects, module, name=None, parent=None):
    # A builtin singleton is assigned to a name.
    if name and name != str(builtin_singleton):
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name=name, parent=parent)
    # This case handles the initial assignment of singletons to names
    # in the builtins module.  It can be triggered in other cases with
    # an object that contains a builtin singleton by its own name, but
    # there's never any reason to write that kind of code, and even if
    # it happens it shouldn't cause any harm.
    elif name and name == str(builtin_singleton):
        parent = nodes.ReservedName(name=name, parent=parent)
    builtin_singleton_node = nodes.NameConstant(value=builtin_singleton, parent=parent)
    if name and name != str(builtin_singleton):
        parent.postinit(targets=[name_node], value=builtin_singleton_node)
        node = parent
    elif name and name == str(builtin_singleton):
        parent.postinit(value=builtin_singleton_node)
        node = parent
    else:
        node = builtin_singleton_node
    return node

@_ast_from_object.register(type(Ellipsis))
def ast_from_ellipsis(ellipsis, built_objects, module, name=None, parent=None):
    if name and name != str(ellipsis):
        parent = nodes.Assign(parent=parent)
        name_node = nodes.AssignName(name=name, parent=parent)
    elif name and name == str(ellipsis):
        parent = nodes.ReservedName(name=name, parent=parent)
    ellipsis_node = nodes.Ellipsis(parent=parent)
    if name and name != str(ellipsis):
        parent.postinit(targets=[name_node], value=ellipsis_node)
        node = parent
    elif name and name == str(ellipsis):
        parent.postinit(value=ellipsis_node)
        node = parent
    else:
        node = ellipsis_node
    return node


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

BUILTIN_TYPES = {type(None): 'NoneType',
                 type(NotImplemented): 'NotImplementedType',
                 types.GeneratorType: 'GeneratorType',
                 types.FunctionType: 'FunctionType',
                 types.MethodType: 'MethodType',
                 types.BuiltinFunctionType: 'BuiltinFunctionType',
                 types.ModuleType: 'ModuleType'}

# Initialize the built_objects map for the builtins mock AST to ensure
# that the types are included as Name nodes, not explicit ASTs.
built_objects = _ChainMap({t: True for t in BUILTIN_TYPES})
astroid_builtin = _ast_from_object(six.moves.builtins,
                                   _ChainMap({t: True for t in BUILTIN_TYPES}),
                                   six.moves.builtins)
astroid_builtins = astroid_builtin

for builtin_type in BUILTIN_TYPES:
    # Now delete each builtin type from built_objects to ensure a real
    # AST for it is created by _ast_from_object.
    del built_objects[builtin_type]
    class_node = _ast_from_object(builtin_type, built_objects,
                                  six.moves.builtins)
    astroid_builtins.body.append(class_node)
    class_node.parent = astroid_builtins
