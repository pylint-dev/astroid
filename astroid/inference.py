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
"""this module contains a set of functions to handle inference on astroid trees
"""

# pylint: disable=no-value-for-parameter; Pylint FP #629, please remove afterwards.

import functools
import itertools
import operator

from astroid import context as contextmod
from astroid import decorators
from astroid import exceptions
from astroid import helpers
from astroid.interpreter import runtimeabc
from astroid.interpreter import util as inferenceutil
from astroid import manager
from astroid import protocols
from astroid.tree import treeabc
from astroid import util


MANAGER = manager.AstroidManager()


@util.singledispatch
def infer(self, context=None):
    raise exceptions.InferenceError


@infer.register(treeabc.Module)
@infer.register(treeabc.ClassDef)
@infer.register(treeabc.FunctionDef)
@infer.register(treeabc.Lambda)
@infer.register(treeabc.Const)
@infer.register(treeabc.List)
@infer.register(treeabc.Tuple)
@infer.register(treeabc.Dict)
@infer.register(treeabc.Set)
@infer.register(treeabc.Slice)
@infer.register(runtimeabc.Super)
@infer.register(runtimeabc.FrozenSet)
def infer_end(self, context=None):
    yield self


def _higher_function_scope(node):
    """ Search for the first function which encloses the given
    scope. This can be used for looking up in that function's
    scope, in case looking up in a lower scope for a particular
    name fails.

    :param node: A scope node.
    :returns:
        ``None``, if no parent function scope was found,
        otherwise an instance of :class:`astroid.scoped_nodes.Function`,
        which encloses the given node.
    """
    current = node
    while current.parent and not isinstance(current.parent, treeabc.FunctionDef):
        current = current.parent
    if current and current.parent:
        return current.parent


def infer_name(self, context=None):
    """infer a Name: use name lookup rules"""
    frame, stmts = self.lookup(self.name)
    if not stmts:
        # Try to see if the name is enclosed in a nested function
        # and use the higher (first function) scope for searching.
        # TODO: should this be promoted to other nodes as well?
        parent_function = _higher_function_scope(self.scope())
        if parent_function:
            _, stmts = parent_function.lookup(self.name)

        if not stmts:
            raise exceptions.UnresolvableName(self.name)
    context = context.clone()
    context.lookupname = self.name
    return inferenceutil.infer_stmts(stmts, context, frame)

infer.register(treeabc.Name, decorators.path_wrapper(infer_name))


@infer.register(treeabc.Call)
@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_call(self, context=None):
    """infer a Call node by trying to guess what the function returns"""
    callcontext = context.clone()
    callcontext.callcontext = contextmod.CallContext(args=self.args,
                                                     keywords=self.keywords)
    callcontext.boundnode = None
    for callee in self.func.infer(context):
        if callee is util.Uninferable:
            yield callee
            continue
        try:
            if hasattr(callee, 'infer_call_result'):
                for inferred in callee.infer_call_result(self, callcontext):
                    yield inferred
        except exceptions.InferenceError:
            ## XXX log error ?
            continue


@infer.register(treeabc.Import)
@decorators.path_wrapper
def infer_import(self, context=None, asname=True):
    """infer an Import node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError()
    if asname:
        yield self.do_import_module(self.real_name(name))
    else:
        yield self.do_import_module(name)


@infer.register(treeabc.ImportFrom)
@decorators.path_wrapper
def infer_import_from(self, context=None, asname=True):
    """infer a ImportFrom node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError()
    if asname:
        name = self.real_name(name)
    module = self.do_import_module()
    try:
        context = contextmod.copy_context(context)
        context.lookupname = name
        stmts = module.getattr(name, ignore_locals=module is self.root())
        return inferenceutil.infer_stmts(stmts, context)
    except exceptions.NotFoundError:
        util.reraise(exceptions.InferenceError(name))


@decorators.raise_if_nothing_inferred
def infer_attribute(self, context=None):
    """infer an Attribute node by using getattr on the associated object"""
    for owner in self.expr.infer(context):
        if owner is util.Uninferable:
            yield owner
            continue
        try:
            context.boundnode = owner
            for obj in owner.igetattr(self.attrname, context):
                yield obj
            context.boundnode = None
        except (exceptions.NotFoundError, exceptions.InferenceError):
            context.boundnode = None
        except AttributeError:
            # XXX method / function
            context.boundnode = None

