# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""this module contains a set of functions to handle inference on astroid trees
"""

from __future__ import annotations

import ast
import functools
import itertools
import operator
from collections.abc import Callable, Generator, Iterable, Iterator
from typing import TYPE_CHECKING, Any, TypeVar

from astroid import bases, decorators, helpers, nodes, protocols, util
from astroid.context import (
    CallContext,
    InferenceContext,
    bind_context_to_node,
    copy_context,
)
from astroid.exceptions import (
    AstroidBuildingError,
    AstroidError,
    AstroidIndexError,
    AstroidTypeError,
    AttributeInferenceError,
    InferenceError,
    NameInferenceError,
    _NonDeducibleTypeHierarchy,
)
from astroid.interpreter import dunder_lookup
from astroid.manager import AstroidManager
from astroid.typing import InferenceErrorInfo

if TYPE_CHECKING:
    from astroid.objects import Property

# Prevents circular imports
objects = util.lazy_import("objects")


_FunctionDefT = TypeVar("_FunctionDefT", bound=nodes.FunctionDef)


# .infer method ###############################################################


_T = TypeVar("_T")
_BaseContainerT = TypeVar("_BaseContainerT", bound=nodes.BaseContainer)


def infer_end(
    self: _T, context: InferenceContext | None = None, **kwargs: Any
) -> Iterator[_T]:
    """Inference's end for nodes that yield themselves on inference

    These are objects for which inference does not have any semantic,
    such as Module or Consts.
    """
    yield self


nodes.Module._infer = infer_end
nodes.ClassDef._infer = infer_end
nodes.Lambda._infer = infer_end
nodes.Const._infer = infer_end
nodes.Slice._infer = infer_end


def _infer_sequence_helper(node, context=None):
    """Infer all values based on _BaseContainer.elts"""
    values = []

    for elt in node.elts:
        if isinstance(elt, nodes.Starred):
            starred = helpers.safe_infer(elt.value, context)
            if not starred:
                raise InferenceError(node=node, context=context)
            if not hasattr(starred, "elts"):
                raise InferenceError(node=node, context=context)
            values.extend(_infer_sequence_helper(starred))
        elif isinstance(elt, nodes.NamedExpr):
            value = helpers.safe_infer(elt.value, context)
            if not value:
                raise InferenceError(node=node, context=context)
            values.append(value)
        else:
            values.append(elt)
    return values


@decorators.raise_if_nothing_inferred
def infer_sequence(
    self: _BaseContainerT,
    context: InferenceContext | None = None,
    **kwargs: Any,
) -> Iterator[_BaseContainerT]:
    has_starred_named_expr = any(
        isinstance(e, (nodes.Starred, nodes.NamedExpr)) for e in self.elts
    )
    if has_starred_named_expr:
        values = _infer_sequence_helper(self, context)
        new_seq = type(self)(
            lineno=self.lineno, col_offset=self.col_offset, parent=self.parent
        )
        new_seq.postinit(values)

        yield new_seq
    else:
        yield self


nodes.List._infer = infer_sequence
nodes.Tuple._infer = infer_sequence
nodes.Set._infer = infer_sequence


def infer_map(self, context=None):
    if not any(isinstance(k, nodes.DictUnpack) for k, _ in self.items):
        yield self
    else:
        items = _infer_map(self, context)
        new_seq = type(self)(self.lineno, self.col_offset, self.parent)
        new_seq.postinit(list(items.items()))
        yield new_seq


def _update_with_replacement(lhs_dict, rhs_dict):
    """Delete nodes that equate to duplicate keys

    Since an astroid node doesn't 'equal' another node with the same value,
    this function uses the as_string method to make sure duplicate keys
    don't get through

    Note that both the key and the value are astroid nodes

    Fixes issue with DictUnpack causing duplicte keys
    in inferred Dict items

    :param dict(nodes.NodeNG, nodes.NodeNG) lhs_dict: Dictionary to 'merge' nodes into
    :param dict(nodes.NodeNG, nodes.NodeNG) rhs_dict: Dictionary with nodes to pull from
    :return dict(nodes.NodeNG, nodes.NodeNG): merged dictionary of nodes
    """
    combined_dict = itertools.chain(lhs_dict.items(), rhs_dict.items())
    # Overwrite keys which have the same string values
    string_map = {key.as_string(): (key, value) for key, value in combined_dict}
    # Return to dictionary
    return dict(string_map.values())


def _infer_map(node, context):
    """Infer all values based on Dict.items"""
    values = {}
    for name, value in node.items:
        if isinstance(name, nodes.DictUnpack):
            double_starred = helpers.safe_infer(value, context)
            if not double_starred:
                raise InferenceError
            if not isinstance(double_starred, nodes.Dict):
                raise InferenceError(node=node, context=context)
            unpack_items = _infer_map(double_starred, context)
            values = _update_with_replacement(values, unpack_items)
        else:
            key = helpers.safe_infer(name, context=context)
            value = helpers.safe_infer(value, context=context)
            if any(not elem for elem in (key, value)):
                raise InferenceError(node=node, context=context)
            values = _update_with_replacement(values, {key: value})
    return values


nodes.Dict._infer = infer_map  # type: ignore[assignment]


def _higher_function_scope(node):
    """Search for the first function which encloses the given
    scope. This can be used for looking up in that function's
    scope, in case looking up in a lower scope for a particular
    name fails.

    :param node: A scope node.
    :returns:
        ``None``, if no parent function scope was found,
        otherwise an instance of :class:`astroid.nodes.scoped_nodes.Function`,
        which encloses the given node.
    """
    current = node
    while current.parent and not isinstance(current.parent, nodes.FunctionDef):
        current = current.parent
    if current and current.parent:
        return current.parent
    return None


def infer_name(self, context=None):
    """infer a Name: use name lookup rules"""
    frame, stmts = self.lookup(self.name)
    if not stmts:
        # Try to see if the name is enclosed in a nested function
        # and use the higher (first function) scope for searching.
        parent_function = _higher_function_scope(self.scope())
        if parent_function:
            _, stmts = parent_function.lookup(self.name)

        if not stmts:
            raise NameInferenceError(
                name=self.name, scope=self.scope(), context=context
            )
    context = copy_context(context)
    context.lookupname = self.name
    return bases._infer_stmts(stmts, context, frame)


# pylint: disable=no-value-for-parameter
nodes.Name._infer = decorators.raise_if_nothing_inferred(
    decorators.path_wrapper(infer_name)
)
nodes.AssignName.infer_lhs = infer_name  # won't work with a path wrapper


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_call(self, context=None):
    """infer a Call node by trying to guess what the function returns"""
    callcontext = copy_context(context)
    callcontext.boundnode = None
    if context is not None:
        callcontext.extra_context = _populate_context_lookup(self, context.clone())

    for callee in self.func.infer(context):
        if callee is util.Uninferable:
            yield callee
            continue
        try:
            if hasattr(callee, "infer_call_result"):
                callcontext.callcontext = CallContext(
                    args=self.args, keywords=self.keywords, callee=callee
                )
                yield from callee.infer_call_result(caller=self, context=callcontext)
        except InferenceError:
            continue
    return dict(node=self, context=context)


nodes.Call._infer = infer_call  # type: ignore[assignment]


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_import(self, context=None, asname=True):
    """infer an Import node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise InferenceError(node=self, context=context)

    try:
        if asname:
            yield self.do_import_module(self.real_name(name))
        else:
            yield self.do_import_module(name)
    except AstroidBuildingError as exc:
        raise InferenceError(node=self, context=context) from exc


