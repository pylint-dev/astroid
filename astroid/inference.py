# Copyright (c) 2006-2011, 2013-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2013-2014 Google, Inc.
# Copyright (c) 2014-2016 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015-2016 Cara Vinson <ceridwenv@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""this module contains a set of functions to handle inference on astroid trees
"""

# pylint: disable=no-value-for-parameter; Pylint FP #629, please remove afterwards.

import functools
import itertools
import operator

from astroid import context as contextmod
from astroid import decorators
from astroid import exceptions
from astroid.interpreter import runtimeabc
from astroid.interpreter import util as inferenceutil
from astroid import protocols
from astroid.tree import treeabc
from astroid import util

manager = util.lazy_import('manager')
MANAGER = manager.AstroidManager()


@util.singledispatch
def infer(self, context=None):
    raise exceptions.InferenceError('No inference function for {node!r}', node=self, context=context)


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
            raise exceptions.NameInferenceError(name=self.name,
                                                scope=self.scope(),
                                                context=context)
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
    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, context=context))


@infer.register(treeabc.Import)
@decorators.path_wrapper
def infer_import(self, context=None, asname=True):
    """infer an Import node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError(node=self, context=context)
    try:
        if asname:
            real_name = inferenceutil.real_name(self, name)
            yield inferenceutil.do_import_module(self, real_name)
        else:
            yield inferenceutil.do_import_module(self, name)
    except exceptions.AstroidBuildingError as exc:
        util.reraise(exceptions.InferenceError(node=self, error=exc,
                                               context=context))        


