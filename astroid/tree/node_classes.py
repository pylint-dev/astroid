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
"""Module for some node classes. More nodes in scoped_nodes.py
"""

import functools
import warnings
import sys

import six

from astroid import context as contextmod
from astroid import decorators
from astroid import exceptions
from astroid import inference
from astroid.interpreter import runtimeabc
from astroid.interpreter import objects
from astroid import manager
from astroid import mixins
from astroid import protocols
from astroid.tree import base
from astroid.tree import treeabc
from astroid import util

raw_building = util.lazy_import('raw_building')

BUILTINS = six.moves.builtins.__name__
MANAGER = manager.AstroidManager()


def _container_getitem(instance, elts, index):
    """Get a slice or an item, using the given *index*, for the given sequence."""
    if isinstance(index, slice):
        new_cls = instance.__class__()
        new_cls.elts = elts[index]
        new_cls.parent = instance.parent
        return new_cls
    else:
        return elts[index]


@util.register_implementation(treeabc.Statement)
class Statement(base.NodeNG):
    """Statement node adding a few attributes"""
    is_statement = True

    def next_sibling(self):
        """return the next sibling statement"""
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        try:
            return stmts[index +1]
        except IndexError:
            pass

    def previous_sibling(self):
        """return the previous sibling statement"""
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        if index >= 1:
            return stmts[index -1]


class AssignedStmtsMixin(object):
    """Provide an `assigned_stmts` method to classes which inherits it."""

    def assigned_stmts(self, node=None, context=None, asspath=None):
        """Responsible to return the assigned statement
        (e.g. not inferred) according to the assignment type.

        The `asspath` parameter is used to record the lhs path of the original node.
        For instance if we want assigned statements for 'c' in 'a, (b,c)', asspath
        will be [1, 1] once arrived to the Assign node.

        The `context` parameter is the current inference context which should be given
        to any intermediary inference necessary.
        """
        # Inject the current module into assigned_stmts, in order to avoid
        # circular dependencies between these modules.
        return protocols.assigned_stmts(self, sys.modules[__name__],
                                        node=node, context=context,
                                        asspath=asspath)


# Name classes

@util.register_implementation(treeabc.AssignName)
class AssignName(mixins.LookupMixIn, mixins.ParentAssignTypeMixin,
                 AssignedStmtsMixin, base.NodeNG):
    """class representing an AssignName node"""
    _other_fields = ('name',)

    def __init__(self, name=None, lineno=None, col_offset=None, parent=None):
        self.name = name
        super(AssignName, self).__init__(lineno, col_offset, parent)

    infer_lhs = inference.infer_name


@util.register_implementation(treeabc.DelName)
class DelName(mixins.LookupMixIn, mixins.ParentAssignTypeMixin, base.NodeNG):
    """class representing a DelName node"""
    _other_fields = ('name',)

    def __init__(self, name=None, lineno=None, col_offset=None, parent=None):
        self.name = name
        super(DelName, self).__init__(lineno, col_offset, parent)


@util.register_implementation(treeabc.Name)
class Name(mixins.LookupMixIn, base.NodeNG):
    """class representing a Name node"""
    _other_fields = ('name',)

    def __init__(self, name=None, lineno=None, col_offset=None, parent=None):
        self.name = name
        super(Name, self).__init__(lineno, col_offset, parent)


