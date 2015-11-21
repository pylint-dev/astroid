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
import sys
import types

# This is a useful function for introspecting class attributes in
# inspect that is for some reason not exported.
from inspect import classify_class_attrs as _classify_class_attrs

try:
    from collections import ChainMap as _ChainMap
except ImportError:
    class _ChainMap(collections.MutableMapping):
        def __init__(self, *maps):
            self.maps = list(maps) or [{}]
        def __getitem__(self, key):
            for mapping in self.maps:
                if key in mapping:
                    return mapping[key]
            raise KeyError(key)
        def __setitem__(self, key, value):
            self.maps[0][key] = value
        def __delitem__(self, key):
            del self.maps[0][key]
        def __len__(self):
            return len(set().union(*self.maps))
        def __iter__(self):
            return iter(set().union(*self.maps))

try:
    from inspect import signature as _signature, Parameter as _Parameter
except ImportError:
    from funcsigs import signature as _signature, Parameter as _Parameter

import lazy_object_proxy
import six

from astroid.interpreter import objects
from astroid import manager
from astroid.tree import node_classes
from astroid.tree import scoped_nodes
from astroid import util


# TODO: handle the names of lambdas better, recurse into imported
# bases and metaclass.


MANAGER = manager.AstroidManager()

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
# to this type as "method-wrapper".  On CPython it's used for bound
# methods corresponding to unbound methods with the wrapper_descriptor
# type.
MethodWrapperType = type(object().__getattribute__)


def ast_from_object(object_, name=None):
    '''Returns a mock AST for a Python object.

    This function is intended for analyzing objects that aren't
    implemented in Python or that are created dynamically in ways that
    static analysis can't capture.  The mock AST this function returns
    has both more and less information than an AST created by
    processing Python code would: it includes special nodes
    representing objects only created at runtime but can't, for
    instance, know anything about the action of functions on their
    arguments.  It uses InterpreterObject nodes as containers to
    insert astroid objects representing runtime-only objects like
    Instances and FrozenSets.  ReservedNames are for special
    names in the builtins module and Unknown nodes are used in place
    of Arguments nodes for functions who arguments can't be
    introspected.

    This function returns an AST whose root is a node of a type
    appropriate to the object it was passed.  In some cases, this
    object may have links to other objects.  The only case where an
    AST will necessarily have a Module node as its root is when it's
    called on a Module.

    Args:
        object_ (Any): Any Python object.

    Returns:
        An AST representing the object and its attributes, methods, etc.

    Raises:
        TypeError: When called on an instance where it's not possible
            to construct an appropriate AST.

    '''
    return _ast_from_object(object_, _ChainMap({}),
                            inspect.getmodule(object_), name)[0]