infer.register(treeabc.Attribute, decorators.path_wrapper(infer_attribute))


@infer.register(treeabc.Global)
@decorators.path_wrapper
def infer_global(self, context=None):
    if context.lookupname is None:
        raise exceptions.InferenceError()
    try:
        return inferenceutil.infer_stmts(self.root().getattr(context.lookupname),
                                         context)
    except exceptions.NotFoundError:
        util.reraise(exceptions.InferenceError())


_SLICE_SENTINEL = object()

def _slice_value(index, context=None):
    """Get the value of the given slice index."""
    if isinstance(index, treeabc.Const):
        if isinstance(index.value, (int, type(None))):
            return index.value
    elif index is None:
        return None
    else:
        # Try to infer what the index actually is.
        # Since we can't return all the possible values,
        # we'll stop at the first possible value.
        try:
            inferred = next(index.infer(context=context))
        except exceptions.InferenceError:
            pass
        else:
            if isinstance(inferred, treeabc.Const):
                if isinstance(inferred.value, (int, type(None))):
                    return inferred.value

    # Use a sentinel, because None can be a valid
    # value that this function can return,
    # as it is the case for unspecified bounds.
    return _SLICE_SENTINEL


@decorators.raise_if_nothing_inferred
def infer_subscript(self, context=None):
    """Inference for subscripts

    We're understanding if the index is a Const
    or a slice, passing the result of inference
    to the value's `getitem` method, which should
    handle each supported index type accordingly.
    """

    value = next(self.value.infer(context))
    if value is util.Uninferable:
        yield util.Uninferable
        return

    index = next(self.slice.infer(context))
    if index is util.Uninferable:
        yield util.Uninferable
        return

    if isinstance(value, runtimeabc.Instance):
        index_value = index
    else:
        index_value = _SLICE_SENTINEL
        if isinstance(index, treeabc.Const):
            index_value = index.value
        elif isinstance(index, treeabc.Slice):
            # Infer slices from the original object.
            lower = _slice_value(index.lower, context)
            upper = _slice_value(index.upper, context)
            step = _slice_value(index.step, context)
            if all(elem is not _SLICE_SENTINEL for elem in (lower, upper, step)):
                index_value = slice(lower, upper, step)
        elif isinstance(index, runtimeabc.Instance):
            index = inferenceutil.class_instance_as_index(index)
            if index:
                index_value = index.value
        else:
            raise exceptions.InferenceError()

    if index_value is _SLICE_SENTINEL:
        raise exceptions.InferenceError

    try:
        assigned = value.getitem(index_value, context)
    except (IndexError, TypeError, AttributeError) as exc:
        util.reraise(exceptions.InferenceError(*exc.args))

    # Prevent inferring if the inferred subscript
    # is the same as the original subscripted object.
    if self is assigned or assigned is util.Uninferable:
        yield util.Uninferable
        return
    for inferred in assigned.infer(context):
        yield inferred

infer.register(treeabc.Subscript, decorators.path_wrapper(infer_subscript))


@infer.register(treeabc.BoolOp)
@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def _infer_boolop(self, context=None):
    """Infer a boolean operation (and / or / not).

    The function will calculate the boolean operation
    for all pairs generated through inference for each component
    node.
    """
    values = self.values
    if self.op == 'or':
        predicate = operator.truth
    else:
        predicate = operator.not_

    try:
        values = [value.infer(context=context) for value in values]
    except exceptions.InferenceError:
        yield util.Uninferable
        return

    for pair in itertools.product(*values):
        if any(item is util.Uninferable for item in pair):
            # Can't infer the final result, just yield Uninferable.
            yield util.Uninferable
            continue

        bool_values = [item.bool_value() for item in pair]
        if any(item is util.Uninferable for item in bool_values):
            # Can't infer the final result, just yield Uninferable.
            yield util.Uninferable
            continue

        # Since the boolean operations are short circuited operations,
        # this code yields the first value for which the predicate is True
        # and if no value respected the predicate, then the last value will
        # be returned (or Uninferable if there was no last value).
        # This is conforming to the semantics of `and` and `or`:
        #   1 and 0 -> 1
        #   0 and 1 -> 0
        #   1 or 0 -> 1
        #   0 or 1 -> 1
        value = util.Uninferable
        for value, bool_value in zip(pair, bool_values):
            if predicate(bool_value):
                yield value
                break
        else:
            yield value


