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
"""this module contains a set of functions to handle python protocols for nodes
where it makes sense.
"""

import collections
import operator
import sys

import six

from astroid import context as contextmod
from astroid import decorators
from astroid import exceptions
from astroid.interpreter import runtimeabc
from astroid.interpreter import util as inferenceutil
from astroid.tree import treeabc
from astroid import util

raw_building = util.lazy_import('raw_building')


def _reflected_name(name):
    return "__r" + name[2:]

def _augmented_name(name):
    return "__i" + name[2:]


_CONTEXTLIB_MGR = 'contextlib.contextmanager'
BIN_OP_METHOD = {'+':  '__add__',
                 '-':  '__sub__',
                 '/':  '__div__' if six.PY2 else '__truediv__',
                 '//': '__floordiv__',
                 '*':  '__mul__',
                 '**': '__pow__',
                 '%':  '__mod__',
                 '&':  '__and__',
                 '|':  '__or__',
                 '^':  '__xor__',
                 '<<': '__lshift__',
                 '>>': '__rshift__',
                 '@': '__matmul__'
                }

REFLECTED_BIN_OP_METHOD = {
    key: _reflected_name(value)
    for (key, value) in BIN_OP_METHOD.items()
}
AUGMENTED_OP_METHOD = {
    key + "=": _augmented_name(value)
    for (key, value) in BIN_OP_METHOD.items()
}

UNARY_OP_METHOD = {'+': '__pos__',
                   '-': '__neg__',
                   '~': '__invert__',
                   'not': None, # XXX not '__nonzero__'
                  }
_UNARY_OPERATORS = {
    '+': operator.pos,
    '-': operator.neg,
    '~': operator.invert,
    'not': operator.not_,
}


def _infer_unary_op(obj, op, nodes):
    func = _UNARY_OPERATORS[op]
    value = func(obj)
    return raw_building.ast_from_object(value)



@util.singledispatch
def infer_unary_op(self, op, nodes):
    raise exceptions.UnaryOperationNotSupportedError


@infer_unary_op.register(treeabc.Tuple)
def _infer_unary_op_tuple(self, op, nodes):
    return _infer_unary_op(tuple(self.elts), op, nodes)


@infer_unary_op.register(treeabc.List)
def _infer_unary_op_list(self, op, nodes):
    return _infer_unary_op(self.elts, op, nodes)


@infer_unary_op.register(treeabc.Set)
def _infer_unary_op_set(self, op, nodes):
    return _infer_unary_op(set(self.elts), op, nodes)


@infer_unary_op.register(treeabc.Const)
def _infer_unary_op_const(self, op, nodes):
    return _infer_unary_op(self.value, op, nodes)


@infer_unary_op.register(treeabc.Dict)
def _infer_unary_op_dict(self, op, nodes):
    return _infer_unary_op(dict(self.items), op, nodes)


# Binary operations

BIN_OP_IMPL = {'+':  lambda a, b: a + b,
               '-':  lambda a, b: a - b,
               '/':  lambda a, b: a / b,
               '//': lambda a, b: a // b,
               '*':  lambda a, b: a * b,
               '**': lambda a, b: a ** b,
               '%':  lambda a, b: a % b,
               '&':  lambda a, b: a & b,
               '|':  lambda a, b: a | b,
               '^':  lambda a, b: a ^ b,
               '<<': lambda a, b: a << b,
               '>>': lambda a, b: a >> b,
              }
if sys.version_info >= (3, 5):
    # MatMult is available since Python 3.5+.
    BIN_OP_IMPL['@'] = operator.matmul

for _KEY, _IMPL in list(BIN_OP_IMPL.items()):
    BIN_OP_IMPL[_KEY + '='] = _IMPL


@util.singledispatch
def infer_binary_op(self, operator, other, context, method, nodes):
    raise exceptions.BinaryOperationNotSupportedError


@infer_binary_op.register(treeabc.Const)
@decorators.yes_if_nothing_inferred
def const_infer_binary_op(self, operator, other, context, _, nodes):
    not_implemented = nodes.NameConstant(NotImplemented)
    if isinstance(other, treeabc.Const):
        try:
            impl = BIN_OP_IMPL[operator]
            try:
                yield raw_building.ast_from_object(impl(self.value, other.value))
            except TypeError:
                # ArithmeticError is not enough: float >> float is a TypeError
                yield not_implemented
            except Exception: # pylint: disable=broad-except
                yield util.Uninferable
        except TypeError:
            yield not_implemented
    elif isinstance(self.value, six.string_types) and operator == '%':
        # TODO(cpopa): implement string interpolation later on.
        yield util.Uninferable
    else:
        yield not_implemented