@util.singledispatch
def _ast_from_object(instance, built_objects, module, name=None, parent=None):
    '''Returns a mock AST for an instance.

    This is the internal recursive generic function for building an
    AST from a runtime object.  Unlike for most generic functions,
    this implementation, for object, is not a stub, because this
    generic function needs to handle all kinds of Python objects.
    This implementation handles instances, but except where noted this
    documentation applies to all implementations of the generic
    function.

    Args:
        instance (Any): The Python object to return a mock AST for.
            This implementation should only receive instances, with all other
            objects directed to other implementations.
        built_objects (ChainMap): Maps id()s for objects to mock ASTs for
            objects, recording what objects already have a mock AST constructed.
            id() is used because not all Python objects are hashable.
            The internal maps of the ChainMap represent scopes within the object
            being recursed over, with a new map for each scope, to ensure that
            ASTs added in inner scopes are duplicated if necessary in other
            scopes.
        module (types.Module): The module of the root object, used to determine
            if any child objects come from different modules.
        name (str): The name the parent object uses for the a child object, if
            any.
        parent (NodeNG): The node corresponding to a parent object, if any.

    Returns:
        A Sequence of nodes representing the object and its attributes, methods,
        etc.

    Raises:
        TypeError: When called on an instance where it's not possible
            to construct an appropriate AST.

    '''
    # Since all Instances pointing to the same ClassDef are
    # identical, they can all share the same node.
    if name is not None and id(instance) in built_objects:
        return (_make_assignment(name, built_objects[id(instance)].name, parent),)

    # Since this ultimately inherits from object but not any type,
    # it's presumably an instance of some kind.
    cls = type(instance)
    result = list(_ast_from_object(cls, built_objects, module, parent=parent))

    # The type of an instance should always be some kind of type, and
    # ast_from_class should always return a sequence of nodes ending
    # with a ClassDef, ImportFrom, or Name node.
    node = result[-1]

    if isinstance(node, scoped_nodes.ClassDef):
        class_node = node
    elif isinstance(node, node_classes.ImportFrom):
        # TODO: this solution is not complete, because it doesn't add
        # instance attributes, but adding instance attributes to class
        # nodes causes problems in general and laziness in the
        # building system needs to be refactored in general.  Note
        # that encapsulating the instance attributes setting in a
        # function won't work, because it contains a call to
        # _ast_from_object, which takes a mutable object whose state
        # won't be preserved in a closure.
        def lazy_instance(node=node, cls=cls, name=name, parent=parent):
            # Handle ImportFrom chains.
            while True:
                try:
                    modname = node.modname
                except AttributeError:
                    # print(node, parent)
                    raise
                node = MANAGER.ast_from_module_name(modname).getattr(cls.__name__)[0]
                if isinstance(node, scoped_nodes.ClassDef):
                    # class_node = node
                    # break
                    return node_classes.InterpreterObject(name=name, object_=node.instantiate_class(), parent=parent)
        result.append(lazy_object_proxy.Proxy(lazy_instance))
        built_objects[id(instance)] = _NameAST(name, result[-1])
        return result
    elif isinstance(node, node_classes.Assign):
        # A Name node means a ClassDef node already exists somewhere,
        # so there's no need to add another one.
        class_node = built_objects[id(cls)].ast
        result = []
    else:
        raise TypeError('Unexpected node, %s, when calling _ast_from_object on '
                        'the type of %s.' % (node, instance))

    # Take the set difference of instance and class attributes.
    for name in set(dir(instance)) - set(dir(cls)):
        if name not in objects.Instance.special_attributes:
            ast = _ast_from_object(getattr(instance, name), built_objects,
                                   module, name=name, parent=parent)[0]
            class_node.instance_attrs[name].append(ast)

    # Create an instance of the class we just created an AST for.
    result.append(node_classes.InterpreterObject(name=name, object_=class_node.instantiate_class(), parent=parent))
    if name is not None:
        built_objects[id(instance)] = _NameAST(name, result[-1])
    return result


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(type)
def ast_from_class(cls, built_objects, module, name=None, parent=None):
    '''Handles classes and other types not handled explicitly elsewhere.'''
    # TODO: this can create duplicate objects
    if id(cls) in built_objects:
        return (_make_assignment(name or cls.__name__, built_objects[id(cls)].name, parent),)

    inspected_module = inspect.getmodule(cls)

    # In some situations, a class claims to be from a module but isn't
    # available in that module.  For example, the quit instance in
    # builtins is of type Quitter.  On Python 2, this claims its
    # module is site, but Quitter isn't in dir(site) or available as
    # site.Quitter. On Python3 in the REPL, Quitter claims its module
    # is _sitebuiltins, which actually does have a Quitter class
    # available.  However, when running the tests, Quitter again
    # claims its module is site, which still doesn't have it
    # available.  If this happens, this statement is ignored and an
    # appropriate ClassDef node is returned.  Arguably, it would be
    # possible to check if a class is in a module under another name,
    # but does this ever happen?
    if (inspected_module is not None and
        inspected_module is not module and
        hasattr(inspected_module, cls.__name__)):
        return (node_classes.ImportFrom(fromname=
                                 getattr(inspected_module, '__name__', None),
                                 names=[[cls.__name__, name]],
                                 parent=parent),)
    class_node = scoped_nodes.ClassDef(name=cls.__name__, doc=inspect.getdoc(cls), parent=parent)
    result = [class_node]
    if name is not None and name != cls.__name__:
        result.append(_make_assignment(name, cls.__name__, parent))
    built_objects[id(cls)] = _NameAST(cls.__name__, class_node)
    built_objects = _ChainMap({}, *built_objects.maps)
    bases = [node_classes.Name(name=b.__name__, parent=class_node)
             for b in cls.__bases__]
    body = [
        t for a in _classify_class_attrs(cls) if a.defining_class is cls and a.name not in scoped_nodes.ClassDef.special_attributes
        for t in _ast_from_object(a.object, built_objects, module, a.name, parent=class_node)]
    class_node.postinit(bases=bases, body=body, decorators=(),
                        newstyle=isinstance(cls, type))
    return result
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
    '''Handles functions, including all kinds of methods.'''
    if id(func) in built_objects:
        return (_make_assignment(name or func.__name__, built_objects[id(func)].name, parent),)
    inspected_module = inspect.getmodule(func)
    if inspected_module is not None and inspected_module is not module:
        return (node_classes.ImportFrom(
            fromname=getattr(inspected_module, '__name__', None),
            names=[[func.__name__, name]],
            parent=parent),)
    func_node = scoped_nodes.FunctionDef(name=func.__name__,
                                  doc=inspect.getdoc(func),
                                  parent=parent)
    result = [func_node]
    if name is not None and name != func.__name__:
        result.append(_make_assignment(name, func.__name__, parent))
    built_objects[id(func)] = _NameAST(func.__name__, func_node)
    built_objects = _ChainMap({}, *built_objects.maps)
    try:
        signature = _signature(func)
    except (ValueError, TypeError):
        # signature() raises these errors for non-introspectable
        # callables.
        func_node.postinit(args=node_classes.Unknown(parent=func_node), body=[])
        return (func_node,)
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
                defaults.extend(_ast_from_object(parameter.default, built_objects, module, parent=parent))
            if parameter.annotation is not _Parameter.empty:
                annotations.extend(_ast_from_object(parameter.annotation, built_objects, module, parent=parent))
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
    args_node = node_classes.Arguments(vararg=vararg_name, kwarg=kwarg_name, parent=func_node)

    # This ignores POSITIONAL_ONLY args, because they only appear in
    # functions implemented in C and can't be mimicked by any Python
    # function.
    names, defaults, annotations = extract_args(parameters.get(_Parameter.POSITIONAL_OR_KEYWORD, ()), args_node)
    kwonlynames, kw_defaults, kwonly_annotations = extract_args(parameters.get(_Parameter.KEYWORD_ONLY, ()), args_node)
    args = [node_classes.AssignName(name=n, parent=args_node) for n in names]
    kwonlyargs = [node_classes.AssignName(name=n, parent=args_node) for n in kwonlynames]
    if vararg_name and vararg[0].annotation is not _Parameter.empty:
        varargannotation = vararg.annotation
    else:
        varargannotation = None
    if kwarg_name and kwarg[0].annotation is not _Parameter.empty:
        kwargannotation = kwarg.annotation
    else:
        kwargannotation = None
    returns = None
    if signature.return_annotation is not _Parameter.empty:
        returns = _ast_from_object(signature.return_annotation,
                                   built_objects,
                                   module,
                                   parent=func_node)[0]
    args_node.postinit(args, defaults, kwonlyargs, kw_defaults,
                       annotations, kwonly_annotations,
                       varargannotation, kwargannotation)
    func_node.postinit(args=args_node, body=[], returns=returns)
    for name in set(dir(func)) - set(dir(type(func))):
        # This checks against method special attributes because
        # methods are also dispatched through this function.
        if name not in objects.BoundMethod.special_attributes:
            ast = _ast_from_object(getattr(func, name), built_objects,
                                   module, name=name, parent=parent)[0]
            func_node.instance_attrs[name].append(ast)
    return result


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(types.ModuleType)
def ast_from_module(module, built_objects, parent_module, name=None, parent=None):
    if id(module) in built_objects:
        return (_make_assignment(name, built_objects[id(module)].name, parent),)
    if module is not parent_module:
        # This module has been imported into another.

        # TODO: this works around an obscure issue in pylib/apikpkg,
        # https://pylib.readthedocs.org/en/latest/index.html /
        # https://bitbucket.org/hpk42/apipkg.  In its
        # __init__.py, pylib has the following line:

        # sys.modules['py.error'] = _apipkg.AliasModule("py.error", "py._error", 'error')

        # AliasModule is a very odd object that has a getattr method
        # that raises an AttributeError for, among other things,
        # __name__.  This probably doesn't comply with the contract
        # for things that should be in sys.modules.
        try:
            return (node_classes.Import([[module.__name__, name]], parent=parent),)
        except AttributeError:
            return ()
    try:
        source_file = inspect.getsourcefile(module)
    except TypeError:
        # inspect.getsourcefile raises TypeError for built-in modules.
        source_file = None
    module_node = scoped_nodes.Module(
        name=name or module.__name__,
        # inspect.getdoc returns None for modules without docstrings like
        # Jython Java modules.
        doc=inspect.getdoc(module),
        source_file=source_file,
        package=hasattr(module, '__path__'),
        # Assume that if inspect couldn't find a Python source file, it's
        # probably not implemented in pure Python.
        pure_python=bool(source_file))
    built_objects[id(module)] = _NameAST(module_node.name, module_node)
    built_objects = _ChainMap({}, *built_objects.maps)
    body = [
        t for n, m in inspect.getmembers(module) if n not in scoped_nodes.Module.special_attributes
        for t in _ast_from_object(m, built_objects, module, n, module_node)]
    module_node.postinit(body=body)
    return (module_node,)