@util.register_implementation(treeabc.Arguments)
class Arguments(mixins.AssignTypeMixin, AssignedStmtsMixin, base.NodeNG):
    """class representing an Arguments node"""
    if six.PY3:
        # Python 3.4+ uses a different approach regarding annotations,
        # each argument is a new class, _ast.arg, which exposes an
        # 'annotation' attribute. In astroid though, arguments are exposed
        # as is in the Arguments node and the only way to expose annotations
        # is by using something similar with Python 3.3:
        #  - we expose 'varargannotation' and 'kwargannotation' of annotations
        #    of varargs and kwargs.
        #  - we expose 'annotation', a list with annotations for
        #    for each normal argument. If an argument doesn't have an
        #    annotation, its value will be None.

        _astroid_fields = ('args', 'defaults', 'kwonlyargs',
                           'kw_defaults', 'annotations', 'kwonly_annotations',
                           'varargannotation', 'kwargannotation')
        varargannotation = None
        kwargannotation = None
    else:
        _astroid_fields = ('args', 'defaults', 'kwonlyargs', 'kw_defaults')
    _other_fields = ('vararg', 'kwarg')

    def __init__(self, vararg=None, kwarg=None, parent=None):
        self.vararg = vararg
        self.kwarg = kwarg
        self.parent = parent
        self.args = []
        self.defaults = []
        self.kwonlyargs = []
        self.kw_defaults = []
        self.annotations = []
        self.kwonly_annotations = []

    def postinit(self, args, defaults, kwonlyargs, kw_defaults,
                 annotations, kwonly_annotations, varargannotation=None,
                 kwargannotation=None):
        self.args = args
        self.defaults = defaults
        self.kwonlyargs = kwonlyargs
        self.kw_defaults = kw_defaults
        self.annotations = annotations
        self.varargannotation = varargannotation
        self.kwargannotation = kwargannotation
        self.kwonly_annotations = kwonly_annotations

    def _infer_name(self, frame, name):
        if self.parent is frame:
            return name
        return None

    @decorators.cachedproperty
    def fromlineno(self):
        lineno = super(Arguments, self).fromlineno
        return max(lineno, self.parent.fromlineno or 0)

    def format_args(self):
        """return arguments formatted as string"""
        result = []
        if self.args:
            result.append(
                _format_args(self.args, self.defaults,
                             getattr(self, 'annotations', None))
            )
        if self.vararg:
            result.append('*%s' % self.vararg)
        if self.kwonlyargs:
            if not self.vararg:
                result.append('*')
            result.append(_format_args(self.kwonlyargs, self.kw_defaults))
        if self.kwarg:
            result.append('**%s' % self.kwarg)
        return ', '.join(result)

    def default_value(self, argname):
        """return the default value for an argument

        :raise `NoDefault`: if there is no default value defined
        """
        i = _find_arg(argname, self.args)[0]
        if i is not None:
            idx = i - (len(self.args) - len(self.defaults))
            if idx >= 0:
                return self.defaults[idx]
        i = _find_arg(argname, self.kwonlyargs)[0]
        if i is not None and self.kw_defaults[i] is not None:
            return self.kw_defaults[i]
        raise exceptions.NoDefault(func=self.parent, name=argname)

    def is_argument(self, name):
        """return True if the name is defined in arguments"""
        if name == self.vararg:
            return True
        if name == self.kwarg:
            return True
        return self.find_argname(name, True)[1] is not None

    def find_argname(self, argname, rec=False):
        """return index and Name node with given name"""
        if self.args: # self.args may be None in some cases (builtin function)
            return _find_arg(argname, self.args, rec)
        return None, None

    def get_children(self):
        """override get_children to skip over None elements in kw_defaults"""
        for child in super(Arguments, self).get_children():
            if child is not None:
                yield child


def _find_arg(argname, args, rec=False):
    for i, arg in enumerate(args):
        if isinstance(arg, Tuple):
            if rec:
                found = _find_arg(argname, arg.elts)
                if found[0] is not None:
                    return found
        elif arg.name == argname:
            return i, arg
    return None, None


def _format_args(args, defaults=None, annotations=None):
    values = []
    if args is None:
        return ''
    if annotations is None:
        annotations = []
    if defaults is not None:
        default_offset = len(args) - len(defaults)
    packed = six.moves.zip_longest(args, annotations)
    for i, (arg, annotation) in enumerate(packed):
        if isinstance(arg, Tuple):
            values.append('(%s)' % _format_args(arg.elts))
        else:
            argname = arg.name
            if annotation is not None:
                argname += ':' + annotation.as_string()
            values.append(argname)

            if defaults is not None and i >= default_offset:
                if defaults[i-default_offset] is not None:
                    values[-1] += '=' + defaults[i-default_offset].as_string()
    return ', '.join(values)


class Unknown(base.NodeNG):
    '''This node represents a node in a constructed AST where
    introspection is not possible.  At the moment, it's only used in
    the args attribute of FunctionDef nodes where function signature
    introspection failed.

    '''
    def infer(self, context=None, **kwargs):
        '''Inference on an Unknown node immediately terminates.'''
        yield util.Uninferable


@util.register_implementation(treeabc.AssignAttr)
class AssignAttr(mixins.ParentAssignTypeMixin,
                 AssignedStmtsMixin, base.NodeNG):
    """class representing an AssignAttr node"""
    _astroid_fields = ('expr',)
    _other_fields = ('attrname',)
    expr = None

    def __init__(self, attrname=None, lineno=None, col_offset=None, parent=None):
        self.attrname = attrname
        super(AssignAttr, self).__init__(lineno, col_offset, parent)

    def postinit(self, expr=None):
        self.expr = expr

    infer_lhs = inference.infer_attribute


