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

from astroid.exceptions import InferenceError, NoDefault, NotFoundError
from astroid.node_classes import unpack_infer
from astroid.bases import (
    InferenceContext, copy_context,
    raise_if_nothing_infered, yes_if_nothing_infered,
    Instance, YES, BoundMethod,
    Generator,
)
from astroid.nodes import const_factory
from astroid import nodes

_CONTEXTLIB_MGR = 'contextlib.contextmanager'
BIN_OP_METHOD = {'+':  '__add__',
                 '-':  '__sub__',
                 '/':  '__div__',
                 '//': '__floordiv__',
                 '*':  '__mul__',
                 '**': '__power__',
                 '%':  '__mod__',
                 '&':  '__and__',
                 '|':  '__or__',
                 '^':  '__xor__',
                 '<<': '__lshift__',
                 '>>': '__rshift__',
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


def _infer_unary_op(obj, op):
    func = _UNARY_OPERATORS[op]
    value = func(obj)
    return const_factory(value)

nodes.Tuple.infer_unary_op = lambda self, op: _infer_unary_op(tuple(self.elts), op)
nodes.List.infer_unary_op = lambda self, op: _infer_unary_op(self.elts, op)
nodes.Set.infer_unary_op = lambda self, op: _infer_unary_op(set(self.elts), op)
nodes.Const.infer_unary_op = lambda self, op: _infer_unary_op(self.value, op)
nodes.Dict.infer_unary_op = lambda self, op: _infer_unary_op(dict(self.items), op)



# binary operations ###########################################################

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
for _KEY, _IMPL in list(BIN_OP_IMPL.items()):
    BIN_OP_IMPL[_KEY + '='] = _IMPL

def const_infer_binary_op(self, operator, other, context):
    for other in other.infer(context):
        if isinstance(other, nodes.Const):
            try:
                impl = BIN_OP_IMPL[operator]

                try:
                    yield const_factory(impl(self.value, other.value))
                except Exception: # pylint: disable=broad-except
                    # ArithmeticError is not enough: float >> float is a TypeError
                    # TODO : let pylint know about the problem
                    pass
            except TypeError:
                # XXX log TypeError
                continue
        elif other is YES:
            yield other
        else:
            try:
                for val in other.infer_binary_op(operator, self, context):
                    yield val
            except AttributeError:
                yield YES
nodes.Const.infer_binary_op = yes_if_nothing_infered(const_infer_binary_op)


def tl_infer_binary_op(self, operator, other, context):
    for other in other.infer(context):
        if isinstance(other, self.__class__) and operator == '+':
            node = self.__class__()
            elts = [n for elt in self.elts for n in elt.infer(context)
                    if not n is YES]
            elts += [n for elt in other.elts for n in elt.infer(context)
                     if not n is YES]
            node.elts = elts
            yield node
        elif isinstance(other, nodes.Const) and operator == '*':
            if not isinstance(other.value, int):
                yield YES
                continue
            node = self.__class__()
            elts = [n for elt in self.elts for n in elt.infer(context)
                    if not n is YES] * other.value
            node.elts = elts
            yield node
        elif isinstance(other, Instance) and not isinstance(other, nodes.Const):
            yield YES
    # XXX else log TypeError
nodes.Tuple.infer_binary_op = yes_if_nothing_infered(tl_infer_binary_op)
nodes.List.infer_binary_op = yes_if_nothing_infered(tl_infer_binary_op)


def dict_infer_binary_op(self, operator, other, context):
    for other in other.infer(context):
        if isinstance(other, Instance) and isinstance(other._proxied, nodes.Class):
            yield YES
        # XXX else log TypeError
nodes.Dict.infer_binary_op = yes_if_nothing_infered(dict_infer_binary_op)

def instance_infer_binary_op(self, operator, other, context):
    try:
        methods = self.getattr(BIN_OP_METHOD[operator])
    except (NotFoundError, KeyError):
        # Unknown operator
        yield YES
    else:
        for method in methods:
            if not isinstance(method, nodes.Function):
                continue
            for result in method.infer_call_result(self, context):
                if result is not YES:
                    yield result
            # We are interested only in the first infered method,
            # don't go looking in the rest of the methods of the ancestors.
            break

Instance.infer_binary_op = yes_if_nothing_infered(instance_infer_binary_op)


# assignment ##################################################################

"""the assigned_stmts method is responsible to return the assigned statement
(e.g. not inferred) according to the assignment type.

The `asspath` argument is used to record the lhs path of the original node.
For instance if we want assigned statements for 'c' in 'a, (b,c)', asspath
will be [1, 1] once arrived to the Assign node.

The `context` argument is the current inference context which should be given
to any intermediary inference necessary.
"""

def _resolve_looppart(parts, asspath, context):
    """recursive function to resolve multiple assignments on loops"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if part is YES:
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
            elif assigned is YES:
                break
            else:
                # we are not yet on the last part of the path
                # search on each possibly inferred value
                try:
                    for infered in _resolve_looppart(assigned.infer(context),
                                                     asspath, context):
                        yield infered
                except InferenceError:
                    break


def for_assigned_stmts(self, node, context=None, asspath=None):
    if asspath is None:
        for lst in self.iter.infer(context):
            if isinstance(lst, (nodes.Tuple, nodes.List)):
                for item in lst.elts:
                    yield item
    else:
        for infered in _resolve_looppart(self.iter.infer(context),
                                         asspath, context):
            yield infered

nodes.For.assigned_stmts = raise_if_nothing_infered(for_assigned_stmts)
nodes.Comprehension.assigned_stmts = raise_if_nothing_infered(for_assigned_stmts)


def mulass_assigned_stmts(self, node, context=None, asspath=None):
    if asspath is None:
        asspath = []
    asspath.insert(0, self.elts.index(node))
    return self.parent.assigned_stmts(self, context, asspath)
nodes.Tuple.assigned_stmts = mulass_assigned_stmts
nodes.List.assigned_stmts = mulass_assigned_stmts


def assend_assigned_stmts(self, context=None):
    return self.parent.assigned_stmts(self, context=context)
nodes.AssName.assigned_stmts = assend_assigned_stmts
nodes.AssAttr.assigned_stmts = assend_assigned_stmts


def _arguments_infer_argname(self, name, context):
    # arguments information may be missing, in which case we can't do anything
    # more
    if not (self.args or self.vararg or self.kwarg):
        yield YES
        return
    # first argument of instance/class method
    if self.args and getattr(self.args[0], 'name', None) == name:
        functype = self.parent.type
        if functype == 'method':
            yield Instance(self.parent.parent.frame())
            return
        if functype == 'classmethod':
            yield self.parent.parent.frame()
            return
    if name == self.vararg:
        vararg = const_factory(())
        vararg.parent = self
        yield vararg
        return
    if name == self.kwarg:
        kwarg = const_factory({})
        kwarg.parent = self
        yield kwarg
        return
    # if there is a default value, yield it. And then yield YES to reflect
    # we can't guess given argument value
    try:
        context = copy_context(context)
        for infered in self.default_value(name).infer(context):
            yield infered
        yield YES
    except NoDefault:
        yield YES


def arguments_assigned_stmts(self, node, context, asspath=None):
    if context.callcontext:
        # reset call context/name
        callcontext = context.callcontext
        context = copy_context(context)
        context.callcontext = None
        return callcontext.infer_argument(self.parent, node.name, context)
    return _arguments_infer_argname(self, node.name, context)
nodes.Arguments.assigned_stmts = arguments_assigned_stmts


def assign_assigned_stmts(self, node, context=None, asspath=None):
    if not asspath:
        yield self.value
        return
    for infered in _resolve_asspart(self.value.infer(context), asspath, context):
        yield infered
nodes.Assign.assigned_stmts = raise_if_nothing_infered(assign_assigned_stmts)
nodes.AugAssign.assigned_stmts = raise_if_nothing_infered(assign_assigned_stmts)


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
            elif assigned is YES:
                return
            else:
                # we are not yet on the last part of the path search on each
                # possibly inferred value
                try:
                    for infered in _resolve_asspart(assigned.infer(context),
                                                    asspath, context):
                        yield infered
                except InferenceError:
                    return


def excepthandler_assigned_stmts(self, node, context=None, asspath=None):
    for assigned in unpack_infer(self.type):
        if isinstance(assigned, nodes.Class):
            assigned = Instance(assigned)
        yield assigned
nodes.ExceptHandler.assigned_stmts = raise_if_nothing_infered(excepthandler_assigned_stmts)


def _infer_context_manager(self, mgr, context):
    try:
        inferred = next(mgr.infer(context=context))
    except InferenceError:
        return
    if isinstance(inferred, Generator):
        # Check if it is decorated with contextlib.contextmanager.
        func = inferred.parent
        if not func.decorators:
            return
        for decorator_node in func.decorators.nodes:
            decorator = next(decorator_node.infer(context))
            if isinstance(decorator, nodes.Function):
                if decorator.qname() == _CONTEXTLIB_MGR:
                    break
        else:
            # It doesn't interest us.
            return

        # Get the first yield point. If it has multiple yields,
        # then a RuntimeError will be raised.
        # TODO(cpopa): Handle flows.
        yield_point = next(func.nodes_of_class(nodes.Yield), None)
        if yield_point:
            if not yield_point.value:
                # TODO(cpopa): an empty yield. Should be wrapped to Const.
                const = nodes.Const(None)
                const.parent = yield_point
                const.lineno = yield_point.lineno
                yield const
            else:
                for inferred in yield_point.value.infer(context=context):
                    yield inferred
    elif isinstance(inferred, Instance):
        try:
            enter = next(inferred.igetattr('__enter__', context=context))
        except (InferenceError, NotFoundError):
            return
        if not isinstance(enter, BoundMethod):
            return
        for result in enter.infer_call_result(self, context):
            yield result

def with_assigned_stmts(self, node, context=None, asspath=None):
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
    """

    mgr = next(mgr for (mgr, vars) in self.items if vars == node)
    if asspath is None:
        for result in _infer_context_manager(self, mgr, context):
            yield result
    else:
        for result in _infer_context_manager(self, mgr, context):
            # Walk the asspath and get the item at the final index.
            obj = result
            for index in asspath:
                if not hasattr(obj, 'elts'):
                    raise InferenceError
                try:
                    obj = obj.elts[index]
                except IndexError:
                    raise InferenceError
            yield obj


nodes.With.assigned_stmts = raise_if_nothing_infered(with_assigned_stmts)


def starred_assigned_stmts(self, node=None, context=None, asspath=None):
    stmt = self.statement()
    if not isinstance(stmt, (nodes.Assign, nodes.For)):
        raise InferenceError()

    if isinstance(stmt, nodes.Assign):
        value = stmt.value
        lhs = stmt.targets[0]

        if sum(1 for node in lhs.nodes_of_class(nodes.Starred)) > 1:
            # Too many starred arguments in the expression.
            raise InferenceError()

        if context is None:
            context = InferenceContext()
        try:
            rhs = next(value.infer(context))
        except InferenceError:
            yield YES
            return
        if rhs is YES or not hasattr(rhs, 'elts'):
            # Not interested in inferred values without elts.
            yield YES
            return

        elts = collections.deque(rhs.elts[:])
        if len(lhs.elts) > len(rhs.elts):
            # a, *b, c = (1, 2)
            raise InferenceError()

        # Unpack iteratively the values from the rhs of the assignment,
        # until the find the starred node. What will remain will
        # be the list of values which the Starred node will represent
        # This is done in two steps, from left to right to remove
        # anything before the starred node and from right to left
        # to remvoe anything after the starred node.

        for index, node in enumerate(lhs.elts):
            if not isinstance(node, nodes.Starred):
                elts.popleft()
                continue
            lhs_elts = collections.deque(reversed(lhs.elts[index:]))
            for node in lhs_elts:
                if not isinstance(node, nodes.Starred):
                    elts.pop()
                    continue
                # We're done
                for elt in elts:
                    yield elt
                break

nodes.Starred.assigned_stmts = starred_assigned_stmts
