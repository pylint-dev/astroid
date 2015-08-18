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

from __future__ import print_function

import functools
import itertools
import operator

from astroid import bases
from astroid import context as contextmod
from astroid import exceptions
from astroid import helpers
from astroid import manager
from astroid import nodes
from astroid import protocols
from astroid import util


MANAGER = manager.AstroidManager()


# .infer method ###############################################################


def infer_end(self, context=None):
    """inference's end for node such as Module, Class, Function, Const...
    """
    yield self
nodes.Module._infer = infer_end
nodes.ClassDef._infer = infer_end
nodes.FunctionDef._infer = infer_end
nodes.Lambda._infer = infer_end
nodes.Const._infer = infer_end
nodes.List._infer = infer_end
nodes.Tuple._infer = infer_end
nodes.Dict._infer = infer_end
nodes.Set._infer = infer_end

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
    while current.parent and not isinstance(current.parent, nodes.FunctionDef):
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
    return bases._infer_stmts(stmts, context, frame)
nodes.Name._infer = bases.path_wrapper(infer_name)
nodes.AssignName.infer_lhs = infer_name # won't work with a path wrapper


@bases.raise_if_nothing_inferred
@bases.path_wrapper
def infer_call(self, context=None):
    """infer a Call node by trying to guess what the function returns"""
    callcontext = context.clone()
    callcontext.callcontext = contextmod.CallContext(args=self.args,
                                                     keywords=self.keywords,
                                                     starargs=self.starargs,
                                                     kwargs=self.kwargs)
    callcontext.boundnode = None
    for callee in self.func.infer(context):
        if callee is util.YES:
            yield callee
            continue
        try:
            if hasattr(callee, 'infer_call_result'):
                for inferred in callee.infer_call_result(self, callcontext):
                    yield inferred
        except exceptions.InferenceError:
            ## XXX log error ?
            continue
nodes.Call._infer = infer_call