# UnaryOp, BinOp and AugAssign inferences

def _filter_operation_errors(self, infer_callable, context, error):
    for result in infer_callable(self, context):
        if isinstance(result, error):
            # For the sake of .infer(), we don't care about operation
            # errors, which is the job of pylint. So return something
            # which shows that we can't infer the result.
            yield util.Uninferable
        else:
            yield result


def infer_unaryop(self, context=None, nodes=None):
    """Infer what an UnaryOp should return when evaluated."""
    for operand in self.operand.infer(context):
        try:
            yield protocols.infer_unary_op(operand, self.op, nodes)
        except TypeError as exc:
            # The operand doesn't support this operation.
            yield exceptions.UnaryOperationError(operand, self.op, exc)
        except exceptions.UnaryOperationNotSupportedError as exc:
            meth = protocols.UNARY_OP_METHOD[self.op]
            if meth is None:
                # `not node`. Determine node's boolean
                # value and negate its result, unless it is
                # Uninferable, which will be returned as is.
                bool_value = operand.bool_value()
                if bool_value is not util.Uninferable:
                    yield nodes.const_factory(not bool_value)
                else:
                    yield util.Uninferable
            else:
                if not isinstance(operand, runtimeabc.Instance):
                    # The operation was used on something which
                    # doesn't support it.
                    yield exceptions.UnaryOperationError(operand, self.op, exc)
                    continue

                try:
                    meth = operand.getattr(meth, context=context)[0]
                    inferred = next(meth.infer(context=context))
                    if inferred is util.Uninferable or not inferred.callable():
                        continue

                    context = contextmod.copy_context(context)
                    context.callcontext = contextmod.CallContext(args=[operand])
                    call_results = inferred.infer_call_result(self, context=context)
                    result = next(call_results, None)
                    if result is None:
                        # Failed to infer, return the same type.
                        yield operand
                    else:
                        yield result
                except exceptions.NotFoundError as exc:
                    # The unary operation special method was not found.
                    yield exceptions.UnaryOperationError(operand, self.op, exc)
                except exceptions.InferenceError:
                    yield util.Uninferable


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def filtered_infer_unaryop(self, context=None, nodes=None):
    """Infer what an UnaryOp should return when evaluated."""
    with_nodes_func = functools.partial(infer_unaryop, nodes=nodes)
    return _filter_operation_errors(self, with_nodes_func, context,
                                    exceptions.UnaryOperationError)


def _is_not_implemented(const):
    """Check if the given const node is NotImplemented."""
    return isinstance(const, treeabc.Const) and const.value is NotImplemented


def _invoke_binop_inference(instance, op, other, context, method_name, nodes):
    """Invoke binary operation inference on the given instance."""
    method = instance.getattr(method_name)[0]
    inferred = next(method.infer(context=context))
    return protocols.infer_binary_op(instance, op, other, context, inferred, nodes)


def _aug_op(instance, op, other, context, nodes, reverse=False):
    """Get an inference callable for an augmented binary operation."""
    method_name = protocols.AUGMENTED_OP_METHOD[op]
    return functools.partial(_invoke_binop_inference,
                             instance=instance,
                             op=op, other=other,
                             context=context,
                             method_name=method_name,
                             nodes=nodes)


def _bin_op(instance, op, other, context, nodes, reverse=False):
    """Get an inference callable for a normal binary operation.

    If *reverse* is True, then the reflected method will be used instead.
    """
    if reverse:
        method_name = protocols.REFLECTED_BIN_OP_METHOD[op]
    else:
        method_name = protocols.BIN_OP_METHOD[op]
    return functools.partial(_invoke_binop_inference,
                             instance=instance,
                             op=op, other=other,
                             context=context,
                             method_name=method_name,
                             nodes=nodes)