def _multiply_seq_by_int(self, other, context):
    node = self.__class__()
    elts = []
    for elt in self.elts:
        infered = inferenceutil.safe_infer(elt, context)
        if infered is None:
            infered = util.Uninferable
        elts.append(infered)
    node.elts = elts * other.value
    return node


def _filter_uninferable_nodes(elts, context):
    for elt in elts:
        if elt is util.Uninferable:
            yield elt
        else:
            for inferred in elt.infer(context):
                yield inferred


@infer_binary_op.register(treeabc.Tuple)
@infer_binary_op.register(treeabc.List)
@decorators.yes_if_nothing_inferred
def tl_infer_binary_op(self, operator, other, context, method, nodes):
    not_implemented = nodes.NameConstant(NotImplemented)
    if isinstance(other, self.__class__) and operator == '+':
        node = self.__class__()
        elts = list(_filter_uninferable_nodes(self.elts, context))
        elts += list(_filter_uninferable_nodes(other.elts, context))
        node.elts = elts
        yield node
    elif isinstance(other, treeabc.Const) and operator == '*':
        if not isinstance(other.value, int):
            yield not_implemented
            return
        yield _multiply_seq_by_int(self, other, context)
    elif isinstance(other, runtimeabc.Instance) and operator == '*':
        # Verify if the instance supports __index__.
        as_index = inferenceutil.class_instance_as_index(other)
        if not as_index:
            yield util.Uninferable
        else:
            yield _multiply_seq_by_int(self, as_index, context)
    else:
        yield not_implemented


@infer_binary_op.register(runtimeabc.Instance)
@decorators.yes_if_nothing_inferred
def instance_infer_binary_op(self, operator, other, context, method, nodes):
    return method.infer_call_result(self, context)


@util.singledispatch
def assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    raise exceptions.NotSupportedError