@util.register_implementation(treeabc.Assert)
class Assert(Statement):
    """class representing an Assert node"""
    _astroid_fields = ('test', 'fail',)
    test = None
    fail = None

    def postinit(self, test=None, fail=None):
        self.fail = fail
        self.test = test


@util.register_implementation(treeabc.Assign)
class Assign(mixins.AssignTypeMixin, AssignedStmtsMixin, Statement):
    """class representing an Assign node"""
    _astroid_fields = ('targets', 'value',)
    targets = None
    value = None

    def postinit(self, targets=None, value=None):
        self.targets = targets
        self.value = value


@util.register_implementation(treeabc.AugAssign)
class AugAssign(mixins.AssignTypeMixin, AssignedStmtsMixin, Statement):
    """class representing an AugAssign node"""
    _astroid_fields = ('target', 'value')
    _other_fields = ('op',)
    target = None
    value = None

    def __init__(self, op=None, lineno=None, col_offset=None, parent=None):
        self.op = op
        super(AugAssign, self).__init__(lineno, col_offset, parent)

    def postinit(self, target=None, value=None):
        self.target = target
        self.value = value

    def _infer_augassign(self, context):
        return inference.infer_augassign(self, nodes=sys.modules[__name__],
                                         context=context)

    def type_errors(self, context=None):
        """Return a list of TypeErrors which can occur during inference.

        Each TypeError is represented by a :class:`BinaryOperationError`,
        which holds the original exception.
        """
        try:
            results = self._infer_augassign(context=context)
            return [result for result in results
                    if isinstance(result, util.BadBinaryOperationMessage)]
        except exceptions.InferenceError:
            return []


@util.register_implementation(treeabc.Repr)
class Repr(base.NodeNG):
    """class representing a Repr node"""
    _astroid_fields = ('value',)
    value = None

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.BinOp)
class BinOp(base.NodeNG):
    """class representing a BinOp node"""
    _astroid_fields = ('left', 'right')
    _other_fields = ('op',)
    left = None
    right = None

    def __init__(self, op=None, lineno=None, col_offset=None, parent=None):
        self.op = op
        super(BinOp, self).__init__(lineno, col_offset, parent)

    def postinit(self, left=None, right=None):
        self.left = left
        self.right = right

    def _infer_binop(self, context):
        return inference.infer_binop(self, nodes=sys.modules[__name__],
                                     context=context)

    def type_errors(self, context=None):
        """Return a list of TypeErrors which can occur during inference.

        Each TypeError is represented by a :class:`BadBinaryOperationMessage`,
        which holds the original exception.
        """
        try:
            results = self._infer_binop(context=context)
            return [result for result in results
                    if isinstance(result, util.BadBinaryOperationMessage)]
        except exceptions.InferenceError:
            return []


@util.register_implementation(treeabc.BoolOp)
class BoolOp(base.NodeNG):
    """class representing a BoolOp node"""
    _astroid_fields = ('values',)
    _other_fields = ('op',)
    values = None

    def __init__(self, op=None, lineno=None, col_offset=None, parent=None):
        self.op = op
        super(BoolOp, self).__init__(lineno, col_offset, parent)

    def postinit(self, values=None):
        self.values = values


@util.register_implementation(treeabc.Break)
class Break(Statement):
    """class representing a Break node"""


@util.register_implementation(treeabc.Call)
class Call(base.NodeNG):
    """class representing a Call node"""
    _astroid_fields = ('func', 'args', 'keywords')
    func = None
    args = None
    keywords = None

    def postinit(self, func=None, args=None, keywords=None):
        self.func = func
        self.args = args
        self.keywords = keywords

    @property
    def starargs(self):
        args = self.args or []
        return [arg for arg in args if isinstance(arg, Starred)]

    @property
    def kwargs(self):
        keywords = self.keywords or []
        return [keyword for keyword in keywords if keyword.arg is None]


@util.register_implementation(treeabc.Compare)
class Compare(base.NodeNG):
    """class representing a Compare node"""
    _astroid_fields = ('left', 'ops',)
    left = None
    ops = None

    def postinit(self, left=None, ops=None):
        self.left = left
        self.ops = ops

    def get_children(self):
        """override get_children for tuple fields"""
        yield self.left
        for _, comparator in self.ops:
            yield comparator # we don't want the 'op'

    def last_child(self):
        """override last_child"""
        # XXX maybe if self.ops:
        return self.ops[-1][1]
        #return self.left