BUILTIN_CONTAINERS = {list: node_classes.List, set: node_classes.Set, frozenset:
                      objects.FrozenSet, tuple: node_classes.Tuple}

# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(list)
@_ast_from_object.register(set)
@_ast_from_object.register(frozenset)
@_ast_from_object.register(tuple)
def ast_from_builtin_container(container, built_objects, module, name=None,
                               parent=None):
    '''Handles builtin container types except for mappings.'''
    if (id(container) in built_objects and
        built_objects[id(container)].name != name):
        return (_make_assignment(name, built_objects[id(container)].name, parent),)
    if name:
        parent = node_classes.Assign(parent=parent)
        name_node = node_classes.AssignName(name, parent=parent)
    try:
        container_node = BUILTIN_CONTAINERS[type(container)](parent=parent)
    except KeyError:
        for container_type in BUILTIN_CONTAINERS:
            if isinstance(container, container_type):
                container_node = BUILTIN_CONTAINERS[container_type](parent=parent)
                break
    if name:
        node = parent
    else:
        node = container_node
    if name is not None:
        built_objects[id(container)] = _NameAST(name, node)
    container_node.postinit(
        elts=[t for i in container
              for t in _ast_from_object(i, built_objects, module, parent=node)])
    if name:
        parent.postinit(targets=[name_node], value=container_node)
    return (node,)


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(dict)
def ast_from_dict(dictionary, built_objects, module, name=None,
                               parent=None):
    '''Handles dictionaries, including DictProxyType and MappingProxyType.'''
    if (id(dictionary) in built_objects and
        built_objects[id(dictionary)].name != name):
        return (_make_assignment(name, built_objects[id(dictionary)].name, parent),)
    if name:
        parent = node_classes.Assign(parent=parent)
        name_node = node_classes.AssignName(name, parent=parent)
    dict_node = node_classes.Dict(parent=parent)
    if name:
        node = parent
    else:
        node = dict_node
    if name is not None:
        built_objects[id(dictionary)] = _NameAST(name, node)
    dict_node.postinit(items=[
        # This explicit list construction works around an obscure
        # interaction: if _ast_from_dict is called on sys.modules and
        # sys.modules contains a module that alters sys.modules upon
        # import, as pytest.AliasModule does, then the recursive call
        # can alter sys.modules's items() while it's being iterated
        # over, causing a RuntimeError.
        (x, y) for k, v in list(dictionary.items())
        for x, y in zip(_ast_from_object(k, built_objects, module, parent=node),
                        _ast_from_object(v, built_objects, module, parent=node))])
    if name:
        parent.postinit(targets=[name_node], value=dict_node)
    return (node,)

