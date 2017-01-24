# Copyright (c) 2006-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2011, 2013-2015 Google, Inc.
# Copyright (c) 2013-2016 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015-2016 Cara Vinson <ceridwenv@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""
This module contains the classes for "scoped" node, i.e. which are opening a
new local scope in the language definition : Module, ClassDef, FunctionDef (and
Lambda, GeneratorExp, DictComp and SetComp to some extent).
"""

import sys
import collections
import io
import itertools
import warnings

try:
    from functools import singledispatch as _singledispatch
except ImportError:
    from singledispatch import singledispatch as _singledispatch

import six

from astroid.tree import base
from astroid import context as contextmod
from astroid import exceptions
from astroid import decorators as decorators_mod
from astroid.interpreter import lookup
from astroid.interpreter import objects
from astroid.interpreter import objectmodel
from astroid.interpreter import runtimeabc
from astroid.interpreter.util import infer_stmts
from astroid.interpreter import dunder_lookup
from astroid import manager
from astroid.tree import base as treebase
from astroid.tree import node_classes
from astroid.tree import treeabc
from astroid import util

MANAGER = manager.AstroidManager()


# TODO: remove this, this is for writing the necessary code only.
try:
    from types import MappingProxyType
except ImportError:
    from dictproxyhack import dictproxy as MappingProxyType


BUILTINS = six.moves.builtins.__name__
ITER_METHODS = ('__iter__', '__getitem__')


def _c3_merge(sequences, cls, context):
    """Merges MROs in *sequences* to a single MRO using the C3 algorithm.

    Adapted from http://www.python.org/download/releases/2.3/mro/.

    """
    result = []
    while True:
        sequences = [s for s in sequences if s]   # purge empty sequences
        if not sequences:
            return result
        for s1 in sequences:   # find merge candidates among seq heads
            candidate = s1[0]
            for s2 in sequences:
                if candidate in s2[1:]:
                    candidate = None
                    break      # reject the current head, it appears later
            else:
                break
        if not candidate:
            # Show all the remaining bases, which were considered as
            # candidates for the next mro sequence.
            raise exceptions.InconsistentMroError(
                message="Cannot create a consistent method resolution order "
                "for MROs {mros} of class {cls!r}.",
                mros=sequences, cls=cls, context=context)

        result.append(candidate)
        # remove the chosen candidate
        for seq in sequences:
            if seq[0] == candidate:
                del seq[0]


def _verify_duplicates_mro(sequences, cls, context):
    for sequence in sequences:
        names = [node.qname() for node in sequence]
        if len(names) != len(set(names)):
            raise exceptions.DuplicateBasesError(
                message='Duplicates found in MROs {mros} for {cls!r}.',
                mros=sequences, cls=cls, context=context)


def function_to_method(n, klass, klass_context):
    if isinstance(n, FunctionDef):
        if n.type == 'classmethod':
            return objects.BoundMethod(n, klass)
        if n.type != 'staticmethod':
            if six.PY2:
                return objects.UnboundMethod(n)
            else:
                if klass_context:
                    return n
                return objects.BoundMethod(n, klass)
    return n


class QualifiedNameMixin(object):

    def qname(node):
        """Return the 'qualified' name of the node."""
        if node.parent is None:
            return node.name
        return '%s.%s' % (node.parent.frame().qname(), node.name)


@util.register_implementation(treeabc.Module)
class Module(QualifiedNameMixin, lookup.LocalsDictNode):
    _astroid_fields = ('body',)

    fromlineno = 0
    lineno = 0

    # attributes below are set by the builder module or by raw factories

    # the file from which as been extracted the astroid representation. It may
    # be None if the representation has been built from a built-in module
    source_file = None
    # Alternatively, if built from a string/bytes, this can be set
    source_code = None
    # encoding of python source file, so we can get unicode out of it (python2
    # only)
    file_encoding = None
    # the module name
    name = None
    # boolean for astroid built from source (i.e. ast)
    pure_python = None
    # boolean for package module
    package = None

    special_attributes = objectmodel.ModuleModel()

    # names of module attributes available through the global scope
    scope_attrs = frozenset(('__name__', '__doc__', '__file__', '__path__'))

    if six.PY2:
        _other_fields = ('name', 'doc', 'file_encoding', 'package',
                         'pure_python', 'source_code', 'source_file')
    else:
        _other_fields = ('name', 'doc', 'package', 'pure_python',
                         'source_code', 'source_file')
    # _other_other_fields = ('locals', 'globals')

    def __init__(self, name, doc, package=None, parent=None,
                 pure_python=True, source_code=None, source_file=None):
        self.name = name
        self.doc = doc
        self.package = package
        self.parent = parent
        self.pure_python = pure_python
        self.source_code = source_code
        self.source_file = source_file
        self.body = []
        self.external_attrs = collections.defaultdict(list)

    def postinit(self, body=None):
        self.body = body

    @property
    def globals(self):
        return MappingProxyType(lookup.get_locals(self))

    @property
    def future_imports(self):
        index = 0
        future_imports = []

        # The start of a Python module has an optional docstring
        # followed by any number of `from __future__ import`
        # statements.  This doesn't try to test for incorrect ASTs,
        # but should function on all correct ones.
        while (index < len(self.body)):
            if (isinstance(self.body[index], node_classes.ImportFrom)
                and self.body[index].modname == '__future__'):
                # This is a `from __future__ import` statement.
                future_imports.extend(n[0] for n in getattr(self.body[index],
                                                            'names', ()))
            elif (index == 0 and isinstance(self.body[0], node_classes.Expr)):
                # This is a docstring, so do nothing.
                pass
            else:
                # This is some other kind of statement, so the future
                # imports must be finished.
                break
            index += 1
        return frozenset(future_imports)

    def _get_stream(self):
        if self.source_code is not None:
            return io.BytesIO(self.source_code)
        if self.source_file is not None:
            stream = open(self.source_file, 'rb')
            return stream
        return None

    def stream(self):
        """Get a stream to the underlying file or bytes."""
        return self._get_stream()

    def block_range(self, lineno):
        """return block line numbers.

        start from the beginning whatever the given lineno
        """
        return self.fromlineno, self.tolineno

    def scope_lookup(self, node, name, offset=0):
        if name in self.scope_attrs and name not in self.locals:
            try:
                return self, self.getattr(name)
            except exceptions.AttributeInferenceError:
                return self, ()
        return self._scope_lookup(node, name, offset)

    def pytype(self):
        return '%s.module' % BUILTINS

    def display_type(self):
        return 'Module'

    def getattr(self, name, context=None, ignore_locals=False):
        result = []
        name_in_locals = name in self.locals

        if name in self.special_attributes and not ignore_locals and not name_in_locals:
            result = [self.special_attributes.lookup(name)]
        elif not ignore_locals and name_in_locals:
            result = self.locals[name]
        # TODO: should ignore_locals also affect external_attrs?
        elif name in self.external_attrs:
            return self.external_attrs[name]
        elif self.package:
            try:
                result = [self.import_module(name, relative_only=True)]
            except (exceptions.AstroidBuildingError, SyntaxError):
                util.reraise(exceptions.AttributeInferenceError(target=self,
                                                                attribute=name,
                                                                context=context))
        result = [n for n in result if not isinstance(n, node_classes.DelName)]
        if result:
            return result
        raise exceptions.AttributeInferenceError(target=self, attribute=name,
                                                 context=context)

    def igetattr(self, name, context=None):
        """inferred getattr"""
        # set lookup name since this is necessary to infer on import nodes for
        # instance
        context = contextmod.copy_context(context)
        context.lookupname = name
        try:
            stmts = self.getattr(name, context)
            return infer_stmts(stmts, context, frame=self)
        except exceptions.AttributeInferenceError as error:
            structured = exceptions.InferenceError(error.message, target=self,
                                                   attribute=name, context=context)
            util.reraise(structured)

    def fully_defined(self):
        """return True if this module has been built from a .py file
        and so contains a complete representation including the code
        """
        return self.file is not None and self.file.endswith('.py')

    def statement(self):
        """return the first parent node marked as statement node
        consider a module as a statement...
        """
        return self

    def previous_sibling(self):
        """module has no sibling"""
        return

    def next_sibling(self):
        """module has no sibling"""
        return

    if six.PY2:
        @decorators_mod.cachedproperty
        def _absolute_import_activated(self):
            return 'absolute_import' in self.future_imports
    else:
        _absolute_import_activated = True

    def absolute_import_activated(self):
        return self._absolute_import_activated

    def import_module(self, modname, relative_only=False, level=None):
        """import the given module considering self as context"""
        if relative_only and level is None:
            level = 0
        absmodname = self.relative_to_absolute_name(modname, level)

        try:
            return MANAGER.ast_from_module_name(absmodname)
        except exceptions.AstroidBuildingError:
            # we only want to import a sub module or package of this module,
            # skip here
            if relative_only:
                raise
        return MANAGER.ast_from_module_name(modname)

    def relative_to_absolute_name(self, modname, level):
        """return the absolute module name for a relative import.

        The relative import can be implicit or explicit.
        """
        # XXX this returns non sens when called on an absolute import
        # like 'pylint.checkers.astroid.utils'
        # XXX doesn't return absolute name if self.name isn't absolute name
        if self.absolute_import_activated() and level is None:
            return modname
        if level:
            if self.package:
                level = level - 1
            if level and self.name.count('.') < level:
                raise exceptions.TooManyLevelsError(
                    level=level, name=self.name)

            package_name = self.name.rsplit('.', level)[0]
        elif self.package:
            package_name = self.name
        else:
            package_name = self.name.rsplit('.', 1)[0]

        if package_name:
            if not modname:
                return package_name
            return '%s.%s' % (package_name, modname)
        return modname

    def public_names(self):
        """Get the list of the names which are publicly available in this module."""
        return [name for name in self.keys() if not name.startswith('_')]

    def bool_value(self):
        return True


class ComprehensionScope(lookup.LocalsDictNode):
    def frame(self):
        return self.parent.frame()

    scope_lookup = lookup.LocalsDictNode._scope_lookup


@util.register_implementation(treeabc.GeneratorExp)
class GeneratorExp(ComprehensionScope):
    _astroid_fields = ('elt', 'generators')
    # _other_other_fields = ('locals',)
    elt = None
    generators = None

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(GeneratorExp, self).__init__(lineno, col_offset, parent)

    def postinit(self, elt=None, generators=None):
        self.elt = elt
        if generators is None:
            self.generators = []
        else:
            self.generators = generators

    def bool_value(self):
        return True


@util.register_implementation(treeabc.DictComp)
class DictComp(ComprehensionScope):
    _astroid_fields = ('key', 'value', 'generators')
    # _other_other_fields = ('locals',)
    key = None
    value = None
    generators = None

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(DictComp, self).__init__(lineno, col_offset, parent)

    def postinit(self, key=None, value=None, generators=None):
        self.key = key
        self.value = value
        if generators is None:
            self.generators = []
        else:
            self.generators = generators

    def bool_value(self):
        return util.Uninferable


@util.register_implementation(treeabc.SetComp)
class SetComp(ComprehensionScope):
    _astroid_fields = ('elt', 'generators')
    # _other_other_fields = ('locals',)
    elt = None
    generators = None

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(SetComp, self).__init__(lineno, col_offset, parent)

    def postinit(self, elt=None, generators=None):
        self.elt = elt
        if generators is None:
            self.generators = []
        else:
            self.generators = generators

    def bool_value(self):
        return util.Uninferable


@util.register_implementation(treeabc.ListComp)
class _ListComp(treebase.NodeNG):
    """class representing a ListComp node"""
    _astroid_fields = ('elt', 'generators')
    elt = None
    generators = None

    def postinit(self, elt=None, generators=None):
        self.elt = elt
        self.generators = generators

    def bool_value(self):
        return util.Uninferable


if six.PY3:
    class ListComp(_ListComp, ComprehensionScope):
        """class representing a ListComp node"""
        # _other_other_fields = ('locals',)

        def __init__(self, lineno=None, col_offset=None, parent=None):
            super(ListComp, self).__init__(lineno, col_offset, parent)
else:
    class ListComp(_ListComp):
        """class representing a ListComp node"""


def _infer_decorator_callchain(node):
    """Detect decorator call chaining and see if the end result is a
    static or a classmethod.
    """
    if not isinstance(node, FunctionDef):
        return
    if not node.parent:
        return
    try:
        # TODO: We don't handle multiple inference results right now,
        #       because there's no flow to reason when the return
        #       is what we are looking for, a static or a class method.
        result = next(node.infer_call_result(node.parent))
    except (StopIteration, exceptions.InferenceError):
        return
    if isinstance(result, objects.Instance):
        result = result._proxied
    if isinstance(result, ClassDef):
        if result.is_subtype_of('%s.classmethod' % BUILTINS):
            return 'classmethod'
        if result.is_subtype_of('%s.staticmethod' % BUILTINS):
            return 'staticmethod'

class CallSite(object):
    """Class for understanding arguments passed into a call site

    It needs a call context, which contains the arguments and the
    keyword arguments that were passed into a given call site.
    In order to infer what an argument represents, call
    :meth:`infer_argument` with the corresponding function node
    and the argument name.
    """

    def __init__(self, funcnode, args, keywords):
        self._funcnode = funcnode
        self.duplicated_keywords = set()
        self._unpacked_args = self._unpack_args(args)
        self._unpacked_kwargs = self._unpack_keywords(keywords)

        self.positional_arguments = [
            arg for arg in self._unpacked_args
            if arg is not util.Uninferable
        ]
        self.keyword_arguments = {
            key: value for key, value in self._unpacked_kwargs.items()
            if value is not util.Uninferable
        }

    def __repr__(self):
        string = '{name}(funcnode={funcnode}, args={args}, keywords={keywords})'
        return string.format(name=type(self).__name__,
                             funcnode=self._funcnode,
                             args=self.positional_arguments,
                             keywords=self.keyword_arguments)


    def has_invalid_arguments(self):
        """Check if in the current CallSite were passed *invalid* arguments

        This can mean multiple things. For instance, if an unpacking
        of an invalid object was passed, then this method will return True.
        Other cases can be when the arguments can't be inferred by astroid,
        for example, by passing objects which aren't known statically.
        """
        return len(self.positional_arguments) != len(self._unpacked_args)

    def has_invalid_keywords(self):
        """Check if in the current CallSite were passed *invalid* keyword arguments

        For instance, unpacking a dictionary with integer keys is invalid
        (**{1:2}), because the keys must be strings, which will make this
        method to return True. Other cases where this might return True if
        objects which can't be inferred were passed.
        """
        return len(self.keyword_arguments) != len(self._unpacked_kwargs)

    def _unpack_keywords(self, keywords):
        values = {}
        context = contextmod.InferenceContext()
        for name, value in keywords:
            if name is None:
                # Then it's an unpacking operation (**)
                try:
                    inferred = next(value.infer(context=context))
                except exceptions.InferenceError:
                    values[name] = util.Uninferable
                    continue

                if not isinstance(inferred, treeabc.Dict):
                    # Not something we can work with.
                    values[name] = util.Uninferable
                    continue

                for dict_key, dict_value in inferred.items:
                    try:
                        dict_key = next(dict_key.infer(context=context))
                    except exceptions.InferenceError:
                        values[name] = util.Uninferable
                        continue
                    if not isinstance(dict_key, treeabc.Const):
                        values[name] = util.Uninferable
                        continue
                    if not isinstance(dict_key.value, six.string_types):
                        values[name] = util.Uninferable
                        continue
                    if dict_key.value in values:
                        # The name is already in the dictionary
                        values[dict_key.value] = util.Uninferable
                        self.duplicated_keywords.add(dict_key.value)
                        continue
                    values[dict_key.value] = dict_value
            else:
                values[name] = value
        return values

    @staticmethod
    def _unpack_args(args):
        values = []
        context = contextmod.InferenceContext()
        for arg in args:
            if isinstance(arg, treeabc.Starred):
                try:
                    inferred = next(arg.value.infer(context=context))
                except exceptions.InferenceError:
                    values.append(util.Uninferable)
                    continue

                if inferred is util.Uninferable:
                    values.append(util.Uninferable)
                    continue
                if not hasattr(inferred, 'elts'):
                    values.append(util.Uninferable)
                    continue
                values.extend(inferred.elts)
            else:
                values.append(arg)
        return values

    def infer_argument(self, name, context):
        """infer a function argument value according to the call context

        Arguments:
            funcnode: The function being called.
            name: The name of the argument whose value is being inferred.
            context: TODO
        """
        if name in self.duplicated_keywords:
            raise exceptions.InferenceError('The arguments passed to {func!r} '
                                            ' have duplicate keywords.',
                                            call_site=self, func=self._funcnode,
                                            arg=name, context=context)

        # Look into the keywords first, maybe it's already there.
        try:
            return self.keyword_arguments[name].infer(context)
        except KeyError:
            pass

        # Too many arguments given and no variable arguments.
        if len(self.positional_arguments) > len(self._funcnode.args.positional_and_keyword):
            if not self._funcnode.args.vararg:
                raise exceptions.InferenceError('Too many positional arguments '
                                                'passed to {func!r} that does '
                                                'not have *args.',
                                                call_site=self, func=self._funcnode,
                                                arg=name, context=context)

        positional = self.positional_arguments[:len(self._funcnode.args.positional_and_keyword)]
        vararg = self.positional_arguments[len(self._funcnode.args.positional_and_keyword):]
        argindex = self._funcnode.args.find_argname(name)[0]
        kwonlyargs = set(arg.name for arg in self._funcnode.args.keyword_only)
        kwargs = {
            key: value for key, value in self.keyword_arguments.items()
            if key not in kwonlyargs
        }
        # If there are too few positionals compared to
        # what the function expects to receive, check to see
        # if the missing positional arguments were passed
        # as keyword arguments and if so, place them into the
        # positional args list.
        if len(positional) < len(self._funcnode.args.positional_and_keyword):
            for func_arg in self._funcnode.args.positional_and_keyword:
                if func_arg.name in kwargs:
                    arg = kwargs.pop(func_arg.name)
                    positional.append(arg)

        if argindex is not None:
            # 2. first argument of instance/class method
            if argindex == 0 and self._funcnode.type in ('method', 'classmethod'):
                if context.boundnode is not None:
                    boundnode = context.boundnode
                else:
                    # XXX can do better ?
                    boundnode = self._funcnode.parent.frame()

                if isinstance(boundnode, ClassDef):
                    # Verify that we're accessing a method
                    # of the metaclass through a class, as in
                    # `cls.metaclass_method`. In this case, the
                    # first argument is always the class. 
                    method_scope = self._funcnode.parent.scope()
                    if method_scope is boundnode.metaclass():
                        return iter((boundnode, ))

                if self._funcnode.type == 'method':
                    if not isinstance(boundnode, runtimeabc.Instance):
                        boundnode = objects.Instance(boundnode)
                    return iter((boundnode,))
                if self._funcnode.type == 'classmethod':
                    return iter((boundnode,))
            # if we have a method, extract one position
            # from the index, so we'll take in account
            # the extra parameter represented by `self` or `cls`
            if self._funcnode.type in ('method', 'classmethod'):
                argindex -= 1
            # 2. search arg index
            try:
                return self.positional_arguments[argindex].infer(context)
            except IndexError:
                pass

        if self._funcnode.args.kwarg and self._funcnode.args.kwarg.name == name:
            # It wants all the keywords that were passed into
            # the call site.
            if self.has_invalid_keywords():
                raise exceptions.InferenceError(
                    "Inference failed to find values for all keyword arguments "
                    "to {func!r}: {unpacked_kwargs!r} doesn't correspond to "
                    "{keyword_arguments!r}.",
                    keyword_arguments=self.keyword_arguments,
                    unpacked_kwargs=self._unpacked_kwargs,
                    call_site=self, func=self._funcnode, arg=name, context=context)
                
            kwarg = node_classes.Dict(lineno=self._funcnode.args.lineno,
                                      col_offset=self._funcnode.args.col_offset,
                                      parent=self._funcnode.args)
            items = [(node_classes.Const(key, parent=kwarg), value)
                     for key, value in kwargs.items()]
            keys, values = zip(*items)
            kwarg.postinit(keys, values)
            return iter((kwarg, ))

        if self._funcnode.args.vararg and self._funcnode.args.vararg.name == name:
            # It wants all the args that were passed into
            # the call site.
            if self.has_invalid_arguments():
                raise exceptions.InferenceError(
                    "Inference failed to find values for all positional "
                    "arguments to {func!r}: {unpacked_args!r} doesn't "
                    "correspond to {positional_arguments!r}.",
                    positional_arguments=self.positional_arguments,
                    unpacked_args=self._unpacked_args,
                    call_site=self, func=self._funcnode, arg=name, context=context)

            args = node_classes.Tuple(lineno=self._funcnode.args.lineno,
                                      col_offset=self._funcnode.args.col_offset,
                                      parent=self._funcnode.args)
            args.postinit(vararg)
            return iter((args, ))

        # Check if it's a default parameter.
        try:
            return self._funcnode.args.default_value(name).infer(context)
        except exceptions.NoDefault:
            pass
        raise exceptions.InferenceError('No value found for argument {name} to '
                                        '{func!r}', call_site=self,
                                        func=self._funcnode, arg=name, context=context)


class LambdaFunctionMixin(QualifiedNameMixin, base.FilterStmtsMixin):
    """Common code for lambda and functions."""

    def called_with(self, args, keywords):
        """Get a CallSite object with the given arguments

        Given these arguments, this will return an object
        which considers them as being passed into the current function,
        which can then be used to infer their values.
        `args` needs to be a list of arguments, while `keywords`
        needs to be a list of tuples, where each tuple is formed
        by a keyword name and a keyword value.
        """
        return CallSite(self, args, keywords)

    def scope_lookup(self, node, name, offset=0):
        
        if node in itertools.chain((self.args.positional_and_keyword,
                                    self.args.keyword_only)):
            frame = self.parent.frame()
            # line offset to avoid that def func(f=func) resolve the default
            # value to the defined function
            offset = -1
        else:
            # check this is not used in function decorators
            frame = self
        return frame._scope_lookup(node, name, offset)

    def argnames(self):
        """return a list of argument names"""
        if self.args.positional_and_keyword: # maybe None with builtin functions
            names = _rec_get_names(self.args.positional_and_keyword)
        else:
            names = []
        if self.args.vararg:
            names.append(self.args.vararg.name)
        if self.args.kwarg:
            names.append(self.args.kwarg.name)
        if self.args.keyword_only:
            names.extend([arg.name for arg in self.keyword_only])
        return names

    def callable(self):
        return True

    def bool_value(self):
        return True


@util.register_implementation(treeabc.Lambda)
class Lambda(LambdaFunctionMixin, lookup.LocalsDictNode):
    _astroid_fields = ('args', 'body',)
    _other_other_fields = ('locals',)
    name = '<lambda>'

    # function's type, 'function' | 'method' | 'staticmethod' | 'classmethod'
    @property
    def type(self):
        if self.args.args and self.args.args[0].name == 'self':
            if isinstance(self.parent.scope(), ClassDef):
                return 'method'
        return 'function'

    def __init__(self, lineno=None, col_offset=None, parent=None):
        self.args = []
        self.body = []
        self.instance_attrs = collections.defaultdict(list)
        super(Lambda, self).__init__(lineno, col_offset, parent)

    def postinit(self, args, body):
        self.args = args
        self.body = body

    # @property
    # def instance_attrs(self):
    #     return MappingProxyType(get_external_assignments(self, collections.defaultdict(list)))

    def pytype(self):
        return '%s.function' % BUILTINS

    def display_type(self):
        return 'Function'

    def infer_call_result(self, caller, context=None):
        """infer what a function is returning when called"""
        return self.body.infer(context)


@util.register_implementation(treeabc.FunctionDef)
class FunctionDef(LambdaFunctionMixin, lookup.LocalsDictNode,
                  node_classes.Statement):
    '''Setting FunctionDef.args to Unknown, rather than an Arguments node,
    means that the corresponding function's arguments are unknown,
    probably because it represents a function implemented in C or that
    is otherwise not introspectable.

    '''

    if six.PY3:
        _astroid_fields = ('decorators', 'args', 'returns', 'body')
        returns = None
    else:
        _astroid_fields = ('decorators', 'args', 'body')
    decorators = None

    special_attributes = objectmodel.FunctionModel()
    is_function = True
    # attributes below are set by the builder module or by raw factories
    _other_fields = ('name', 'doc')
    # _other_other_fields = ('locals', '_type')
    _other_other_fields = ('_type')
    _type = None

    def __init__(self, name=None, doc=None, lineno=None,
                 col_offset=None, parent=None):
        self.name = name
        self.doc = doc
        self.instance_attrs = collections.defaultdict(list)
        super(FunctionDef, self).__init__(lineno, col_offset, parent)

    # pylint: disable=arguments-differ; different than Lambdas
    def postinit(self, args, body, decorators=None, returns=None):
        self.args = args
        self.body = body
        self.decorators = decorators
        self.returns = returns

    def pytype(self):
        if 'method' in self.type:
            return '%s.instancemethod' % BUILTINS
        return '%s.function' % BUILTINS

    def display_type(self):
        if 'method' in self.type:
            return 'Method'
        return 'Function'

    @decorators_mod.cachedproperty
    def extra_decorators(self):
        """Get the extra decorators that this function can haves
        Additional decorators are considered when they are used as
        assignments, as in `method = staticmethod(method)`.
        The property will return all the callables that are used for
        decoration.
        """
        frame = self.parent.frame()
        if not isinstance(frame, ClassDef):
            return []

        decorators = []
        for assign in frame.nodes_of_class(node_classes.Assign):
            if (isinstance(assign.value, node_classes.Call)
                    and isinstance(assign.value.func, node_classes.Name)):
                for assign_node in assign.targets:
                    if not isinstance(assign_node, node_classes.AssignName):
                        # Support only `name = callable(name)`
                        continue

                    if assign_node.name != self.name:
                        # Interested only in the assignment nodes that
                        # decorates the current method.
                        continue
                    try:
                        meth = frame[self.name]
                    except KeyError:
                        continue
                    else:
                        # Must be a function and in the same frame as the
                        # original method.
                        if (isinstance(meth, FunctionDef)
                                and assign_node.frame() == frame):
                            decorators.append(assign.value)
        return decorators

    @decorators_mod.cachedproperty
    def type(self):
        """Get the function type for this node.

        Possible values are: method, function, staticmethod, classmethod.
        """
        builtin_descriptors = {'classmethod', 'staticmethod'}

        for decorator in self.extra_decorators:
            if decorator.func.name in builtin_descriptors:
                return decorator.func.name

        frame = self.parent.frame()
        type_name = 'function'
        if isinstance(frame, ClassDef):
            if self.name == '__new__':
                return 'classmethod'
            elif sys.version_info >= (3, 6) and self.name == '__init_subclass__':
                return 'classmethod'
            else:
                type_name = 'method'

        if not self.decorators:
            return type_name

        for node in self.decorators.nodes:
            if isinstance(node, node_classes.Name):
                if node.name in builtin_descriptors:
                    return node.name

            if isinstance(node, node_classes.Call):
                # Handle the following case:
                # @some_decorator(arg1, arg2)
                # def func(...)
                #
                try:
                    current = next(node.func.infer())
                except exceptions.InferenceError:
                    continue
                _type = _infer_decorator_callchain(current)
                if _type is not None:
                    return _type

            try:
                for inferred in node.infer():
                    # Check to see if this returns a static or a class method.
                    _type = _infer_decorator_callchain(inferred)
                    if _type is not None:
                        return _type

                    if not isinstance(inferred, ClassDef):
                        continue
                    for ancestor in inferred.ancestors():
                        if not isinstance(ancestor, ClassDef):
                            continue
                        if ancestor.is_subtype_of('%s.classmethod' % BUILTINS):
                            return 'classmethod'
                        elif ancestor.is_subtype_of('%s.staticmethod' % BUILTINS):
                            return 'staticmethod'
            except exceptions.InferenceError:
                pass
        return type_name

    @decorators_mod.cachedproperty
    def fromlineno(self):
        # lineno is the line number of the first decorator, we want the def
        # statement lineno
        lineno = self.lineno
        if self.decorators is not None:
            lineno += sum(node.tolineno - node.lineno + 1
                          for node in self.decorators.nodes)

        return lineno

    @decorators_mod.cachedproperty
    def blockstart_tolineno(self):
        return self.args.tolineno

    def block_range(self, lineno):
        """return block line numbers.

        start from the "def" position whatever the given lineno
        """
        return self.fromlineno, self.tolineno

    def getattr(self, name, context=None):
        """this method doesn't look in the instance_attrs dictionary since it's
        done by an Instance proxy at inference time.
        """
        if name in self.instance_attrs:
            return self.instance_attrs[name]
        if name in self.special_attributes:
            return [self.special_attributes.lookup(name)]
        raise exceptions.AttributeInferenceError(target=self, attribute=name)

    def igetattr(self, name, context=None):
        """Inferred getattr, which returns an iterator of inferred statements."""
        try:
            stmts = self.getattr(name, context)
            return infer_stmts(stmts, context, frame=self)
        except exceptions.AttributeInferenceError as error:
            structured = exceptions.InferenceError(error.message, target=self,
                                                   attribute=name,
                                                   context=context)
            util.reraise(structured)

    def is_method(self):
        """return true if the function node should be considered as a method"""
        # check we are defined in a ClassDef, because this is usually expected
        # (e.g. pylint...) when is_method() return True
        return self.type != 'function' and isinstance(self.parent.frame(), ClassDef)

    @decorators_mod.cached
    def decoratornames(self):
        """return a list of decorator qualified names"""
        result = set()
        decoratornodes = []
        if self.decorators is not None:
            # pylint: disable=unsupported-binary-operation; damn flow control.
            decoratornodes += self.decorators.nodes
        decoratornodes += self.extra_decorators
        for decnode in decoratornodes:
            try:
                for infnode in decnode.infer():
                    result.add(infnode.qname())
            except exceptions.InferenceError:
                continue
        return result

    def is_bound(self):
        """return true if the function is bound to an Instance or a class"""
        return self.type == 'classmethod'

    def is_abstract(self, pass_is_abstract=True):
        """Returns True if the method is abstract.

        A method is considered abstract if
         - the only statement is 'raise NotImplementedError', or
         - the only statement is 'pass' and pass_is_abstract is True, or
         - the method is annotated with abc.astractproperty/abc.abstractmethod
        """
        if self.decorators:
            for node in self.decorators.nodes:
                try:
                    inferred = next(node.infer())
                except exceptions.InferenceError:
                    continue
                if inferred and inferred.qname() in ('abc.abstractproperty',
                                                     'abc.abstractmethod'):
                    return True

        for child_node in self.body:
            if isinstance(child_node, node_classes.Raise):
                if child_node.raises_not_implemented():
                    return True
            return pass_is_abstract and isinstance(child_node, node_classes.Pass)
        # empty function is the same as function with a single "pass" statement
        if pass_is_abstract:
            return True

    def is_generator(self):
        """return true if this is a generator function"""
        yield_nodes = (node_classes.Yield, node_classes.YieldFrom)
        return next(self.nodes_of_class(yield_nodes,
                                        skip_klass=(FunctionDef, Lambda)), False)

    def infer_call_result(self, caller, context=None):
        """infer what a function is returning when called"""
        if self.is_generator():
            yield objects.Generator(self)
            return
        # This is really a gigantic hack to work around metaclass
        # generators that return transient class-generating
        # functions. Pylint's AST structure cannot handle a base class
        # object that is only used for calling __new__, but does not
        # contribute to the inheritance structure itself. We inject a
        # fake class into the hierarchy here for several well-known
        # metaclass generators, and filter it out later.
        if (self.name == 'with_metaclass' and
                len(self.args.args) == 1 and
                self.args.vararg is not None):
            metaclass = next(caller.args[0].infer(context))
            if isinstance(metaclass, ClassDef):
                c = ClassDef('temporary_class', None)
                c.hide = True
                c.parent = self
                class_bases = [next(b.infer(context)) for b in caller.args[1:]]
                c.bases = [base for base in class_bases if base != util.Uninferable]
                c._metaclass = metaclass
                yield c
                return
        returns = self.nodes_of_class(node_classes.Return, skip_klass=FunctionDef)
        for returnnode in returns:
            if returnnode.value is None:
                yield node_classes.NameConstant(None)
            else:
                try:
                    for inferred in returnnode.value.infer(context):
                        yield inferred
                except exceptions.InferenceError:
                    yield util.Uninferable


@util.register_implementation(treeabc.AsyncFunctionDef)
class AsyncFunctionDef(FunctionDef):
    """Asynchronous function created with the `async` keyword."""


def _rec_get_names(args, names=None):
    """return a list of all argument names"""
    if names is None:
        names = []
    for arg in args:
        if isinstance(arg, node_classes.Tuple):
            _rec_get_names(arg.elts, names)
        else:
            names.append(arg.name)
    return names


def _is_metaclass(klass, seen=None):
    """ Return if the given class can be
    used as a metaclass.
    """
    if klass.name == 'type':
        return True
    if seen is None:
        seen = set()
    for base in klass.bases:
        try:
            for baseobj in base.infer():
                baseobj_name = baseobj.qname()
                if baseobj_name in seen:
                    continue
                else:
                    seen.add(baseobj_name)
                if isinstance(baseobj, objects.Instance):
                    # not abstract
                    return False
                if baseobj is util.Uninferable:
                    continue
                if baseobj is klass:
                    continue
                if not isinstance(baseobj, ClassDef):
                    continue
                if baseobj._type == 'metaclass':
                    return True
                if _is_metaclass(baseobj, seen):
                    return True
        except exceptions.InferenceError:
            continue
    return False


def _class_type(klass, ancestors=None):
    """return a ClassDef node type to differ metaclass and exception
    from 'regular' classes
    """
    # XXX we have to store ancestors in case we have a ancestor loop
    if klass._type is not None:
        return klass._type
    if _is_metaclass(klass):
        klass._type = 'metaclass'
    elif klass.name.endswith('Exception'):
        klass._type = 'exception'
    else:
        if ancestors is None:
            ancestors = set()
        klass_name = klass.qname()
        if klass_name in ancestors:
            # XXX we are in loop ancestors, and have found no type
            klass._type = 'class'
            return 'class'
        ancestors.add(klass_name)
        for base in klass.ancestors(recurs=False):
            name = _class_type(base, ancestors)
            if name != 'class':
                if name == 'metaclass' and not _is_metaclass(klass):
                    # don't propagate it if the current class
                    # can't be a metaclass
                    continue
                klass._type = base.type
                break
    if klass._type is None:
        klass._type = 'class'
    return klass._type


def get_wrapping_class(node):
    """Obtain the class that *wraps* this node

    We consider that a class wraps a node if the class
    is a parent for the said node.
    """

    klass = node.frame()
    while klass is not None and not isinstance(klass, ClassDef):
        if klass.parent is None:
            klass = None
        else:
            klass = klass.parent.frame()
    return klass



@util.register_implementation(treeabc.ClassDef)
class ClassDef(QualifiedNameMixin, base.FilterStmtsMixin,
               lookup.LocalsDictNode,
               node_classes.Statement):

    # some of the attributes below are set by the builder module or
    # by a raw factories

    _astroid_fields = ('decorators', 'bases', 'body')

    decorators = None
    special_attributes = objectmodel.ClassModel()

    _type = None
    _metaclass_hack = False
    hide = False
    type = property(_class_type,
                    doc="class'type, possible values are 'class' | "
                    "'metaclass' | 'exception'")
    _other_fields = ('name', 'doc')
    _other_other_fields = ('_newstyle', 'instance_attrs', 'external_attrs')
    _newstyle = None

    def __init__(self, name=None, doc=None, lineno=None,
                 col_offset=None, parent=None, keywords=None):
        self.keywords = keywords
        self.bases = []
        self.body = []
        self.name = name
        self.doc = doc
        self.instance_attrs = collections.defaultdict(list)
        self.external_attrs = collections.defaultdict(list)
        super(ClassDef, self).__init__(lineno, col_offset, parent)

    # pylint: disable=redefined-outer-name
    def postinit(self, bases, body, decorators, newstyle=None, metaclass=None, keywords=None):
        self.keywords = keywords
        self.bases = bases
        self.body = body
        self.decorators = decorators
        if newstyle is not None:
            self._newstyle = newstyle
        if metaclass is not None:
            self._metaclass = metaclass

    @property
    def locals(self):
        # return get_locals(self)
        return MappingProxyType(lookup.get_locals(self))

    # @property
    # def instance_attrs(self):
    #     return MappingProxyType(get_external_assignments(self, collections.defaultdict(list)))

    def _newstyle_impl(self, context=None):
        if context is None:
            context = contextmod.InferenceContext()
        if self._newstyle is not None:
            return self._newstyle
        for base in self.ancestors(recurs=False, context=context):
            if base._newstyle_impl(context):
                self._newstyle = True
                break
        klass = self.declared_metaclass()
        # could be any callable, we'd need to infer the result of klass(name,
        # bases, dict).  punt if it's not a class node.
        if klass is not None and isinstance(klass, ClassDef):
            self._newstyle = klass._newstyle_impl(context)
        if self._newstyle is None:
            self._newstyle = False
        return self._newstyle

    _newstyle = None
    newstyle = property(_newstyle_impl,
                        doc="boolean indicating if it's a new style class"
                        "or not")

    @decorators_mod.cachedproperty
    def blockstart_tolineno(self):
        if self.bases:
            return self.bases[-1].tolineno
        else:
            return self.fromlineno

    def block_range(self, lineno):
        """return block line numbers.

        start from the "class" position whatever the given lineno
        """
        return self.fromlineno, self.tolineno

    def pytype(self):
        if self.newstyle:
            return '%s.type' % BUILTINS
        return '%s.classobj' % BUILTINS

    def display_type(self):
        return 'Class'

    def callable(self):
        return True

    def is_subtype_of(self, type_name, context=None):
        if self.qname() == type_name:
            return True
        for anc in self.ancestors(context=context):
            if anc.qname() == type_name:
                return True

    def _infer_type_call(self, caller, context):
        name_node = next(caller.args[0].infer(context))
        if (isinstance(name_node, node_classes.Const) and
                isinstance(name_node.value, six.string_types)):
            name = name_node.value
        else:
            return util.Uninferable

        result = ClassDef(name, None, parent=caller.parent)

        # Get the bases of the class.
        class_bases = next(caller.args[1].infer(context))
        if isinstance(class_bases, (node_classes.Tuple, node_classes.List)):
            bases = class_bases.itered()
        else:
            # There is currently no AST node that can represent an 'unknown'
            # node (Uninferable is not an AST node), therefore we simply return Uninferable here
            # although we know at least the name of the class.
            return util.Uninferable

        # Get the members of the class
        try:
            members = next(caller.args[2].infer(context))
        except exceptions.InferenceError:
            members = None

        body = []
        if members and isinstance(members, node_classes.Dict):
            for attr, value in members.items:
                if (isinstance(attr, node_classes.Const) and
                        isinstance(attr.value, six.string_types)):
                    assign = node_classes.Assign(parent=result)
                    assign.postinit(targets=node_classes.AssignName(attr.value,
                                                                    parent=assign),
                                    value=value)
                    body.append(assign)

        result.postinit(bases=bases, body=body, decorators=[], newstyle=True)
        return result

    def infer_call_result(self, caller, context=None):
        """infer what a class is returning when called"""
        if (self.is_subtype_of('%s.type' % (BUILTINS,), context)
                and len(caller.args) == 3):
            result = self._infer_type_call(caller, context)
            yield result
        else:
            yield objects.Instance(self)

    def scope_lookup(self, node, name, offset=0):
        # If the name looks like a builtin name, just try to look
        # into the upper scope of this class. We might have a
        # decorator that it's poorly named after a builtin object
        # inside this class.
        lookup_upper_frame = (
            isinstance(node.parent, node_classes.Decorators) and
            name in MANAGER.builtins()
        )
        if any(node == base or base.parent_of(node)
               for base in self.bases) or lookup_upper_frame:
            # Handle the case where we have either a name
            # in the bases of a class, which exists before
            # the actual definition or the case where we have
            # a Getattr node, with that name.
            #
            # name = ...
            # class A(name):
            #     def name(self): ...
            #
            # import name
            # class A(name.Name):
            #     def name(self): ...

            frame = self.parent.frame()
            # line offset to avoid that class A(A) resolve the ancestor to
            # the defined class
            offset = -1
        else:
            frame = self
        return frame._scope_lookup(node, name, offset)

    @property
    def basenames(self):
        """Get the list of parent class names, as they appear in the class definition."""
        return [bnode.as_string() for bnode in self.bases]

    def ancestors(self, recurs=True, context=None):
        """return an iterator on the node base classes in a prefixed
        depth first order

        :param recurs:
          boolean indicating if it should recurse or return direct
          ancestors only
        """
        # FIXME: should be possible to choose the resolution order
        # FIXME: inference make infinite loops possible here
        yielded = {self}
        if context is None:
            context = contextmod.InferenceContext()
        if six.PY3:
            if not self.bases and self.qname() != 'builtins.object':
                yield lookup.builtin_lookup("object")[1][0]
                return

        for stmt in self.bases:
            with context.restore_path():
                try:
                    for baseobj in stmt.infer(context):
                        if not isinstance(baseobj, ClassDef):
                            if isinstance(baseobj, objects.Instance):
                                baseobj = baseobj._proxied
                            else:
                                continue
                        if not baseobj.hide:
                            if baseobj in yielded:
                                continue
                            yielded.add(baseobj)
                            yield baseobj
                        if recurs:
                            for grandpa in baseobj.ancestors(recurs=True,
                                                             context=context):
                                if grandpa is self:
                                    # This class is the ancestor of itself.
                                    break
                                if grandpa in yielded:
                                    continue
                                yielded.add(grandpa)
                                yield grandpa
                except exceptions.InferenceError:
                    continue

    def local_attr_ancestors(self, name, context=None):
        """return an iterator on astroid representation of parent classes
        which have <name> defined in their locals
        """
        if self.newstyle and all(n.newstyle for n in self.ancestors(context)):
            # Look up in the mro if we can. This will result in the
            # attribute being looked up just as Python does it.
            try:
                ancestors = self.mro(context)[1:]
            except exceptions.MroError:
                # Fallback to use ancestors, we can't determine
                # a sane MRO.
                ancestors = self.ancestors(context=context)
        else:
            ancestors = self.ancestors(context=context)
        for astroid in ancestors:
            if name in astroid:
                yield astroid

    def instance_attr_ancestors(self, name, context=None):
        """return an iterator on astroid representation of parent classes
        which have <name> defined in their instance attribute dictionary
        """
        for astroid in self.ancestors(context=context):
            if name in astroid.instance_attrs:
                yield astroid

    def has_base(self, node):
        return node in self.bases

    def local_attr(self, name, context=None):
        """return the list of assign node associated to name in this class
        locals or in its parents

        :raises `AttributeInferenceError`:
          if no attribute with this name has been find in this class or
          its parent classes
        """
        result = []
        if name in self.locals:
            result = self.locals[name]
        else:
            class_node = next(self.local_attr_ancestors(name, context), ())
            if class_node:
                result = class_node.locals[name]
        result = [n for n in result if not isinstance(n, node_classes.DelAttr)]
        if result:
            return result
        raise exceptions.AttributeInferenceError(target=self, attribute=name,
                                                 context=context)

    def instance_attr(self, name, context=None):
        """return the astroid nodes associated to name in this class instance
        attributes dictionary and in its parents

        :raises `AttributeInferenceError`:
          if no attribute with this name has been find in this class or
          its parent classes
        """
        # Return a copy, so we don't modify self.instance_attrs,
        # which could lead to infinite loop.
        values = list(self.instance_attrs.get(name, []))
        # get all values from parents
        for class_node in self.instance_attr_ancestors(name, context):
            values += class_node.instance_attrs[name]
        values = [n for n in values if not isinstance(n, node_classes.DelAttr)]
        if values:
            return values
        raise exceptions.AttributeInferenceError(target=self, attribute=name,
                                                 context=context)

    def instantiate_class(self):
        """return Instance of ClassDef node, else return self"""
        return objects.Instance(self)

    def getattr(self, name, context=None, class_context=True):
        """Get an attribute from this class, using Python's attribute semantic

        This method doesn't look in the instance_attrs dictionary
        since it's done by an Instance proxy at inference time.  It
        may return a Uninferable object if the attribute has not been actually
        found but a __getattr__ or __getattribute__ method is defined.
        If *class_context* is given, then it's considered that the
        attribute is accessed from a class context,
        e.g. ClassDef.attribute, otherwise it might have been accessed
        from an instance as well.  If *class_context* is used in that
        case, then a lookup in the implicit metaclass and the explicit
        metaclass will be done.

        """
        local_values = self.locals.get(name, [])
        external_values = self.external_attrs.get(name, [])
        values = local_values + external_values

        # Determine if we should look retrieve special attributes.
        # If a class has local values with the given name and that given
        # name is also a special attribute, then priority should be given
        # to the local defined value, irrespective of the underlying
        # potential attributes defined by the special model.
        # But this is not the case for builtins, for which the
        # value can't be redefined locally. In the case of builtins though,
        # we always look into the special method and for the rest,
        # we only look if there is no local value defined with the same name.
        is_builtin = self.root().name == BUILTINS
        look_special_attributes = is_builtin or not local_values

        if name in self.special_attributes and class_context and look_special_attributes:
            result = [self.special_attributes.lookup(name)]            
            if name == '__bases__':
                # Need special treatment, since they are mutable
                # and we need to return all the values.
                result += values
            return result

        # don't modify the list in self.locals!
        values = list(values)
        for classnode in self.ancestors(recurs=True, context=context):
            values += classnode.locals.get(name, []) + classnode.external_attrs.get(name, [])

        if class_context:
            values += self._metaclass_lookup_attribute(name, context)

        if not values:
            raise exceptions.AttributeInferenceError(target=self, attribute=name,
                                                     context=context)

        return values

    def _metaclass_lookup_attribute(self, name, context):
        """Search the given name in the implicit and the explicit metaclass."""
        attrs = set()
        implicit_meta = self.implicit_metaclass()
        metaclass = self.metaclass()
        for cls in {implicit_meta, metaclass}:
            if cls and cls != self and isinstance(cls, ClassDef):
                cls_attributes = self._get_attribute_from_metaclass(
                    cls, name, context)
                attrs.update(set(cls_attributes))
        return attrs

    def _get_attribute_from_metaclass(self, cls, name, context):
        try:
            attrs = cls.getattr(name, context=context,
                                class_context=True)
        except exceptions.AttributeInferenceError:
            return

        for attr in infer_stmts(attrs, context, frame=cls):
            if not isinstance(attr, FunctionDef):
                yield attr
                continue

            if objects.is_property(attr):
                for inferred in attr.infer_call_result(self, context):
                    yield inferred
                continue

            if attr.type == 'classmethod':
                # If the method is a classmethod, then it will
                # be bound to the metaclass, not to the class
                # from where the attribute is retrieved.
                # get_wrapping_class could return None, so just
                # default to the current class.
                frame = get_wrapping_class(attr) or self
                yield objects.BoundMethod(attr, frame)
            elif attr.type == 'staticmethod':
                yield attr
            else:
                yield objects.BoundMethod(attr, self)

    def igetattr(self, name, context=None, class_context=True):
        """inferred getattr, need special treatment in class to handle
        descriptors
        """
        # set lookup name since this is necessary to infer on import nodes for
        # instance
        context = contextmod.copy_context(context)
        context.lookupname = name
        try:
            for inferred in infer_stmts(self.getattr(name, context, class_context=class_context),
                                        context, frame=self):
                # yield Uninferable object instead of descriptors when necessary
                if (not isinstance(inferred, node_classes.Const)
                        and isinstance(inferred, objects.Instance)):
                    if inferred.root().pure_python:
                        # We need to process only those descriptors which are custom
                        # classes, with their own implementation of __get__.
                        # Other objects, coming from builtins, shouldn't be of interest.
                        # TODO: do the __get__ computation.
                        try:
                            inferred._proxied.local_attr('__get__', context)
                        except exceptions.AttributeInferenceError:
                            yield inferred
                        else:
                            yield util.Uninferable
                    else:
                        yield inferred
                else:
                    yield function_to_method(inferred, self, class_context)
        except exceptions.AttributeInferenceError as error:
            if not name.startswith('__') and self.has_dynamic_getattr(context):
                # class handle some dynamic attributes, return a Uninferable object
                yield util.Uninferable
            else:
                util.reraise(exceptions.InferenceError(
                    error.message, target=self, attribute=name, context=context))

    def has_dynamic_getattr(self, context=None):
        """
        Check if the current instance has a custom __getattr__
        or a custom __getattribute__.

        If any such method is found and it is not from
        builtins, nor from an extension module, then the function
        will return True.
        """
        def _valid_getattr(node):
            root = node.root()
            return root.name != BUILTINS and getattr(root, 'pure_python', None)

        try:
            return _valid_getattr(self.getattr('__getattr__', context)[0])
        except exceptions.AttributeInferenceError:
            #if self.newstyle: XXX cause an infinite recursion error
            try:
                getattribute = self.getattr('__getattribute__', context)[0]
                return _valid_getattr(getattribute)
            except exceptions.AttributeInferenceError:
                pass
        return False

    def getitem(self, index, context=None):
        """Return the inference of a subscript.

        This is basically looking up the method in the metaclass and calling it.
        """
        try:
            methods = dunder_lookup.lookup(self, '__getitem__')
        except (exceptions.AttributeInferenceError,
                exceptions.NotSupportedError) as error:
            util.reraise(exceptions.InferenceError(**vars(error)))

        method = methods[0]

        # Create a new callcontext for providing index as an argument.
        if context:
            new_context = context.clone()
        else:
            new_context = contextmod.InferenceContext()

        new_context.callcontext = contextmod.CallContext(args=[index])
        new_context.boundnode = self

        return next(method.infer_call_result(self, new_context))

    def methods(self):
        """return an iterator on all methods defined in the class and
        its ancestors
        """
        done = {}
        for astroid in itertools.chain(iter((self,)), self.ancestors()):
            for meth in astroid.mymethods():
                if meth.name in done:
                    continue
                done[meth.name] = None
                yield meth

    def mymethods(self):
        """return an iterator on all methods defined in the class"""
        for member in self.values():
            if isinstance(member, FunctionDef):
                yield member

    def implicit_metaclass(self):
        """Get the implicit metaclass of the current class

        For newstyle classes, this will return an instance of builtins.type.
        For oldstyle classes, it will simply return None, since there's
        no implicit metaclass there.
        """

        if self.newstyle:
            return lookup.builtin_lookup('type')[1][0]

    _metaclass = None
    def declared_metaclass(self):
        """Return the explicit declared metaclass for the current class.

        An explicit declared metaclass is defined
        either by passing the ``metaclass`` keyword argument
        in the class definition line (Python 3) or (Python 2) by
        having a ``__metaclass__`` class attribute, or if there are
        no explicit bases but there is a global ``__metaclass__`` variable.
        """
        for base in self.bases:
            try:
                for baseobj in base.infer():
                    if isinstance(baseobj, ClassDef) and baseobj.hide:
                        self._metaclass = baseobj._metaclass
                        self._metaclass_hack = True
                        break
            except exceptions.InferenceError:
                pass

        if self._metaclass:
            # Expects this from Py3k TreeRebuilder
            try:
                return next(node for node in self._metaclass.infer()
                            if node is not util.Uninferable)
            except (exceptions.InferenceError, StopIteration):
                return None
        if six.PY3:
            return None

        if '__metaclass__' in self.locals:
            assignment = self.locals['__metaclass__'][-1]
        elif self.bases:
            return None
        elif '__metaclass__' in self.root().locals:
            assignments = [ass for ass in self.root().locals['__metaclass__']
                           if ass.lineno < self.lineno]
            if not assignments:
                return None
            assignment = assignments[-1]
        else:
            return None

        try:
            inferred = next(assignment.infer())
        except exceptions.InferenceError:
            return
        if inferred is util.Uninferable: # don't expose this
            return None
        return inferred

    def _find_metaclass(self, seen=None):
        if seen is None:
            seen = set()
        seen.add(self)

        klass = self.declared_metaclass()
        if klass is None:
            for parent in self.ancestors():
                if parent not in seen:
                    klass = parent._find_metaclass(seen)
                    if klass is not None:
                        break
        return klass

    def metaclass(self):
        """Return the metaclass of this class.

        If this class does not define explicitly a metaclass,
        then the first defined metaclass in ancestors will be used
        instead.
        """
        return self._find_metaclass()

    def has_metaclass_hack(self):
        return self._metaclass_hack

    def _islots(self):
        """ Return an iterator with the inferred slots. """
        if '__slots__' not in self.locals:
            return
        for slots in self.igetattr('__slots__'):
            # check if __slots__ is a valid type
            for meth in ITER_METHODS:
                try:
                    slots.getattr(meth)
                    break
                except exceptions.AttributeInferenceError:
                    continue
            else:
                continue

            if isinstance(slots, node_classes.Const):
                # a string. Ignore the following checks,
                # but yield the node, only if it has a value
                if slots.value:
                    yield slots
                continue
            if not hasattr(slots, 'itered'):
                # we can't obtain the values, maybe a .deque?
                continue

            if isinstance(slots, node_classes.Dict):
                values = [item[0] for item in slots.items]
            else:
                values = slots.itered()
            if values is util.Uninferable:
                continue
            if not values:
                # Stop the iteration, because the class
                # has an empty list of slots.
                raise StopIteration(values)

            for elt in values:
                try:
                    for inferred in elt.infer():
                        if inferred is util.Uninferable:
                            continue
                        if (not isinstance(inferred, node_classes.Const) or
                                not isinstance(inferred.value,
                                               six.string_types)):
                            continue
                        if not inferred.value:
                            continue
                        yield inferred
                except exceptions.InferenceError:
                    continue

    def _slots(self):
        if not self.newstyle:
            raise TypeError(
                "The concept of slots is undefined for old-style classes.")

        slots = self._islots()
        try:
            first = next(slots)
        except StopIteration as exc:
            # The class doesn't have a __slots__ definition or empty slots.
            if exc.args and exc.args[0] not in ('', None):
                return exc.args[0]
            return None
        # pylint: disable=unsupported-binary-operation; false positive
        return [first] + list(slots)

    # Cached, because inferring them all the time is expensive
    @decorators_mod.cached
    def slots(self):
        """Get all the slots for this node.

        If the class doesn't define any slot, through `__slots__`
        variable, then this function will return a None.
        Also, it will return None in the case the slots weren't inferred.
        Otherwise, it will return a list of slot names.
        """
        def grouped_slots():
            # Not interested in object, since it can't have slots.
            for cls in self.mro()[:-1]:
                try:
                    cls_slots = cls._slots()
                except NotImplementedError:
                    continue
                if cls_slots is not None:
                    for slot in cls_slots:
                        yield slot
                else:
                    yield None

        if not self.newstyle:
            raise TypeError(
                "The concept of slots is undefined for old-style classes.")

        slots = list(grouped_slots())
        if not all(slot is not None for slot in slots):
            return None

        return sorted(slots, key=lambda item: item.value)

    def _inferred_bases(self, context=None):
        # TODO(cpopa): really similar with .ancestors,
        # but the difference is when one base is inferred,
        # only the first object is wanted. That's because
        # we aren't interested in superclasses, as in the following
        # example:
        #
        # class SomeSuperClass(object): pass
        # class SomeClass(SomeSuperClass): pass
        # class Test(SomeClass): pass
        #
        # Inferring SomeClass from the Test's bases will give
        # us both SomeClass and SomeSuperClass, but we are interested
        # only in SomeClass.

        if context is None:
            context = contextmod.InferenceContext()
        if six.PY3:
            if not self.bases and self.qname() != 'builtins.object':
                yield lookup.builtin_lookup("object")[1][0]
                return

        for stmt in self.bases:
            try:
                baseobj = next(stmt.infer(context=context))
            except exceptions.InferenceError:
                continue
            if isinstance(baseobj, objects.Instance):
                baseobj = baseobj._proxied
            if not isinstance(baseobj, ClassDef):
                continue
            if not baseobj.hide:
                yield baseobj
            else:
                for base in baseobj.bases:
                    yield base

    def mro(self, context=None):
        """Get the method resolution order, using C3 linearization.

        It returns the list of ancestors sorted by the mro.
        This will raise `TypeError` for old-style classes, since
        they don't have the concept of MRO.
        """
        if not self.newstyle:
            raise TypeError(
                "Could not obtain mro for old-style classes.")

        bases = list(self._inferred_bases(context=context))
        bases_mro = []
        for base in bases:
            if base is self:
                continue
            try:
                mro = base.mro(context=context)
                bases_mro.append(mro)
            except TypeError:
                # Some classes have in their ancestors both newstyle and
                # old style classes. For these we can't retrieve the .mro,
                # although in Python it's possible, since the class we are
                # currently working is in fact new style.
                # So, we fallback to ancestors here.
                ancestors = list(base.ancestors(context=context))
                bases_mro.append(ancestors)

        unmerged_mro = ([[self]] + bases_mro + [bases])
        _verify_duplicates_mro(unmerged_mro, self, context)
        return _c3_merge(unmerged_mro, self, context)

    def bool_value(self):
        return True