@util.register_implementation(treeabc.Comprehension)
class Comprehension(AssignedStmtsMixin, base.NodeNG):
    """class representing a Comprehension node"""
    _astroid_fields = ('target', 'iter', 'ifs')
    target = None
    iter = None
    ifs = None

    def __init__(self, parent=None):
        self.parent = parent

    def postinit(self, target=None, iter=None, ifs=None):
        self.target = target
        self.iter = iter
        self.ifs = ifs

    optional_assign = True
    def assign_type(self):
        return self

    def ass_type(self):
        util.rename_warning((type(self).__name__, type(self).__name__))
        return self.assign_type()

    def _get_filtered_stmts(self, lookup_node, node, stmts, mystmt):
        """method used in filter_stmts"""
        if self is mystmt:
            if isinstance(lookup_node, (Const, Name)):
                return [lookup_node], True

        elif self.statement() is mystmt:
            # original node's statement is the assignment, only keeps
            # current node (gen exp, list comp)

            return [node], True

        return stmts, False


@util.register_implementation(treeabc.Const)
@util.register_implementation(runtimeabc.BuiltinInstance)
class Const(base.NodeNG, objects.BaseInstance):
    """represent a constant node like num, str, bytes"""
    _other_fields = ('value',)

    def __init__(self, value, lineno=None, col_offset=None, parent=None):
        self.value = value
        super(Const, self).__init__(lineno, col_offset, parent)

    def getitem(self, index, context=None):
        if isinstance(self.value, six.string_types):
            return Const(self.value[index])
        if isinstance(self.value, bytes) and six.PY3:
            # Bytes aren't instances of six.string_types
            # on Python 3. Also, indexing them should return
            # integers.
            return Const(self.value[index])
        raise TypeError('%r (value=%s)' % (self, self.value))

    def has_dynamic_getattr(self):
        return False

    def itered(self):
        if isinstance(self.value, six.string_types):
            return self.value
        raise TypeError()

    def pytype(self):
        return self._proxied.qname()

    def bool_value(self):
        return bool(self.value)

    @decorators.cachedproperty
    def _proxied(self):
        builtins = MANAGER.astroid_cache[BUILTINS]
        return builtins.getattr(type(self.value).__name__)[0]


class NameConstant(Const):
    """Represents a builtin singleton, at the moment True, False, None,
    and NotImplemented.

    """

    # @decorators.cachedproperty
    # def _proxied(self):
    #     return self
    #     # builtins = MANAGER.astroid_cache[BUILTINS]
    #     # return builtins.getattr(str(self.value))[0]


class ReservedName(base.NodeNG):
    '''Used in the builtins AST to assign names to singletons.'''
    _astroid_fields = ('value',)
    _other_fields = ('name',)

    def __init__(self, name, lineno=None, col_offset=None, parent=None):
        self.name = name
        super(ReservedName, self).__init__(lineno, col_offset, parent)

    def postinit(self, value):
        self.value = value


@util.register_implementation(treeabc.Continue)
class Continue(Statement):
    """class representing a Continue node"""


@util.register_implementation(treeabc.Decorators)
class Decorators(base.NodeNG):
    """class representing a Decorators node"""
    _astroid_fields = ('nodes',)
    nodes = None

    def postinit(self, nodes):
        self.nodes = nodes


@util.register_implementation(treeabc.DelAttr)
class DelAttr(mixins.ParentAssignTypeMixin, base.NodeNG):
    """class representing a DelAttr node"""
    _astroid_fields = ('expr',)
    _other_fields = ('attrname',)
    expr = None

    def __init__(self, attrname=None, lineno=None, col_offset=None, parent=None):
        self.attrname = attrname
        super(DelAttr, self).__init__(lineno, col_offset, parent)

    def postinit(self, expr=None):
        self.expr = expr


@util.register_implementation(treeabc.Delete)
class Delete(mixins.AssignTypeMixin, Statement):
    """class representing a Delete node"""
    _astroid_fields = ('targets',)
    targets = None

    def postinit(self, targets=None):
        self.targets = targets