if six.PY2:
    _ast_from_object.register(types.DictProxyType, ast_from_dict)
else:
    _ast_from_object.register(types.MappingProxyType, ast_from_dict)


# pylint: disable=unused-variable; doesn't understand singledispatch
@_ast_from_object.register(str)
@_ast_from_object.register(bytes)
@_ast_from_object.register(int)
@_ast_from_object.register(float)
@_ast_from_object.register(complex)
def ast_from_builtin_number_text_binary(builtin_number_text_binary, built_objects, module, name=None, parent=None):
    '''Handles the builtin numeric and text/binary sequence types.'''
    if (name is not None and id(builtin_number_text_binary) in built_objects and
        built_objects[id(builtin_number_text_binary)].name != name):
        return (_make_assignment(name, built_objects[id(builtin_number_text_binary)].name, parent),)
    if name:
        parent = node_classes.Assign(parent=parent)
        name_node = node_classes.AssignName(name, parent=parent)
    builtin_number_text_binary_node = node_classes.Const(value=builtin_number_text_binary, parent=parent)
    if name is not None:
        built_objects[id(builtin_number_text_binary)] = _NameAST(name, builtin_number_text_binary_node)
    if name:
        parent.postinit(targets=[name_node], value=builtin_number_text_binary_node)
        node = parent
    else:
        node = builtin_number_text_binary_node
    return (node,)