def _resolve_looppart(parts, asspath, context):
    """recursive function to resolve multiple assignments on loops"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if part is util.Uninferable:
            continue
        # XXX handle __iter__ and log potentially detected errors
        if not hasattr(part, 'itered'):
            continue
        try:
            itered = part.itered()
        except TypeError:
            continue # XXX log error
        for stmt in itered:
            try:
                assigned = stmt.getitem(index, context)
            except (AttributeError, IndexError):
                continue
            except TypeError: # stmt is unsubscriptable Const
                continue
            if not asspath:
                # we achieved to resolved the assignment path,
                # don't infer the last part
                yield assigned
            elif assigned is util.Uninferable:
                break
            else:
                # we are not yet on the last part of the path
                # search on each possibly inferred value
                try:
                    for inferred in _resolve_looppart(assigned.infer(context),
                                                      asspath, context):
                        yield inferred
                except exceptions.InferenceError:
                    break


@assigned_stmts.register(treeabc.For)
@assigned_stmts.register(treeabc.Comprehension)
@decorators.raise_if_nothing_inferred
def for_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    if asspath is None:
        for lst in self.iter.infer(context):
            if isinstance(lst, (treeabc.Tuple, treeabc.List)):
                for item in lst.elts:
                    yield item
    else:
        for inferred in _resolve_looppart(self.iter.infer(context),
                                          asspath, context):
            yield inferred
    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, unknown=node,
                             assign_path=asspath, context=context))


@assigned_stmts.register(treeabc.Tuple)
@assigned_stmts.register(treeabc.List)
def mulass_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    if asspath is None:
        asspath = []

    try:
        index = self.elts.index(node)
    except ValueError:
         util.reraise(exceptions.InferenceError(
             'Tried to retrieve a node {node!r} which does not exist',
             node=self, assign_path=asspath, context=context))

    asspath.insert(0, index)
    return self.parent.assigned_stmts(node=self, context=context, asspath=asspath)


@assigned_stmts.register(treeabc.AssignName)
@assigned_stmts.register(treeabc.AssignAttr)
def assend_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    return self.parent.assigned_stmts(self, context=context)


def _arguments_infer_argname(self, name, context, nodes):
    # arguments information may be missing, in which case we can't do anything
    # more
    if not (self.args or self.vararg or self.kwarg):
        yield util.Uninferable
        return
    # first argument of instance/class method
    if self.args and getattr(self.args[0], 'name', None) == name:
        functype = self.parent.type
        cls = self.parent.parent.scope()
        is_metaclass = isinstance(cls, treeabc.ClassDef) and cls.type == 'metaclass'
        # If this is a metaclass, then the first argument will always
        # be the class, not an instance.
        if is_metaclass or functype == 'classmethod':
            yield cls
            return
        if functype == 'method':
            yield self.parent.parent.frame().instantiate_class()
            return

    if context and context.callcontext:
        call_site = self.parent.called_with(context.callcontext.args,
                                            context.callcontext.keywords)
        for value in call_site.infer_argument(name, context):
            yield value
        return

    # TODO: just provide the type here, no need to have an empty Dict.
    if name == self.vararg:
        yield nodes.Tuple(parent=self)
        return
    if name == self.kwarg:
        yield nodes.Dict(parent=self)
        return
    # if there is a default value, yield it. And then yield Uninferable to reflect
    # we can't guess given argument value
    try:
        context = contextmod.copy_context(context)
        for inferred in self.default_value(name).infer(context):
            yield inferred
        yield util.Uninferable
    except exceptions.NoDefault:
        yield util.Uninferable


@assigned_stmts.register(treeabc.Arguments)
def arguments_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    if context.callcontext:
        # reset call context/name
        callcontext = context.callcontext
        context = contextmod.copy_context(context)
        context.callcontext = None
        call_site = self.parent.called_with(callcontext.args,
                                            callcontext.keywords)
        return call_site.infer_argument(node.name, context)
    return _arguments_infer_argname(self, node.name, context, nodes)


@assigned_stmts.register(treeabc.Assign)
@assigned_stmts.register(treeabc.AugAssign)
@decorators.raise_if_nothing_inferred
def assign_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    if not asspath:
        yield self.value
        return
    for inferred in _resolve_asspart(self.value.infer(context), asspath, context):
        yield inferred

    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, unknown=node,
                             assign_path=asspath, context=context))


def _resolve_asspart(parts, asspath, context):
    """recursive function to resolve multiple assignments"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if hasattr(part, 'getitem'):
            try:
                assigned = part.getitem(index, context)
            # XXX raise a specific exception to avoid potential hiding of
            # unexpected exception ?
            except (TypeError, IndexError):
                return
            if not asspath:
                # we achieved to resolved the assignment path, don't infer the
                # last part
                yield assigned
            elif assigned is util.Uninferable:
                return
            else:
                # we are not yet on the last part of the path search on each
                # possibly inferred value
                try:
                    for inferred in _resolve_asspart(assigned.infer(context),
                                                     asspath, context):
                        yield inferred
                except exceptions.InferenceError:
                    return


@assigned_stmts.register(treeabc.ExceptHandler)
@decorators.raise_if_nothing_inferred
def excepthandler_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    for assigned in inferenceutil.unpack_infer(self.type):
        if isinstance(assigned, treeabc.ClassDef):
            assigned = assigned.instantiate_class()
        yield assigned

    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, unknown=node,
                             assign_path=asspath, context=context))


def _infer_context_manager(self, mgr, context, nodes):
    try:
        inferred = next(mgr.infer(context=context))
    except exceptions.InferenceError:
        return
    if isinstance(inferred, runtimeabc.Generator):
        # Check if it is decorated with contextlib.contextmanager.
        func = inferred.parent
        if not func.decorators:
            return
        for decorator_node in func.decorators.nodes:
            decorator = next(decorator_node.infer(context))
            if isinstance(decorator, treeabc.FunctionDef):
                if decorator.qname() == _CONTEXTLIB_MGR:
                    break
        else:
            # It doesn't interest us.
            return

        # Get the first yield point. If it has multiple yields,
        # then a RuntimeError will be raised.
        # TODO(cpopa): Handle flows.
        yield_point = next(func.nodes_of_class(treeabc.Yield), None)
        if yield_point:
            if not yield_point.value:
                # TODO(cpopa): an empty yield. Should be wrapped to Const.
                const = nodes.NameConstant(None, lineno=yield_point.lineno, parent=yield_point)
                yield const
            else:
                for inferred in yield_point.value.infer(context=context):
                    yield inferred
    elif isinstance(inferred, runtimeabc.Instance):
        try:
            enter = next(inferred.igetattr('__enter__', context=context))
        except (exceptions.InferenceError, exceptions.AttributeInferenceError):
            return
        if not isinstance(enter, runtimeabc.BoundMethod):
            return
        if not context.callcontext:
            context.callcontext = contextmod.CallContext(args=[inferred])
        for result in enter.infer_call_result(self, context):
            yield result