@util.register_implementation(treeabc.Dict)
@util.register_implementation(runtimeabc.BuiltinInstance)
class Dict(base.NodeNG, objects.BaseInstance):
    """class representing a Dict node"""
    _astroid_fields = ('items',)

    def __init__(self, lineno=None, col_offset=None, parent=None):
        self.items = []
        super(Dict, self).__init__(lineno, col_offset, parent)

    def postinit(self, items):
        self.items = items

    def pytype(self):
        return '%s.dict' % BUILTINS

    def get_children(self):
        """get children of a Dict node"""
        # overrides get_children
        for key, value in self.items:
            yield key
            yield value

    def last_child(self):
        """override last_child"""
        if self.items:
            return self.items[-1][1]
        return None

    def itered(self):
        return self.items[::2]

    def getitem(self, lookup_key, context=None):
        for key, value in self.items:
            # TODO(cpopa): no support for overriding yet, {1:2, **{1: 3}}.
            if isinstance(key, DictUnpack):
                try:
                    return value.getitem(lookup_key, context)
                except IndexError:
                    continue
            for inferredkey in key.infer(context):
                if inferredkey is util.Uninferable:
                    continue
                if isinstance(inferredkey, Const) \
                        and inferredkey.value == lookup_key:
                    return value
        # This should raise KeyError, but all call sites only catch
        # IndexError. Let's leave it like that for now.
        raise IndexError(lookup_key)

    def bool_value(self):
        return bool(self.items)

    @decorators.cachedproperty
    def _proxied(self):
        builtins = MANAGER.astroid_cache[BUILTINS]
        return builtins.getattr('dict')[0]


@util.register_implementation(treeabc.Expr)
class Expr(Statement):
    """class representing a Expr node"""
    _astroid_fields = ('value',)
    value = None

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.Ellipsis)
class Ellipsis(base.NodeNG): # pylint: disable=redefined-builtin
    """class representing an Ellipsis node"""

    def bool_value(self):
        return True

@util.register_implementation(treeabc.InterpreterObject)
class InterpreterObject(base.NodeNG):
    '''InterpreterObjects are used in manufactured ASTs that simulate features of
    real ASTs for inference, usually to handle behavior implemented in
    the interpreter or in C extensions.

    '''
    _other_fields = ('name', 'object')

    def __init__(self, object_=None, name=None, lineno=None, col_offset=None, parent=None):
        if object_ is not None:
            self.object = object_
        self.name = name
        super(InterpreterObject, self).__init__(lineno, col_offset, parent)

    def has_underlying_object(self):
        return hasattr(self, 'object')


@util.register_implementation(treeabc.ExceptHandler)
class ExceptHandler(mixins.AssignTypeMixin, AssignedStmtsMixin, Statement):
    """class representing an ExceptHandler node"""
    _astroid_fields = ('type', 'name', 'body',)
    type = None
    name = None
    body = None

    def postinit(self, type=None, name=None, body=None):
        self.type = type
        self.name = name
        self.body = body

    @decorators.cachedproperty
    def blockstart_tolineno(self):
        if self.name:
            return self.name.tolineno
        elif self.type:
            return self.type.tolineno
        else:
            return self.lineno

    def catch(self, exceptions):
        if self.type is None or exceptions is None:
            return True
        for node in self.type.nodes_of_class(Name):
            if node.name in exceptions:
                return True


@util.register_implementation(treeabc.Exec)
class Exec(Statement):
    """class representing an Exec node"""
    _astroid_fields = ('expr', 'globals', 'locals')
    expr = None
    globals = None
    locals = None

    def postinit(self, expr=None, globals=None, locals=None):
        self.expr = expr
        self.globals = globals
        self.locals = locals


@util.register_implementation(treeabc.ExtSlice)
class ExtSlice(base.NodeNG):
    """class representing an ExtSlice node"""
    _astroid_fields = ('dims',)
    dims = None

    def postinit(self, dims=None):
        self.dims = dims


@util.register_implementation(treeabc.For)
class For(mixins.BlockRangeMixIn, mixins.AssignTypeMixin,
          AssignedStmtsMixin, Statement):
    """class representing a For node"""
    _astroid_fields = ('target', 'iter', 'body', 'orelse',)
    target = None
    iter = None
    body = None
    orelse = None

    def postinit(self, target=None, iter=None, body=None, orelse=None):
        self.target = target
        self.iter = iter
        self.body = body
        self.orelse = orelse

    optional_assign = True
    @decorators.cachedproperty
    def blockstart_tolineno(self):
        return self.iter.tolineno


@util.register_implementation(treeabc.AsyncFor)
class AsyncFor(For):
    """Asynchronous For built with `async` keyword."""