def _get_binop_contexts(context, left, right):
    """Get contexts for binary operations.

    This will return two inferrence contexts, the first one
    for x.__op__(y), the other one for y.__rop__(x), where
    only the arguments are inversed.
    """
    # The order is important, since the first one should be
    # left.__op__(right).
    for arg in (right, left):
        new_context = context.clone()
        new_context.callcontext = contextmod.CallContext(args=[arg])
        new_context.boundnode = None
        yield new_context


def _same_type(type1, type2):
    """Check if type1 is the same as type2."""
    return type1.qname() == type2.qname()


def _get_binop_flow(left, left_type, op, right, right_type,
                    context, reverse_context, nodes):
    """Get the flow for binary operations.

    The rules are a bit messy:

        * if left and right have the same type, then only one
          method will be called, left.__op__(right)
        * if left and right are unrelated typewise, then first
          left.__op__(right) is tried and if this does not exist
          or returns NotImplemented, then right.__rop__(left) is tried.
        * if left is a subtype of right, then only left.__op__(right)
          is tried.
        * if left is a supertype of right, then right.__rop__(left)
          is first tried and then left.__op__(right)
    """
    if _same_type(left_type, right_type):
        methods = [_bin_op(left, op, right, context, nodes)]
    elif inferenceutil.is_subtype(left_type, right_type):
        methods = [_bin_op(left, op, right, context, nodes)]
    elif inferenceutil.is_supertype(left_type, right_type):
        methods = [_bin_op(right, op, left, reverse_context, nodes, reverse=True),
                   _bin_op(left, op, right, context, nodes)]
    else:
        methods = [_bin_op(left, op, right, context, nodes),
                   _bin_op(right, op, left, reverse_context, nodes, reverse=True)]
    return methods


def _get_aug_flow(left, left_type, aug_op, right, right_type,
                  context, reverse_context, nodes):
    """Get the flow for augmented binary operations.

    The rules are a bit messy:

        * if left and right have the same type, then left.__augop__(right)
          is first tried and then left.__op__(right).
        * if left and right are unrelated typewise, then
          left.__augop__(right) is tried, then left.__op__(right)
          is tried and then right.__rop__(left) is tried.
        * if left is a subtype of right, then left.__augop__(right)
          is tried and then left.__op__(right).
        * if left is a supertype of right, then left.__augop__(right)
          is tried, then right.__rop__(left) and then
          left.__op__(right)
    """
    op = aug_op.strip("=")
    if _same_type(left_type, right_type):
        methods = [_aug_op(left, aug_op, right, context, nodes),
                   _bin_op(left, op, right, context, nodes)]
    elif inferenceutil.is_subtype(left_type, right_type):
        methods = [_aug_op(left, aug_op, right, context, nodes),
                   _bin_op(left, op, right, context, nodes)]
    elif inferenceutil.is_supertype(left_type, right_type):
        methods = [_aug_op(left, aug_op, right, context, nodes),
                   _bin_op(right, op, left, reverse_context, nodes, reverse=True),
                   _bin_op(left, op, right, context, nodes)]
    else:
        methods = [_aug_op(left, aug_op, right, context, nodes),
                   _bin_op(left, op, right, context, nodes),
                   _bin_op(right, op, left, reverse_context, nodes, reverse=True)]
    return methods


def _infer_binary_operation(left, right, op, context, flow_factory, nodes):
    """Infer a binary operation between a left operand and a right operand

    This is used by both normal binary operations and augmented binary
    operations, the only difference is the flow factory used.
    """

    context, reverse_context = _get_binop_contexts(context, left, right)
    left_type = helpers.object_type(left)
    right_type = helpers.object_type(right)
    methods = flow_factory(left, left_type, op, right, right_type,
                           context, reverse_context, nodes)
    for method in methods:
        try:
            results = list(method())
        except exceptions.BinaryOperationNotSupportedError:
            continue
        except (AttributeError, exceptions.NotFoundError):
            continue
        except exceptions.InferenceError:
            yield util.Uninferable
            return
        else:
            if any(result is util.Uninferable for result in results):
                yield util.Uninferable
                return

            # TODO(cpopa): since the inferrence engine might return
            # more values than are actually possible, we decide
            # to return util.Uninferable if we have union types.
            if all(map(_is_not_implemented, results)):
                continue
            not_implemented = sum(1 for result in results
                                  if _is_not_implemented(result))
            if not_implemented and not_implemented != len(results):
                # Can't decide yet what this is, not yet though.
                yield util.Uninferable
                return

            for result in results:
                yield result
            return
    # TODO(cpopa): yield a BinaryOperationError here,
    # since the operation is not supported
    yield exceptions.BinaryOperationError(left_type, op, right_type)