nodes.Import._infer = infer_import


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_import_from(self, context=None, asname=True):
    """infer a ImportFrom node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise InferenceError(node=self, context=context)
    if asname:
        try:
            name = self.real_name(name)
        except AttributeInferenceError as exc:
            # See https://github.com/PyCQA/pylint/issues/4692
            raise InferenceError(node=self, context=context) from exc
    try:
        module = self.do_import_module()
    except AstroidBuildingError as exc:
        raise InferenceError(node=self, context=context) from exc

    try:
        context = copy_context(context)
        context.lookupname = name
        stmts = module.getattr(name, ignore_locals=module is self.root())
        return bases._infer_stmts(stmts, context)
    except AttributeInferenceError as error:
        raise InferenceError(
            str(error), target=self, attribute=name, context=context
        ) from error


nodes.ImportFrom._infer = infer_import_from  # type: ignore[assignment]


def infer_attribute(self, context=None):
    """infer an Attribute node by using getattr on the associated object"""
    for owner in self.expr.infer(context):
        if owner is util.Uninferable:
            yield owner
            continue

        if not context:
            context = InferenceContext()
        else:
            context = copy_context(context)

        old_boundnode = context.boundnode
        try:
            context.boundnode = owner
            yield from owner.igetattr(self.attrname, context)
        except (
            AttributeInferenceError,
            InferenceError,
            AttributeError,
        ):
            pass
        finally:
            context.boundnode = old_boundnode
    return dict(node=self, context=context)


nodes.Attribute._infer = decorators.raise_if_nothing_inferred(
    decorators.path_wrapper(infer_attribute)
)
# won't work with a path wrapper
nodes.AssignAttr.infer_lhs = decorators.raise_if_nothing_inferred(infer_attribute)


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_global(self, context=None):
    if context.lookupname is None:
        raise InferenceError(node=self, context=context)
    try:
        return bases._infer_stmts(self.root().getattr(context.lookupname), context)
    except AttributeInferenceError as error:
        raise InferenceError(
            str(error), target=self, attribute=context.lookupname, context=context
        ) from error


nodes.Global._infer = infer_global  # type: ignore[assignment]


_SUBSCRIPT_SENTINEL = object()


def infer_subscript(self, context=None):
    """Inference for subscripts

    We're understanding if the index is a Const
    or a slice, passing the result of inference
    to the value's `getitem` method, which should
    handle each supported index type accordingly.
    """

    found_one = False
    for value in self.value.infer(context):
        if value is util.Uninferable:
            yield util.Uninferable
            return None
        for index in self.slice.infer(context):
            if index is util.Uninferable:
                yield util.Uninferable
                return None

            # Try to deduce the index value.
            index_value = _SUBSCRIPT_SENTINEL
            if value.__class__ == bases.Instance:
                index_value = index
            elif index.__class__ == bases.Instance:
                instance_as_index = helpers.class_instance_as_index(index)
                if instance_as_index:
                    index_value = instance_as_index
            else:
                index_value = index

            if index_value is _SUBSCRIPT_SENTINEL:
                raise InferenceError(node=self, context=context)

            try:
                assigned = value.getitem(index_value, context)
            except (
                AstroidTypeError,
                AstroidIndexError,
                AttributeInferenceError,
                AttributeError,
            ) as exc:
                raise InferenceError(node=self, context=context) from exc

            # Prevent inferring if the inferred subscript
            # is the same as the original subscripted object.
            if self is assigned or assigned is util.Uninferable:
                yield util.Uninferable
                return None
            yield from assigned.infer(context)
            found_one = True

    if found_one:
        return dict(node=self, context=context)
    return None


nodes.Subscript._infer = decorators.raise_if_nothing_inferred(  # type: ignore[assignment]
    decorators.path_wrapper(infer_subscript)
)
nodes.Subscript.infer_lhs = decorators.raise_if_nothing_inferred(infer_subscript)


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def _infer_boolop(self, context=None):
    """Infer a boolean operation (and / or / not).

    The function will calculate the boolean operation
    for all pairs generated through inference for each component
    node.
    """
    values = self.values
    if self.op == "or":
        predicate = operator.truth
    else:
        predicate = operator.not_

    try:
        values = [value.infer(context=context) for value in values]
    except InferenceError:
        yield util.Uninferable
        return None

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

    return dict(node=self, context=context)


nodes.BoolOp._infer = _infer_boolop


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


def _infer_unaryop(self, context=None):
    """Infer what an UnaryOp should return when evaluated."""
    for operand in self.operand.infer(context):
        try:
            yield operand.infer_unary_op(self.op)
        except TypeError as exc:
            # The operand doesn't support this operation.
            yield util.BadUnaryOperationMessage(operand, self.op, exc)
        except AttributeError as exc:
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
                if not isinstance(operand, (bases.Instance, nodes.ClassDef)):
                    # The operation was used on something which
                    # doesn't support it.
                    yield util.BadUnaryOperationMessage(operand, self.op, exc)
                    continue

                try:
                    try:
                        methods = dunder_lookup.lookup(operand, meth)
                    except AttributeInferenceError:
                        yield util.BadUnaryOperationMessage(operand, self.op, exc)
                        continue

                    meth = methods[0]
                    inferred = next(meth.infer(context=context), None)
                    if inferred is util.Uninferable or not inferred.callable():
                        continue

                    context = copy_context(context)
                    context.boundnode = operand
                    context.callcontext = CallContext(args=[], callee=inferred)

                    call_results = inferred.infer_call_result(self, context=context)
                    result = next(call_results, None)
                    if result is None:
                        # Failed to infer, return the same type.
                        yield operand
                    else:
                        yield result
                except AttributeInferenceError as inner_exc:
                    # The unary operation special method was not found.
                    yield util.BadUnaryOperationMessage(operand, self.op, inner_exc)
                except InferenceError:
                    yield util.Uninferable


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_unaryop(self, context=None):
    """Infer what an UnaryOp should return when evaluated."""
    yield from _filter_operation_errors(
        self, _infer_unaryop, context, util.BadUnaryOperationMessage
    )
    return dict(node=self, context=context)


nodes.UnaryOp._infer_unaryop = _infer_unaryop
nodes.UnaryOp._infer = infer_unaryop


def _is_not_implemented(const):
    """Check if the given const node is NotImplemented."""
    return isinstance(const, nodes.Const) and const.value is NotImplemented


def _invoke_binop_inference(instance, opnode, op, other, context, method_name):
    """Invoke binary operation inference on the given instance."""
    methods = dunder_lookup.lookup(instance, method_name)
    context = bind_context_to_node(context, instance)
    method = methods[0]
    context.callcontext.callee = method
    try:
        inferred = next(method.infer(context=context))
    except StopIteration as e:
        raise InferenceError(node=method, context=context) from e
    if inferred is util.Uninferable:
        raise InferenceError
    return instance.infer_binary_op(opnode, op, other, context, inferred)


def _aug_op(instance, opnode, op, other, context, reverse=False):
    """Get an inference callable for an augmented binary operation."""
    method_name = protocols.AUGMENTED_OP_METHOD[op]
    return functools.partial(
        _invoke_binop_inference,
        instance=instance,
        op=op,
        opnode=opnode,
        other=other,
        context=context,
        method_name=method_name,
    )


def _bin_op(instance, opnode, op, other, context, reverse=False):
    """Get an inference callable for a normal binary operation.

    If *reverse* is True, then the reflected method will be used instead.
    """
    if reverse:
        method_name = protocols.REFLECTED_BIN_OP_METHOD[op]
    else:
        method_name = protocols.BIN_OP_METHOD[op]
    return functools.partial(
        _invoke_binop_inference,
        instance=instance,
        op=op,
        opnode=opnode,
        other=other,
        context=context,
        method_name=method_name,
    )


def _get_binop_contexts(context, left, right):
    """Get contexts for binary operations.

    This will return two inference contexts, the first one
    for x.__op__(y), the other one for y.__rop__(x), where
    only the arguments are inversed.
    """
    # The order is important, since the first one should be
    # left.__op__(right).
    for arg in (right, left):
        new_context = context.clone()
        new_context.callcontext = CallContext(args=[arg])
        new_context.boundnode = None
        yield new_context


def _same_type(type1, type2):
    """Check if type1 is the same as type2."""
    return type1.qname() == type2.qname()


def _get_binop_flow(
    left, left_type, binary_opnode, right, right_type, context, reverse_context
):
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
        methods = [_bin_op(left, binary_opnode, op, right, context)]
    elif helpers.is_subtype(left_type, right_type):
        methods = [_bin_op(left, binary_opnode, op, right, context)]
    elif helpers.is_supertype(left_type, right_type):
        methods = [
            _bin_op(right, binary_opnode, op, left, reverse_context, reverse=True),
            _bin_op(left, binary_opnode, op, right, context),
        ]
    else:
        methods = [
            _bin_op(left, binary_opnode, op, right, context),
            _bin_op(right, binary_opnode, op, left, reverse_context, reverse=True),
        ]
    return methods


def _get_aug_flow(
    left, left_type, aug_opnode, right, right_type, context, reverse_context
):
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
        methods = [
            _aug_op(left, aug_opnode, aug_op, right, context),
            _bin_op(left, aug_opnode, bin_op, right, context),
        ]
    elif helpers.is_subtype(left_type, right_type):
        methods = [
            _aug_op(left, aug_opnode, aug_op, right, context),
            _bin_op(left, aug_opnode, bin_op, right, context),
        ]
    elif helpers.is_supertype(left_type, right_type):
        methods = [
            _aug_op(left, aug_opnode, aug_op, right, context),
            _bin_op(right, aug_opnode, bin_op, left, reverse_context, reverse=True),
            _bin_op(left, aug_opnode, bin_op, right, context),
        ]
    else:
        methods = [
            _aug_op(left, aug_opnode, aug_op, right, context),
            _bin_op(left, aug_opnode, bin_op, right, context),
            _bin_op(right, aug_opnode, bin_op, left, reverse_context, reverse=True),
        ]
    return methods


def _infer_binary_operation(left, right, binary_opnode, context, flow_factory):
    """Infer a binary operation between a left operand and a right operand

    This is used by both normal binary operations and augmented binary
    operations, the only difference is the flow factory used.
    """

    context, reverse_context = _get_binop_contexts(context, left, right)
    left_type = helpers.object_type(left)
    right_type = helpers.object_type(right)
    methods = flow_factory(
        left, left_type, binary_opnode, right, right_type, context, reverse_context
    )
    for method in methods:
        try:
            results = list(method())
        except AttributeError:
            continue
        except AttributeInferenceError:
            continue
        except InferenceError:
            yield util.Uninferable
            return
        else:
            if any(result is util.Uninferable for result in results):
                yield util.Uninferable
                return

            if all(map(_is_not_implemented, results)):
                continue
            not_implemented = sum(
                1 for result in results if _is_not_implemented(result)
            )
            if not_implemented and not_implemented != len(results):
                # Can't infer yet what this is.
                yield util.Uninferable
                return

            yield from results
            return
    # The operation doesn't seem to be supported so let the caller know about it
    yield util.BadBinaryOperationMessage(left_type, binary_opnode.op, right_type)


def _infer_binop(self, context):
    """Binary operation inference logic."""
    left = self.left
    right = self.right

    # we use two separate contexts for evaluating lhs and rhs because
    # 1. evaluating lhs may leave some undesired entries in context.path
    #    which may not let us infer right value of rhs
    context = context or InferenceContext()
    lhs_context = copy_context(context)
    rhs_context = copy_context(context)
    lhs_iter = left.infer(context=lhs_context)
    rhs_iter = right.infer(context=rhs_context)
    for lhs, rhs in itertools.product(lhs_iter, rhs_iter):
        if any(value is util.Uninferable for value in (rhs, lhs)):
            # Don't know how to process this.
            yield util.Uninferable
            return

        try:
            yield from _infer_binary_operation(lhs, rhs, self, context, _get_binop_flow)
        except _NonDeducibleTypeHierarchy:
            yield util.Uninferable


@decorators.yes_if_nothing_inferred
@decorators.path_wrapper
def infer_binop(self, context=None):
    return _filter_operation_errors(
        self, _infer_binop, context, util.BadBinaryOperationMessage
    )


nodes.BinOp._infer_binop = _infer_binop
nodes.BinOp._infer = infer_binop

COMPARE_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "in": lambda a, b: a in b,
    "not in": lambda a, b: a not in b,
}
UNINFERABLE_OPS = {
    "is",
    "is not",
}


def _to_literal(node: nodes.NodeNG) -> Any:
    # Can raise SyntaxError or ValueError from ast.literal_eval
    # Can raise AttributeError from node.as_string() as not all nodes have a visitor
    # Is this the stupidest idea or the simplest idea?
    return ast.literal_eval(node.as_string())


def _do_compare(
    left_iter: Iterable[nodes.NodeNG], op: str, right_iter: Iterable[nodes.NodeNG]
) -> bool | type[util.Uninferable]:
    """
    If all possible combinations are either True or False, return that:
    >>> _do_compare([1, 2], '<=', [3, 4])
    True
    >>> _do_compare([1, 2], '==', [3, 4])
    False

    If any item is uninferable, or if some combinations are True and some
    are False, return Uninferable:
    >>> _do_compare([1, 3], '<=', [2, 4])
    util.Uninferable
    """
    retval: bool | None = None
    if op in UNINFERABLE_OPS:
        return util.Uninferable
    op_func = COMPARE_OPS[op]

    for left, right in itertools.product(left_iter, right_iter):
        if left is util.Uninferable or right is util.Uninferable:
            return util.Uninferable

        try:
            left, right = _to_literal(left), _to_literal(right)
        except (SyntaxError, ValueError, AttributeError):
            return util.Uninferable

        try:
            expr = op_func(left, right)
        except TypeError as exc:
            raise AstroidTypeError from exc

        if retval is None:
            retval = expr
        elif retval != expr:
            return util.Uninferable
            # (or both, but "True | False" is basically the same)

    assert retval is not None
    return retval  # it was all the same value


def _infer_compare(
    self: nodes.Compare, context: InferenceContext | None = None
) -> Iterator[nodes.Const | type[util.Uninferable]]:
    """Chained comparison inference logic."""
    retval: bool | type[util.Uninferable] = True

    ops = self.ops
    left_node = self.left
    lhs = list(left_node.infer(context=context))
    # should we break early if first element is uninferable?
    for op, right_node in ops:
        # eagerly evaluate rhs so that values can be re-used as lhs
        rhs = list(right_node.infer(context=context))
        try:
            retval = _do_compare(lhs, op, rhs)
        except AstroidTypeError:
            retval = util.Uninferable
            break
        if retval is not True:
            break  # short-circuit
        lhs = rhs  # continue
    if retval is util.Uninferable:
        yield retval  # type: ignore[misc]
    else:
        yield nodes.Const(retval)


nodes.Compare._infer = _infer_compare  # type: ignore[assignment]


def _infer_augassign(self, context=None):
    """Inference logic for augmented binary operations."""
    if context is None:
        context = InferenceContext()

    rhs_context = context.clone()

    lhs_iter = self.target.infer_lhs(context=context)
    rhs_iter = self.value.infer(context=rhs_context)
    for lhs, rhs in itertools.product(lhs_iter, rhs_iter):
        if any(value is util.Uninferable for value in (rhs, lhs)):
            # Don't know how to process this.
            yield util.Uninferable
            return

        try:
            yield from _infer_binary_operation(
                left=lhs,
                right=rhs,
                binary_opnode=self,
                context=context,
                flow_factory=_get_aug_flow,
            )
        except _NonDeducibleTypeHierarchy:
            yield util.Uninferable


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_augassign(self, context=None):
    return _filter_operation_errors(
        self, _infer_augassign, context, util.BadBinaryOperationMessage
    )


nodes.AugAssign._infer_augassign = _infer_augassign
nodes.AugAssign._infer = infer_augassign

# End of binary operation inference.


@decorators.raise_if_nothing_inferred
def infer_arguments(self, context=None):
    name = context.lookupname
    if name is None:
        raise InferenceError(node=self, context=context)
    return protocols._arguments_infer_argname(self, name, context)


nodes.Arguments._infer = infer_arguments  # type: ignore[assignment]


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_assign(self, context=None):
    """infer a AssignName/AssignAttr: need to inspect the RHS part of the
    assign node
    """
    if isinstance(self.parent, nodes.AugAssign):
        return self.parent.infer(context)

    stmts = list(self.assigned_stmts(context=context))
    return bases._infer_stmts(stmts, context)


nodes.AssignName._infer = infer_assign
nodes.AssignAttr._infer = infer_assign


@decorators.raise_if_nothing_inferred
@decorators.path_wrapper
def infer_empty_node(self, context=None):
    if not self.has_underlying_object():
        yield util.Uninferable
    else:
        try:
            yield from AstroidManager().infer_ast_from_something(
                self.object, context=context
            )
        except AstroidError:
            yield util.Uninferable


nodes.EmptyNode._infer = infer_empty_node  # type: ignore[assignment]


@decorators.raise_if_nothing_inferred
def infer_index(self, context=None):
    return self.value.infer(context)


nodes.Index._infer = infer_index  # type: ignore[assignment]


def _populate_context_lookup(call, context):
    # Allows context to be saved for later
    # for inference inside a function
    context_lookup = {}
    if context is None:
        return context_lookup
    for arg in call.args:
        if isinstance(arg, nodes.Starred):
            context_lookup[arg.value] = context
        else:
            context_lookup[arg] = context
    keywords = call.keywords if call.keywords is not None else []
    for keyword in keywords:
        context_lookup[keyword.value] = context
    return context_lookup


@decorators.raise_if_nothing_inferred
def infer_ifexp(self, context=None):
    """Support IfExp inference

    If we can't infer the truthiness of the condition, we default
    to inferring both branches. Otherwise, we infer either branch
    depending on the condition.
    """
    both_branches = False
    # We use two separate contexts for evaluating lhs and rhs because
    # evaluating lhs may leave some undesired entries in context.path
    # which may not let us infer right value of rhs.

    context = context or InferenceContext()
    lhs_context = copy_context(context)
    rhs_context = copy_context(context)
    try:
        test = next(self.test.infer(context=context.clone()))
    except (InferenceError, StopIteration):
        both_branches = True
    else:
        if test is not util.Uninferable:
            if test.bool_value():
                yield from self.body.infer(context=lhs_context)
            else:
                yield from self.orelse.infer(context=rhs_context)
        else:
            both_branches = True
    if both_branches:
        yield from self.body.infer(context=lhs_context)
        yield from self.orelse.infer(context=rhs_context)


nodes.IfExp._infer = infer_ifexp  # type: ignore[assignment]


def infer_functiondef(
    self: _FunctionDefT, context: InferenceContext | None = None
) -> Generator[Property | _FunctionDefT, None, InferenceErrorInfo]:
    if not self.decorators or not bases._is_property(self):
        yield self
        return InferenceErrorInfo(node=self, context=context)

    # When inferring a property, we instantiate a new `objects.Property` object,
    # which in turn, because it inherits from `FunctionDef`, sets itself in the locals
    # of the wrapping frame. This means that every time we infer a property, the locals
    # are mutated with a new instance of the property. To avoid this, we detect this
    # scenario and avoid passing the `parent` argument to the constructor.
    parent_frame = self.parent.frame(future=True)
    property_already_in_parent_locals = self.name in parent_frame.locals and any(
        isinstance(val, objects.Property) for val in parent_frame.locals[self.name]
    )

    prop_func = objects.Property(
        function=self,
        name=self.name,
        lineno=self.lineno,
        parent=self.parent if not property_already_in_parent_locals else None,
        col_offset=self.col_offset,
    )
    if property_already_in_parent_locals:
        prop_func.parent = self.parent
    prop_func.postinit(body=[], args=self.args, doc_node=self.doc_node)
    yield prop_func
    return InferenceErrorInfo(node=self, context=context)


nodes.FunctionDef._infer = infer_functiondef  # type: ignore[assignment]