@util.register_implementation(treeabc.Await)
class Await(base.NodeNG):
    """Await node for the `await` keyword."""

    _astroid_fields = ('value', )
    value = None

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.ImportFrom)
class ImportFrom(mixins.ImportFromMixin, Statement):
    """class representing a ImportFrom node"""
    _other_fields = ('modname', 'names', 'level')

    def __init__(self, fromname, names, level=0, lineno=None,
                 col_offset=None, parent=None):
        self.modname = fromname
        self.names = names
        self.level = level
        super(ImportFrom, self).__init__(lineno, col_offset, parent)


@util.register_implementation(treeabc.Attribute)
class Attribute(base.NodeNG):
    """class representing a Attribute node"""
    _astroid_fields = ('expr',)
    _other_fields = ('attrname',)
    expr = None

    def __init__(self, attrname=None, lineno=None, col_offset=None, parent=None):
        self.attrname = attrname
        super(Attribute, self).__init__(lineno, col_offset, parent)

    def postinit(self, expr=None):
        self.expr = expr


@util.register_implementation(treeabc.Global)
class Global(Statement):
    """class representing a Global node"""
    _other_fields = ('names',)

    def __init__(self, names, lineno=None, col_offset=None, parent=None):
        self.names = names
        super(Global, self).__init__(lineno, col_offset, parent)

    def _infer_name(self, frame, name):
        return name


@util.register_implementation(treeabc.If)
class If(mixins.BlockRangeMixIn, Statement):
    """class representing an If node"""
    _astroid_fields = ('test', 'body', 'orelse')
    test = None
    body = None
    orelse = None

    def postinit(self, test=None, body=None, orelse=None):
        self.test = test
        self.body = body
        self.orelse = orelse

    @decorators.cachedproperty
    def blockstart_tolineno(self):
        return self.test.tolineno

    def block_range(self, lineno):
        """handle block line numbers range for if statements"""
        if lineno == self.body[0].fromlineno:
            return lineno, lineno
        if lineno <= self.body[-1].tolineno:
            return lineno, self.body[-1].tolineno
        return self._elsed_block_range(lineno, self.orelse,
                                       self.body[0].fromlineno - 1)


@util.register_implementation(treeabc.IfExp)
class IfExp(base.NodeNG):
    """class representing an IfExp node"""
    _astroid_fields = ('test', 'body', 'orelse')
    test = None
    body = None
    orelse = None

    def postinit(self, test=None, body=None, orelse=None):
        self.test = test
        self.body = body
        self.orelse = orelse


@util.register_implementation(treeabc.Import)
class Import(mixins.ImportFromMixin, Statement):
    """class representing an Import node"""
    _other_fields = ('names',)

    def __init__(self, names=None, lineno=None, col_offset=None, parent=None):
        self.names = names
        super(Import, self).__init__(lineno, col_offset, parent)

    def infer_name_module(self, name):
        context = contextmod.InferenceContext()
        context.lookupname = name
        return self.infer(context, asname=False)


@util.register_implementation(treeabc.Index)
class Index(base.NodeNG):
    """class representing an Index node"""
    _astroid_fields = ('value',)
    value = None

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.Keyword)
class Keyword(base.NodeNG):
    """class representing a Keyword node"""
    _astroid_fields = ('value',)
    _other_fields = ('arg',)
    value = None

    def __init__(self, arg=None, lineno=None, col_offset=None, parent=None):
        self.arg = arg
        super(Keyword, self).__init__(lineno, col_offset, parent)

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.List)
@util.register_implementation(runtimeabc.BuiltinInstance)
class List(base.BaseContainer, AssignedStmtsMixin, objects.BaseInstance):
    """class representing a List node"""

    def pytype(self):
        return '%s.list' % BUILTINS

    def getitem(self, index, context=None):
        return _container_getitem(self, self.elts, index)


@util.register_implementation(treeabc.Nonlocal)
class Nonlocal(Statement):
    """class representing a Nonlocal node"""
    _other_fields = ('names',)

    def __init__(self, names, lineno=None, col_offset=None, parent=None):
        self.names = names
        super(Nonlocal, self).__init__(lineno, col_offset, parent)

    def _infer_name(self, frame, name):
        return name


@util.register_implementation(treeabc.Pass)
class Pass(Statement):
    """class representing a Pass node"""


@util.register_implementation(treeabc.Print)
class Print(Statement):
    """class representing a Print node"""
    _astroid_fields = ('dest', 'values',)
    dest = None
    values = None

    def __init__(self, nl=None, lineno=None, col_offset=None, parent=None):
        self.nl = nl
        super(Print, self).__init__(lineno, col_offset, parent)

    def postinit(self, dest=None, values=None):
        self.dest = dest
        self.values = values