@assigned_stmts.register(treeabc.With)
@decorators.raise_if_nothing_inferred
def with_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    """Infer names and other nodes from a *with* statement.

    This enables only inference for name binding in a *with* statement.
    For instance, in the following code, inferring `func` will return
    the `ContextManager` class, not whatever ``__enter__`` returns.
    We are doing this intentionally, because we consider that the context
    manager result is whatever __enter__ returns and what it is binded
    using the ``as`` keyword.

        class ContextManager(object):
            def __enter__(self):
                return 42
        with ContextManager() as f:
            pass
        # ContextManager().infer() will return ContextManager
        # f.infer() will return 42.

    Arguments:
        self: nodes.With
        node: The target of the assignment, `as (a, b)` in `with foo as (a, b)`.
        context: TODO
        asspath: TODO
    """
    mgr = next(mgr for (mgr, vars) in self.items if vars == node)
    if asspath is None:
        for result in _infer_context_manager(self, mgr, context, nodes):
            yield result
    else:
        for result in _infer_context_manager(self, mgr, context, nodes):
            # Walk the asspath and get the item at the final index.
            obj = result
            for index in asspath:
                if not hasattr(obj, 'elts'):
                    raise exceptions.InferenceError(
                        'Wrong type ({targets!r}) for {node!r} assignment',
                        node=self, targets=node, assign_path=asspath,
                        context=context)

                try:
                    obj = obj.elts[index]
                except IndexError:
                    util.reraise(exceptions.InferenceError(
                        'Tried to infer a nonexistent target with index {index} '
                        'in {node!r}.', node=self, targets=node,
                        assign_path=asspath, context=context))

            yield obj
    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, unknown=node,
                             assign_path=asspath, context=context))


@assigned_stmts.register(treeabc.Starred)
@decorators.yes_if_nothing_inferred
def starred_assigned_stmts(self, nodes, node=None, context=None, asspath=None):
    """
    Arguments:
        self: nodes.Starred
        node: TODO
        context: TODO
        asspath: TODO
    """
    stmt = self.statement()
    if not isinstance(stmt, (treeabc.Assign, treeabc.For)):
        raise exceptions.InferenceError('Statement {stmt!r} enclosing {node!r} '
                                        'must be an Assign or For node.',
                                        node=self, stmt=stmt, unknown=node,
                                        context=context)

    if isinstance(stmt, treeabc.Assign):
        value = stmt.value
        lhs = stmt.targets[0]

        if sum(1 for node in lhs.nodes_of_class(treeabc.Starred)) > 1:
            raise exceptions.InferenceError('Too many starred arguments in the '
                                            ' assignment targets {lhs!r}.',
                                            node=self, targets=lhs,
                                            unknown=node, context=context)

        if context is None:
            context = contextmod.InferenceContext()
        try:
            rhs = next(value.infer(context))
        except exceptions.InferenceError:
            yield util.Uninferable
            return
        if rhs is util.Uninferable or not hasattr(rhs, 'elts'):
            # Not interested in inferred values without elts.
            yield util.Uninferable
            return

        if len(lhs.elts) > len(rhs.elts) + 1:
            # Since there is only one Starred node on the
            # left hand side, the lhs number of elements
            # can be at most N + 1, where N is the number of elements
            # of rhs.
            raise exceptions.InferenceError('More targets, {targets!r}, than '
                                            'values to unpack, {values!r}.',
                                            node=self, targets=lhs,
                                            values=rhs, unknown=node,
                                            context=context)

        elts = collections.deque(rhs.elts[:])
        # Unpack iteratively the values from the rhs of the assignment,
        # until the find the starred node. What will remain will
        # be the list of values which the Starred node will represent
        # This is done in two steps, from left to right to remove
        # anything before the starred node and from right to left
        # to remove anything after the starred node.

        for index, node in enumerate(lhs.elts):
            if not isinstance(node, treeabc.Starred):
                elts.popleft()
                continue
            lhs_elts = collections.deque(reversed(lhs.elts[index:]))
            for node in lhs_elts:
                if not isinstance(node, treeabc.Starred):
                    elts.pop()
                    continue
                # We're done.
                packed = nodes.List(parent=self)
                packed.postinit(elts=elts)
                yield packed
                break
            break