if six.PY2:
    _ast_from_object.register(unicode, ast_from_builtin_number_text_binary)
    _ast_from_object.register(long, ast_from_builtin_number_text_binary)


def ast_from_builtin_singleton_factory(node_class):
    '''A higher-order function for building functions for handling the
    builtin singleton types.

    Args:
        node_class (NodeNG): The constructor for the AST node for the builtin
        singleton.

    Returns:
        A function that handles the type corresponding to node_class.
    '''
    def ast_from_builtin_singleton(builtin_singleton, built_objects,
                                   module, name=None, parent=None,
                                   node_class=node_class):
        '''Handles builtin singletons, currently True, False, None,
        NotImplemented, and Ellipsis.'''
        if name and name != str(builtin_singleton):
            assign_node = node_classes.Assign(parent=parent)
            target_node = node_classes.AssignName(name, parent=assign_node)
            value_node = node_class(builtin_singleton, parent=assign_node)
            assign_node.postinit(targets=[target_node], value=value_node)
            return (assign_node,)
        else:
            return (node_class(builtin_singleton, parent=parent),)
    return ast_from_builtin_singleton

BUILTIN_SINGLETONS = {None: node_classes.NameConstant,
                      NotImplemented: node_classes.NameConstant,
                      False: node_classes.NameConstant,
                      True: node_classes.NameConstant,
                      Ellipsis: lambda value=None, parent=None:
                      node_classes.Ellipsis(parent=parent)}

for singleton, node_class in BUILTIN_SINGLETONS.items():
    _ast_from_object.register(type(singleton), ast_from_builtin_singleton_factory(node_class))


def _make_assignment(new_name, old_name, parent):
    assign_node = node_classes.Assign(parent=parent)
    target_node = node_classes.AssignName(new_name, parent=assign_node)
    value_node = node_classes.Name(old_name, parent=assign_node)
    assign_node.postinit(targets=[target_node], value=value_node)
    return assign_node

_NameAST = collections.namedtuple('_NameAST', 'name ast')


# @scoped_nodes.get_locals.register(Builtins)
# def scoped_node(node):
#     locals_ = collections.defaultdict(list)
#     for name in ('Ellipsis', 'False', 'None', 'NotImplemented',
#                  'True', '__debug__', '__package__', '__spec__', 'copyright',
#                  'credits', 'exit', 'help', 'license', 'quit'):
#         for child in (n for n in node.body if
#                      isinstance(n, (node_classes.Const, node_classes.InterpreterObject))):
#             if child.name == name:
#                 locals_[name].append(child)
#     for n in node.get_children():
#         scoped_nodes._get_locals(n, locals_)
#     return locals_


BUILTIN_TYPES = (types.GetSetDescriptorType,
                 types.MemberDescriptorType, type(None), type(NotImplemented),
                 types.GeneratorType, types.FunctionType, types.MethodType,
                 types.BuiltinFunctionType, types.ModuleType)

def ast_from_builtins():
    # Initialize the built_objects map for the builtins mock AST to ensure
    # that the types are included as Name nodes, not explicit ASTs.
    built_objects = _ChainMap({})
    for builtin_type in BUILTIN_TYPES:
        built_objects[id(builtin_type)] = _NameAST(builtin_type.__name__, _ast_from_object(builtin_type, built_objects, six.moves.builtins)[0])

    for singleton, node_class in BUILTIN_SINGLETONS.items():
        reserved_name = node_classes.ReservedName(name=str(singleton))
        singleton_node = node_class(value=singleton, parent=reserved_name)
        reserved_name.postinit(value=singleton_node)
        built_objects[id(singleton)] = _NameAST(str(singleton), reserved_name)

    builtins_ast = _ast_from_object(six.moves.builtins,
                                    built_objects,
                                    six.moves.builtins)[0]

    for builtin_type in BUILTIN_TYPES:
        type_node = built_objects[id(builtin_type)].ast
        builtins_ast.body.append(type_node)
        type_node.parent = builtins_ast

    for singleton, _ in BUILTIN_SINGLETONS.items():
        reserved_name = built_objects[id(singleton)].ast
        builtins_ast.body.append(reserved_name)
        reserved_name.parent = builtins_ast

    MANAGER.astroid_cache[six.moves.builtins.__name__] = builtins_ast
    return builtins_ast

builtins_ast = ast_from_builtins()
astroid_builtin = builtins_ast

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