@util.register_implementation(treeabc.Raise)
class Raise(Statement):
    """class representing a Raise node"""
    exc = None
    if six.PY2:
        _astroid_fields = ('exc', 'inst', 'tback')
        inst = None
        tback = None

        def postinit(self, exc=None, inst=None, tback=None):
            self.exc = exc
            self.inst = inst
            self.tback = tback
    else:
        _astroid_fields = ('exc', 'cause')
        exc = None
        cause = None

        def postinit(self, exc=None, cause=None):
            self.exc = exc
            self.cause = cause

    def raises_not_implemented(self):
        if not self.exc:
            return
        for name in self.exc.nodes_of_class(Name):
            if name.name == 'NotImplementedError':
                return True


@util.register_implementation(treeabc.Return)
class Return(Statement):
    """class representing a Return node"""
    _astroid_fields = ('value',)
    value = None

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.Set)
@util.register_implementation(runtimeabc.BuiltinInstance)
class Set(base.BaseContainer, objects.BaseInstance):
    """class representing a Set node"""

    def pytype(self):
        return '%s.set' % BUILTINS


@util.register_implementation(treeabc.Slice)
class Slice(base.NodeNG):
    """class representing a Slice node"""
    _astroid_fields = ('lower', 'upper', 'step')
    lower = None
    upper = None
    step = None

    def postinit(self, lower=None, upper=None, step=None):
        self.lower = lower
        self.upper = upper
        self.step = step

    def _wrap_attribute(self, attr):
        """Wrap the empty attributes of the Slice in a Const node."""
        if not attr:
            return Const(attr, parent=self)
        return attr

    @decorators.cachedproperty
    def _proxied(self):
        builtins = MANAGER.astroid_cache[BUILTINS]
        return builtins.getattr('slice')[0]

    def pytype(self):
        return '%s.slice' % BUILTINS

    def igetattr(self, attrname, context=None):
        if attrname == 'start':
            yield self._wrap_attribute(self.lower)
        elif attrname == 'stop':
            yield self._wrap_attribute(self.upper)
        elif attrname == 'step':
            yield self._wrap_attribute(self.step)
        else:
            for value in self.getattr(attrname, context=context):
                yield value

    def getattr(self, attrname, context=None):
        return self._proxied.getattr(attrname, context)


@util.register_implementation(treeabc.Starred)
class Starred(mixins.ParentAssignTypeMixin, AssignedStmtsMixin, base.NodeNG):
    """class representing a Starred node"""
    _astroid_fields = ('value',)
    value = None

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.Subscript)
class Subscript(base.NodeNG):
    """class representing a Subscript node"""
    _astroid_fields = ('value', 'slice')
    value = None
    slice = None

    def postinit(self, value=None, slice=None):
        self.value = value
        self.slice = slice

    infer_lhs = inference.infer_subscript


@util.register_implementation(treeabc.TryExcept)
class TryExcept(mixins.BlockRangeMixIn, Statement):
    """class representing a TryExcept node"""
    _astroid_fields = ('body', 'handlers', 'orelse',)
    body = None
    handlers = None
    orelse = None

    def postinit(self, body=None, handlers=None, orelse=None):
        self.body = body
        self.handlers = handlers
        self.orelse = orelse

    def _infer_name(self, frame, name):
        return name

    def block_range(self, lineno):
        """handle block line numbers range for try/except statements"""
        last = None
        for exhandler in self.handlers:
            if exhandler.type and lineno == exhandler.type.fromlineno:
                return lineno, lineno
            if exhandler.body[0].fromlineno <= lineno <= exhandler.body[-1].tolineno:
                return lineno, exhandler.body[-1].tolineno
            if last is None:
                last = exhandler.body[0].fromlineno - 1
        return self._elsed_block_range(lineno, self.orelse, last)


@util.register_implementation(treeabc.TryFinally)
class TryFinally(mixins.BlockRangeMixIn, Statement):
    """class representing a TryFinally node"""
    _astroid_fields = ('body', 'finalbody',)
    body = None
    finalbody = None

    def postinit(self, body=None, finalbody=None):
        self.body = body
        self.finalbody = finalbody

    def block_range(self, lineno):
        """handle block line numbers range for try/finally statements"""
        child = self.body[0]
        # py2.5 try: except: finally:
        if (isinstance(child, TryExcept) and child.fromlineno == self.fromlineno
                and lineno > self.fromlineno and lineno <= child.tolineno):
            return child.block_range(lineno)
        return self._elsed_block_range(lineno, self.finalbody)