@bases.path_wrapper
def infer_import(self, context=None, asname=True):
    """infer an Import node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError()
    if asname:
        yield self.do_import_module(self.real_name(name))
    else:
        yield self.do_import_module(name)
nodes.Import._infer = infer_import


def infer_name_module(self, name):
    context = contextmod.InferenceContext()
    context.lookupname = name
    return self.infer(context, asname=False)
nodes.Import.infer_name_module = infer_name_module


@bases.path_wrapper
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
        return bases._infer_stmts(stmts, context)
    except exceptions.NotFoundError:
        raise exceptions.InferenceError(name)
nodes.ImportFrom._infer = infer_import_from


@bases.raise_if_nothing_inferred
def infer_attribute(self, context=None):
    """infer an Attribute node by using getattr on the associated object"""
    for owner in self.expr.infer(context):
        if owner is util.YES:
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
nodes.Attribute._infer = bases.path_wrapper(infer_attribute)
nodes.AssignAttr.infer_lhs = infer_attribute # # won't work with a path wrapper


@bases.path_wrapper
def infer_global(self, context=None):
    if context.lookupname is None:
        raise exceptions.InferenceError()
    try:
        return bases._infer_stmts(self.root().getattr(context.lookupname),
                                  context)
    except exceptions.NotFoundError:
        raise exceptions.InferenceError()
nodes.Global._infer = infer_global


def infer_subscript(self, context=None):
    """infer simple subscription such as [1,2,3][0] or (1,2,3)[-1]"""
    value = next(self.value.infer(context))
    if value is util.YES:
        yield util.YES
        return

    index = next(self.slice.infer(context))
    if index is util.YES:
        yield util.YES
        return

    if isinstance(index, nodes.Const):
        try:
            assigned = value.getitem(index.value, context)
        except AttributeError:
            raise exceptions.InferenceError()
        except (IndexError, TypeError):
            yield util.YES
            return

        # Prevent inferring if the inferred subscript
        # is the same as the original subscripted object.
        if self is assigned or assigned is util.YES:
            yield util.YES
            return
        for inferred in assigned.infer(context):
            yield inferred
    else:
        raise exceptions.InferenceError()
nodes.Subscript._infer = bases.path_wrapper(infer_subscript)
nodes.Subscript.infer_lhs = bases.raise_if_nothing_inferred(infer_subscript)


@bases.raise_if_nothing_inferred
@bases.path_wrapper
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
        yield util.YES
        return

    for pair in itertools.product(*values):
        if any(item is util.YES for item in pair):
            # Can't infer the final result, just yield YES.
            yield util.YES
            continue

        bool_values = [item.bool_value() for item in pair]
        if any(item is util.YES for item in bool_values):
            # Can't infer the final result, just yield YES.
            yield util.YES
            continue

        # Since the boolean operations are short circuited operations,
        # this code yields the first value for which the predicate is True
        # and if no value respected the predicate, then the last value will
        # be returned (or YES if there was no last value).
        # This is conforming to the semantics of `and` and `or`:
        #   1 and 0 -> 1
        #   0 and 1 -> 0
        #   1 or 0 -> 1
        #   0 or 1 -> 1
        value = util.YES
        for value, bool_value in zip(pair, bool_values):
            if predicate(bool_value):
                yield value
                break
        else:
            yield value

nodes.BoolOp._infer = _infer_boolop


# UnaryOp, BinOp and AugAssign inferences

def _filter_operation_errors(self, infer_callable, context, error):
    for result in infer_callable(self, context):
        if isinstance(result, error):
            # For the sake of .infer(), we don't care about operation
            # errors, which is the job of pylint. So return something
            # which shows that we can't infer the result.
            yield util.YES
        else:
            yield result


def _infer_unaryop(self, context=None):
    """Infer what an UnaryOp should return when evaluated."""
    for operand in self.operand.infer(context):
        try:
            yield operand.infer_unary_op(self.op)
        except TypeError as exc:
            # The operand doesn't support this operation.
            yield exceptions.UnaryOperationError(operand, self.op, exc)
        except AttributeError as exc:
            meth = protocols.UNARY_OP_METHOD[self.op]
            if meth is None:
                # `not node`. Determine node's boolean
                # value and negate its result, unless it is
                # YES, which will be returned as is.
                bool_value = operand.bool_value()
                if bool_value is not util.YES:
                    yield nodes.const_factory(not bool_value)
                else:
                    yield util.YES
            else:
                if not isinstance(operand, bases.Instance):
                    # The operation was used on something which
                    # doesn't support it.
                    yield exceptions.UnaryOperationError(operand, self.op, exc)
                    continue

                try:
                    meth = operand.getattr(meth, context=context)[0]
                    inferred = next(meth.infer(context=context))
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
                    yield util.YES


@bases.path_wrapper
def infer_unaryop(self, context=None):
    """Infer what an UnaryOp should return when evaluated."""
    return _filter_operation_errors(self, _infer_unaryop, context,
                                    exceptions.UnaryOperationError)

nodes.UnaryOp._infer_unaryop = _infer_unaryop
nodes.UnaryOp._infer = bases.raise_if_nothing_inferred(infer_unaryop)


def _is_not_implemented(const):
    """Check if the given const node is NotImplemented."""
    return isinstance(const, nodes.Const) and const.value is NotImplemented


def  _invoke_binop_inference(instance, op, other, context, method_name):
    """Invoke binary operation inference on the given instance."""
    method = instance.getattr(method_name)[0]
    inferred = next(method.infer(context=context))
    return instance.infer_binary_op(op, other, context, inferred)


def _aug_op(instance, op, other, context, reverse=False):
    """Get an inference callable for an augmented binary operation."""
    method_name = protocols.AUGMENTED_OP_METHOD[op]
    return functools.partial(_invoke_binop_inference,
                             instance=instance,
                             op=op, other=other,
                             context=context,
                             method_name=method_name)


def _bin_op(instance, op, other, context, reverse=False):
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
                             method_name=method_name)


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
                    context, reverse_context):
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
        methods = [_bin_op(left, op, right, context)]
    elif helpers.is_subtype(left_type, right_type):
        methods = [_bin_op(left, op, right, context)]
    elif helpers.is_supertype(left_type, right_type):
        methods = [_bin_op(right, op, left, reverse_context, reverse=True),
                   _bin_op(left, op, right, context)]
    else:
        methods = [_bin_op(left, op, right, context),
                   _bin_op(right, op, left, reverse_context, reverse=True)]
    return methods


def _get_aug_flow(left, left_type, aug_op, right, right_type,
                  context, reverse_context):
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
        methods = [_aug_op(left, aug_op, right, context),
                   _bin_op(left, op, right, context)]
    elif helpers.is_subtype(left_type, right_type):
        methods = [_aug_op(left, aug_op, right, context),
                   _bin_op(left, op, right, context)]
    elif helpers.is_supertype(left_type, right_type):
        methods = [_aug_op(left, aug_op, right, context),
                   _bin_op(right, op, left, reverse_context, reverse=True),
                   _bin_op(left, op, right, context)]
    else:
        methods = [_aug_op(left, aug_op, right, context),
                   _bin_op(left, op, right, context),
                   _bin_op(right, op, left, reverse_context, reverse=True)]
    return methods


def _infer_binary_operation(left, right, op, context, flow_factory):
    """Infer a binary operation between a left operand and a right operand

    This is used by both normal binary operations and augmented binary
    operations, the only difference is the flow factory used.
    """

    context, reverse_context = _get_binop_contexts(context, left, right)
    left_type = helpers.object_type(left)
    right_type = helpers.object_type(right)
    methods = flow_factory(left, left_type, op, right, right_type,
                           context, reverse_context)
    for method in methods:
        try:
            results = list(method())
        except AttributeError:
            continue
        except exceptions.NotFoundError:
            continue
        except exceptions.InferenceError:
            yield util.YES
            return
        else:
            if any(result is util.YES for result in results):
                yield util.YES
                return

            # TODO(cpopa): since the inferrence engine might return
            # more values than are actually possible, we decide
            # to return util.YES if we have union types.
            if all(map(_is_not_implemented, results)):
                continue
            not_implemented = sum(1 for result in results
                                  if _is_not_implemented(result))
            if not_implemented and not_implemented != len(results):
                # Can't decide yet what this is, not yet though.
                yield util.YES
                return

            for result in results:
                yield result
            return
    # TODO(cpopa): yield a BinaryOperationError here,
    # since the operation is not supported
    yield exceptions.BinaryOperationError(left_type, op, right_type)


def _infer_binop(self, context):
    """Binary operation inferrence logic."""
    if context is None:
        context = contextmod.InferenceContext()
    left = self.left
    right = self.right
    op = self.op

    for lhs in left.infer(context=context):
        if lhs is util.YES:
            # Don't know how to process this.
            yield util.YES
            return

        # TODO(cpopa): if we have A() * A(), trying to infer
        # the rhs with the same context will result in an
        # inferrence error, so we create another context for it.
        # This is a bug which should be fixed in InferenceContext at some point.
        rhs_context = context.clone()
        rhs_context.path = set()
        for rhs in right.infer(context=rhs_context):
            if rhs is util.YES:
                # Don't know how to process this.
                yield util.YES
                return

            results = _infer_binary_operation(lhs, rhs, op,
                                              context, _get_binop_flow)
            for result in results:
                yield result


@bases.path_wrapper
def infer_binop(self, context=None):
    return _filter_operation_errors(self, _infer_binop, context,
                                    exceptions.BinaryOperationError)

nodes.BinOp._infer_binop = _infer_binop
nodes.BinOp._infer = bases.yes_if_nothing_inferred(infer_binop)


def _infer_augassign(self, context=None):
    """Inferrence logic for augmented binary operations."""
    if context is None:
        context = contextmod.InferenceContext()
    op = self.op

    for lhs in self.target.infer_lhs(context=context):
        if lhs is util.YES:
            # Don't know how to process this.
            yield util.YES
            return

        # TODO(cpopa): if we have A() * A(), trying to infer
        # the rhs with the same context will result in an
        # inferrence error, so we create another context for it.
        # This is a bug which should be fixed in InferenceContext at some point.
        rhs_context = context.clone()
        rhs_context.path = set()
        for rhs in self.value.infer(context=rhs_context):
            if rhs is util.YES:
                # Don't know how to process this.
                yield util.YES
                return

            results = _infer_binary_operation(lhs, rhs, op,
                                              context, _get_aug_flow)
            for result in results:
                yield result


@bases.path_wrapper
def infer_augassign(self, context=None):
    return _filter_operation_errors(self, _infer_augassign, context,
                                    exceptions.BinaryOperationError)

nodes.AugAssign._infer_augassign = _infer_augassign
nodes.AugAssign._infer = infer_augassign

# End of binary operation inference.


def infer_arguments(self, context=None):
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError()
    return protocols._arguments_infer_argname(self, name, context)
nodes.Arguments._infer = infer_arguments


@bases.path_wrapper
def infer_assign(self, context=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmt = self.statement()
    if isinstance(stmt, nodes.AugAssign):
        return stmt.infer(context)
    stmts = list(self.assigned_stmts(context=context))
    return bases._infer_stmts(stmts, context)
nodes.AssignName._infer = infer_assign
nodes.AssignAttr._infer = infer_assign


# no infer method on DelName and DelAttr (expected InferenceError)

@bases.path_wrapper
def infer_empty_node(self, context=None):
    if not self.has_underlying_object():
        yield util.YES
    else:
        try:
            for inferred in MANAGER.infer_ast_from_something(self.object,
                                                             context=context):
                yield inferred
        except exceptions.AstroidError:
            yield util.YES
nodes.EmptyNode._infer = infer_empty_node


def infer_index(self, context=None):
    return self.value.infer(context)
nodes.Index._infer = infer_index

# TODO: move directly into bases.Instance when the dependency hell
# will be solved.
def instance_getitem(self, index, context=None):
    # Rewrap index to Const for this case
    index = nodes.Const(index)

    if context:
        new_context = context.clone()
    else:
        context = new_context = contextmod.InferenceContext()

    # Create a new callcontext for providing index as an argument.
    new_context.callcontext = contextmod.CallContext(args=[index])
    new_context.boundnode = self

    method = next(self.igetattr('__getitem__', context=context))
    if not isinstance(method, bases.BoundMethod):
        raise exceptions.InferenceError

    try:
        return next(method.infer_call_result(self, new_context))
    except StopIteration:
        raise exceptions.InferenceError

bases.Instance.getitem = instance_getitem