@infer.register(treeabc.ImportFrom)
@decorators.path_wrapper
def infer_import_from(self, context=None, asname=True):
    """infer a ImportFrom node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError(node=self, context=context)
    if asname:
        name = inferenceutil.real_name(self, name)
    try:
        module = inferenceutil.do_import_module(self, self.modname)
    except exceptions.AstroidBuildingError as exc:
        util.reraise(exceptions.InferenceError(node=self, error=exc,
                                               context=context))

    try:
        context = contextmod.copy_context(context)
        context.lookupname = name
        stmts = module.getattr(name, ignore_locals=module is self.root())
        return inferenceutil.infer_stmts(stmts, context)
    except exceptions.AttributeInferenceError as error:
        structured = exceptions.InferenceError(error.message, target=self,
                                               attribute=name, context=context)
        util.reraise(structured)


@decorators.raise_if_nothing_inferred
def infer_attribute(self, context=None):
    """infer an Attribute node by using getattr on the associated object"""
    for owner in self.expr.infer(context):
        if owner is util.Uninferable:
            yield owner
            continue

        if context and context.boundnode:
            # This handles the situation where the attribute is accessed through a subclass
            # of a base class and the attribute is defined at the base class's level,
            # by taking in consideration a redefinition in the subclass.
            if (isinstance(owner, runtimeabc.Instance)
                  and isinstance(context.boundnode, runtimeabc.Instance)):
                try:
                    if inferenceutil.is_subtype(inferenceutil.object_type(context.boundnode),
                                                inferenceutil.object_type(owner)):
                        owner = context.boundnode
                except exceptions._NonDeducibleTypeHierarchy:
                    # Can't determine anything useful.
                    pass


        try:
            context.boundnode = owner
            for obj in owner.igetattr(self.attrname, context):
                yield obj
            context.boundnode = None
        except (exceptions.AttributeInferenceError, exceptions.InferenceError):
            context.boundnode = None
    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, context=context))

infer.register(treeabc.Attribute, decorators.path_wrapper(infer_attribute))


@infer.register(treeabc.Global)
@decorators.path_wrapper
def infer_global(self, context=None):
    if context.lookupname is None:
        raise exceptions.InferenceError(node=self, context=context)

    try:
        stmts = self.root().getattr(context.lookupname)
        return inferenceutil.infer_stmts(stmts, context)
    except exceptions.AttributeInferenceError as error:
        structured = exceptions.InferenceError(error.message, target=self,
                                               attribute=context.lookupname,
                                               context=context)
        util.reraise(structured)


_SUBSCRIPT_SENTINEL = object()


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

    if not hasattr(value, 'getitem'):
        # TODO: we could have a Sequence protocol class or something similar.
        raise exceptions.InferenceError(node=self, context=context)

    index = next(self.slice.infer(context))
    if index is util.Uninferable:
        yield util.Uninferable
        return

    index_value = _SUBSCRIPT_SENTINEL
    if isinstance(value, runtimeabc.Instance):
        index_value = index
    else:
        if isinstance(index, runtimeabc.Instance):
            instance_as_index = inferenceutil.class_instance_as_index(index)
            if instance_as_index:
                index_value = instance_as_index
        else:
            index_value = index
    if index_value is _SUBSCRIPT_SENTINEL:
        raise exceptions.InferenceError(node=self, context=context)

    try:
        assigned = value.getitem(index_value, context)
    except (IndexError, TypeError) as exc:
        util.reraise(exceptions.InferenceError(node=self, error=exc,
                                               context=context))

    # Prevent inferring if the inferred subscript
    # is the same as the original subscripted object.
    if self is assigned or assigned is util.Uninferable:
        yield util.Uninferable
        return
    for inferred in assigned.infer(context):
        yield inferred

    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, context=context))

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

    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, context=context))


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
            yield util.BadUnaryOperationMessage(operand, self.op, exc)
        except exceptions.UnaryOperationNotSupportedError as exc:
            meth = protocols.UNARY_OP_METHOD[self.op]
            if meth is None:
                # `not node`. Determine node's boolean
                # value and negate its result, unless it is
                # Uninferable, which will be returned as is.
                bool_value = operand.bool_value()
                if bool_value is not util.Uninferable:
                    yield nodes.Const(not bool_value)
                else:
                    yield util.Uninferable
            else:
                if not isinstance(operand, runtimeabc.Instance):
                    # The operation was used on something which
                    # doesn't support it.
                    yield util.BadUnaryOperationMessage(operand, self.op, exc)
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
                except exceptions.AttributeInferenceError as exc:
                    # The unary operation special method was not found.
                    yield util.BadUnaryOperationMessage(operand, self.op, exc)
                except exceptions.InferenceError:
                    yield util.Uninferable


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def filtered_infer_unaryop(self, context=None, nodes=None):
    """Infer what an UnaryOp should return when evaluated."""
    with_nodes_func = functools.partial(infer_unaryop, nodes=nodes)
    for inferred in _filter_operation_errors(self, with_nodes_func, context,
                                             util.BadUnaryOperationMessage):
        yield inferred

    # Explicit StopIteration to return error information, see comment
    # in raise_if_nothing_inferred.
    raise StopIteration(dict(node=self, context=context))


def _is_not_implemented(const):
    """Check if the given const node is NotImplemented."""
    return isinstance(const, treeabc.Const) and const.value is NotImplemented


def  _invoke_binop_inference(instance, opnode, op, other, context, method_name, nodes):
    """Invoke binary operation inference on the given instance."""
    if not hasattr(instance, 'getattr'):
        # The operation is undefined for the given node. We can stop
        # the inference at this point.
        raise exceptions.BinaryOperationNotSupportedError

    method = instance.getattr(method_name)[0]
    inferred = next(method.infer(context=context))
    return protocols.infer_binary_op(instance, opnode, op, other, context, inferred, nodes)


def _aug_op(instance, opnode, op, other, context, nodes, reverse=False):
    """Get an inference callable for an augmented binary operation."""
    method_name = protocols.AUGMENTED_OP_METHOD[op]
    return functools.partial(_invoke_binop_inference,
                             instance=instance,
                             op=op, opnode=opnode, other=other,
                             context=context,
                             method_name=method_name,
                             nodes=nodes)


def _bin_op(instance, opnode, op, other, context, nodes, reverse=False):
    """Get an inference callable for a normal binary operation.

    If *reverse* is True, then the reflected method will be used instead.
    """
    if reverse:
        method_name = protocols.REFLECTED_BIN_OP_METHOD[op]
    else:
        method_name = protocols.BIN_OP_METHOD[op]
    return functools.partial(_invoke_binop_inference,
                             instance=instance,
                             op=op, opnode=opnode, other=other,
                             context=context,
                             method_name=method_name,
                             nodes=nodes)


def _same_type(type1, type2):
    """Check if type1 is the same as type2."""
    return type1.qname() == type2.qname()


def _get_binop_flow(left, left_type, binary_opnode, right, right_type,
                    context, nodes):
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
    op = binary_opnode.op
    if _same_type(left_type, right_type):
        methods = [_bin_op(left, binary_opnode, op, right, context, nodes)]
    elif inferenceutil.is_subtype(left_type, right_type):
        methods = [_bin_op(left, binary_opnode, op, right, context, nodes)]
    elif inferenceutil.is_supertype(left_type, right_type):
        methods = [_bin_op(right, binary_opnode, op, left, context, nodes, reverse=True),
                   _bin_op(left, binary_opnode, op, right, context, nodes)]
    else:
        methods = [_bin_op(left, binary_opnode, op, right, context, nodes),
                   _bin_op(right, binary_opnode, op, left, context, nodes, reverse=True)]
    return methods


def _get_aug_flow(left, left_type, aug_opnode, right, right_type,
                  context, nodes):
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
    bin_op = aug_opnode.op.strip("=")
    aug_op = aug_opnode.op
    if _same_type(left_type, right_type):
        methods = [_aug_op(left, aug_opnode, aug_op, right, context, nodes),
                   _bin_op(left, aug_opnode, bin_op, right, context, nodes)]
    elif inferenceutil.is_subtype(left_type, right_type):
        methods = [_aug_op(left, aug_opnode, aug_op, right, context, nodes),
                   _bin_op(left, aug_opnode, bin_op, right, context, nodes)]
    elif inferenceutil.is_supertype(left_type, right_type):
        methods = [_aug_op(left, aug_opnode, aug_op, right, context, nodes),
                   _bin_op(right, aug_opnode, bin_op, left, context, nodes, reverse=True),
                   _bin_op(left, aug_opnode, bin_op, right, context, nodes)]
    else:
        methods = [_aug_op(left, aug_opnode, aug_op, right, context, nodes),
                   _bin_op(left, aug_opnode, bin_op, right, context, nodes),
                   _bin_op(right, aug_opnode, bin_op, left, context, nodes, reverse=True)]
    return methods


def _infer_binary_operation(left, right, binary_opnode, context, flow_factory, nodes):
    """Infer a binary operation between a left operand and a right operand

    This is used by both normal binary operations and augmented binary
    operations, the only difference is the flow factory used.
    """
    left_type = inferenceutil.object_type(left)
    right_type = inferenceutil.object_type(right)
    methods = flow_factory(left, left_type, binary_opnode, right, right_type,
                           context, nodes)
    for method in methods:
        try:
            results = list(method())
        except exceptions.BinaryOperationNotSupportedError:
            continue
        except exceptions.AttributeInferenceError:
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
    # TODO(cpopa): yield a BadBinaryOperationMessage here,
    # since the operation is not supported
    yield util.BadBinaryOperationMessage(left_type, binary_opnode.op, right_type)


def infer_binop(self, context, nodes):
    """Binary operation inferrence logic."""
    if context is None:
        context = contextmod.InferenceContext()
    left = self.left
    right = self.right

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

            try:
                results = _infer_binary_operation(lhs, rhs, self, context,
                                                  _get_binop_flow, nodes)
            except exceptions._NonDeducibleTypeHierarchy:
                yield util.Uninferable
            else:
                for result in results:
                    yield result


@decorators.yes_if_nothing_inferred
@decorators.path_wrapper
def filtered_infer_binop(self, context=None, nodes=None):
    with_nodes_func = functools.partial(infer_binop, nodes=nodes)
    return _filter_operation_errors(self, with_nodes_func, context,
                                    util.BadBinaryOperationMessage)


def infer_augassign(self, context=None, nodes=None):
    """Inferrence logic for augmented binary operations."""
    if context is None:
        context = contextmod.InferenceContext()

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

            try:
                results = _infer_binary_operation(lhs, rhs, self,
                                                  context, _get_aug_flow, nodes)
            except exceptions._NonDeducibleTypeHierarchy:
                yield util.Uninferable
            else:
                for result in results:
                    yield result


@decorators.path_wrapper
def filtered_infer_augassign(self, context=None, nodes=None):
    with_nodes_func = functools.partial(infer_augassign, nodes=nodes)
    return _filter_operation_errors(self, with_nodes_func, context,
                                    util.BadBinaryOperationMessage)


# End of binary operation inference.


def infer_arguments(self, context=None, nodes=None):
    name = context.lookupname
    if name is None:
        raise exceptions.InferenceError(node=self, context=context)
    return protocols._arguments_infer_argname(self, name, context, nodes)


@infer.register(treeabc.AssignName)
@infer.register(treeabc.AssignAttr)
@infer.register(treeabc.Parameter)
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

@infer.register(treeabc.InterpreterObject)
@decorators.path_wrapper
def infer_interpreter_object(self, context=None):
    if not self.has_underlying_object():
        yield util.Uninferable
    else:
        try:
            for inferred in self.object.infer(context=context):
                yield inferred
        except exceptions.AstroidError:
            yield util.Uninferable


@infer.register(treeabc.Index)
def infer_index(self, context=None):
    return self.value.infer(context)