def infer_binop(self, context, nodes):
    """Binary operation inferrence logic."""
    if context is None:
        context = contextmod.InferenceContext()
    left = self.left
    right = self.right
    op = self.op

    # we use two separate contexts for evaluating lhs and rhs because
    # 1. evaluating lhs may leave some undesired entries in context.path
    #    which may not let us infer right value of rhs
    lhs_context = context.clone()
    rhs_context = context.clone()

    for lhs in left.infer(context=lhs_context):
        if lhs is util.Uninferable:
            # Don't know how to process this.
            yield util.Uninferable
            return

        for rhs in right.infer(context=rhs_context):
            if rhs is util.Uninferable:
                # Don't know how to process this.
                yield util.Uninferable
                return

            results = _infer_binary_operation(lhs, rhs, op, context,
                                              _get_binop_flow, nodes)
            for result in results:
                yield result


@decorators.yes_if_nothing_inferred
@decorators.path_wrapper
def filtered_infer_binop(self, context=None, nodes=None):
    with_nodes_func = functools.partial(infer_binop, nodes=nodes)
    return _filter_operation_errors(self, with_nodes_func, context,
                                    exceptions.BinaryOperationError)


def infer_augassign(self, context=None, nodes=None):
    """Inferrence logic for augmented binary operations."""
    if context is None:
        context = contextmod.InferenceContext()
    op = self.op

    for lhs in self.target.infer_lhs(context=context):
        if lhs is util.Uninferable:
            # Don't know how to process this.
            yield util.Uninferable
            return

        # TODO(cpopa): if we have A() * A(), trying to infer
        # the rhs with the same context will result in an
        # inferrence error, so we create another context for it.
        # This is a bug which should be fixed in InferenceContext at some point.
        rhs_context = context.clone()
        rhs_context.path = set()
        for rhs in self.value.infer(context=rhs_context):
            if rhs is util.Uninferable:
                # Don't know how to process this.
                yield util.Uninferable
                return

            results = _infer_binary_operation(lhs, rhs, op,
                                              context, _get_aug_flow, nodes)
            for result in results:
                yield result


@decorators.path_wrapper
def filtered_infer_augassign(self, context=None, nodes=None):
    with_nodes_func = functools.partial(infer_augassign, nodes=nodes)
    return _filter_operation_errors(self, with_nodes_func, context,
                                    exceptions.BinaryOperationError)


# End of binary operation inference.


def infer_arguments(self, context=None, nodes=None):
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError()
    return protocols._arguments_infer_argname(self, name, context, nodes)


@infer.register(treeabc.AssignName)
@infer.register(treeabc.AssignAttr)
@decorators.path_wrapper
def infer_assign(self, context=None):
    """infer a AssignName/AssignAttr: need to inspect the RHS part of the
    assign node
    """
    stmt = self.statement()
    if isinstance(stmt, treeabc.AugAssign):
        return stmt.infer(context)

    stmts = list(self.assigned_stmts(context=context))
    return inferenceutil.infer_stmts(stmts, context)


# no infer method on DelName and DelAttr (expected InferenceError)

@infer.register(treeabc.EmptyNode)
@decorators.path_wrapper
def infer_empty_node(self, context=None):
    if not self.has_underlying_object():
        yield util.Uninferable
    else:
        try:
            for inferred in MANAGER.infer_ast_from_something(self.object,
                                                             context=context):
                yield inferred
        except exceptions.AstroidError:
            yield util.Uninferable


@infer.register(treeabc.Index)
def infer_index(self, context=None):
    return self.value.infer(context)