@util.register_implementation(treeabc.Tuple)
@util.register_implementation(runtimeabc.BuiltinInstance)
class Tuple(base.BaseContainer, AssignedStmtsMixin, objects.BaseInstance):
    """class representing a Tuple node"""

    def pytype(self):
        return '%s.tuple' % BUILTINS

    def getitem(self, index, context=None):
        return _container_getitem(self, self.elts, index)


@util.register_implementation(treeabc.UnaryOp)
class UnaryOp(base.NodeNG):
    """class representing an UnaryOp node"""
    _astroid_fields = ('operand',)
    _other_fields = ('op',)
    operand = None

    def __init__(self, op=None, lineno=None, col_offset=None, parent=None):
        self.op = op
        super(UnaryOp, self).__init__(lineno, col_offset, parent)

    def postinit(self, operand=None):
        self.operand = operand

    def _infer_unaryop(self, context=None):
        return inference.infer_unaryop(self, nodes=sys.modules[__name__],
                                       context=context)

    def type_errors(self, context=None):
        """Return a list of TypeErrors which can occur during inference.

        Each TypeError is represented by a :class:`BadUnaryOperationMessage`,
        which holds the original exception.
        """
        try:
            results = self._infer_unaryop(context=context)
            return [result for result in results
                    if isinstance(result, util.BadUnaryOperationMessage)]
        except exceptions.InferenceError:
            return []


@util.register_implementation(treeabc.While)
class While(mixins.BlockRangeMixIn, Statement):
    """class representing a While node"""
    _astroid_fields = ('test', 'body', 'orelse',)
    test = None
    body = None
    orelse = None

    def postinit(self, test=None, body=None, orelse=None):
        self.test = test
        self.body = body
        self.orelse = orelse

    @decorators.cachedproperty
    def blockstart_tolineno(self):
        return self.test.tolineno

    def block_range(self, lineno):
        """handle block line numbers range for for and while statements"""
        return self. _elsed_block_range(lineno, self.orelse)


@util.register_implementation(treeabc.With)
class With(mixins.BlockRangeMixIn, mixins.AssignTypeMixin,
           AssignedStmtsMixin, Statement):
    """class representing a With node"""
    _astroid_fields = ('items', 'body')
    items = None
    body = None

    def postinit(self, items=None, body=None):
        self.items = items
        self.body = body

    @decorators.cachedproperty
    def blockstart_tolineno(self):
        return self.items[-1][0].tolineno

    def get_children(self):
        for expr, var in self.items:
            yield expr
            if var:
                yield var
        for elt in self.body:
            yield elt


@util.register_implementation(treeabc.AsyncWith)
class AsyncWith(With):
    """Asynchronous `with` built with the `async` keyword."""


@util.register_implementation(treeabc.Yield)
class Yield(base.NodeNG):
    """class representing a Yield node"""
    _astroid_fields = ('value',)
    value = None

    def postinit(self, value=None):
        self.value = value


@util.register_implementation(treeabc.YieldFrom)
class YieldFrom(Yield):
    """ Class representing a YieldFrom node. """


@util.register_implementation(treeabc.DictUnpack)
class DictUnpack(base.NodeNG):
    """Represents the unpacking of dicts into dicts using PEP 448."""


# Backward-compatibility aliases

Backquote = util.proxy_alias('Backquote', Repr)
Discard = util.proxy_alias('Discard', Expr)
AssName = util.proxy_alias('AssName', AssignName)
AssAttr = util.proxy_alias('AssAttr', AssignAttr)
Getattr = util.proxy_alias('Getattr', Attribute)
CallFunc = util.proxy_alias('CallFunc', Call)
From = util.proxy_alias('From', ImportFrom)


# Register additional inference dispatched functions. We do
# this here, since we need to pass this module as an argument
# to these functions, in order to avoid circular dependencies
# between inference and node_classes.

_module = sys.modules[__name__]
inference.infer.register(treeabc.UnaryOp,
                         functools.partial(inference.filtered_infer_unaryop,
                                           nodes=_module))
inference.infer.register(treeabc.Arguments,
                         functools.partial(inference.infer_arguments,
                                           nodes=_module))
inference.infer.register(treeabc.BinOp,
                         functools.partial(inference.filtered_infer_binop,
                                           nodes=_module))
inference.infer.register(treeabc.AugAssign,
                         functools.partial(inference.filtered_infer_augassign,
                                           nodes=_module))
del _module
