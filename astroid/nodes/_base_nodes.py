# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""This module contains some base nodes that can be inherited for the different nodes.

Previously these were called Mixin nodes.
"""

from __future__ import annotations

import itertools
from collections.abc import Generator, Iterator
from functools import cached_property, partial
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional, Union

from astroid import bases, decorators, nodes, util
from astroid.const import PY310_PLUS
from astroid.context import CallContext, bind_context_to_node, copy_context
from astroid.exceptions import (
    AttributeInferenceError,
    InferenceError,
    NameInferenceError,
)
from astroid.interpreter import dunder_lookup
from astroid.nodes.node_ng import NodeNG
from astroid.typing import InferenceErrorInfo, InferenceResult

if TYPE_CHECKING:
    from astroid.context import InferenceContext
    from astroid.nodes.node_classes import AssignedStmtsPossibleNode

    GetFlowFactory = Callable[
        [
            InferenceResult,
            Optional[InferenceResult],
            Union[nodes.AugAssign, nodes.BinOp],
            InferenceResult,
            Optional[InferenceResult],
            InferenceContext,
            InferenceContext,
        ],
        "list[partial[Generator[InferenceResult, None, None]]]",
    ]


class Statement(NodeNG):
    """Statement node adding a few attributes.

    NOTE: This class is part of the public API of 'astroid.nodes'.
    """

    is_statement = True
    """Whether this node indicates a statement."""

    def next_sibling(self):
        """The next sibling statement node.

        :returns: The next sibling statement node.
        :rtype: NodeNG or None
        """
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        try:
            return stmts[index + 1]
        except IndexError:
            return None

    def previous_sibling(self):
        """The previous sibling statement.

        :returns: The previous sibling statement node.
        :rtype: NodeNG or None
        """
        stmts = self.parent.child_sequence(self)
        index = stmts.index(self)
        if index >= 1:
            return stmts[index - 1]
        return None


class NoChildrenNode(NodeNG):
    """Base nodes for nodes with no children, e.g. Pass."""

    def get_children(self) -> Iterator[NodeNG]:
        yield from ()


class FilterStmtsBaseNode(NodeNG):
    """Base node for statement filtering and assignment type."""

    def _get_filtered_stmts(self, _, node, _stmts, mystmt: Statement | None):
        """Method used in _filter_stmts to get statements and trigger break."""
        if self.statement() is mystmt:
            # original node's statement is the assignment, only keep
            # current node (gen exp, list comp)
            return [node], True
        return _stmts, False

    def assign_type(self):
        return self


class AssignTypeNode(NodeNG):
    """Base node for nodes that can 'assign' such as AnnAssign."""

    def assign_type(self):
        return self

    def _get_filtered_stmts(self, lookup_node, node, _stmts, mystmt: Statement | None):
        """Method used in filter_stmts."""
        if self is mystmt:
            return _stmts, True
        if self.statement() is mystmt:
            # original node's statement is the assignment, only keep
            # current node (gen exp, list comp)
            return [node], True
        return _stmts, False


class ParentAssignNode(AssignTypeNode):
    """Base node for nodes whose assign_type is determined by the parent node."""

    def assign_type(self):
        return self.parent.assign_type()


class ImportNode(FilterStmtsBaseNode, NoChildrenNode, Statement):
    """Base node for From and Import Nodes."""

    modname: str | None
    """The module that is being imported from.

    This is ``None`` for relative imports.
    """

    names: list[tuple[str, str | None]]
    """What is being imported from the module.

    Each entry is a :class:`tuple` of the name being imported,
    and the alias that the name is assigned to (if any).
    """

    def _infer_name(self, frame, name):
        return name

    def do_import_module(self, modname: str | None = None) -> nodes.Module:
        """Return the ast for a module whose name is <modname> imported by <self>."""
        mymodule = self.root()
        level: int | None = getattr(self, "level", None)  # Import has no level
        if modname is None:
            modname = self.modname
        # If the module ImportNode is importing is a module with the same name
        # as the file that contains the ImportNode we don't want to use the cache
        # to make sure we use the import system to get the correct module.
        if (
            modname
            # pylint: disable-next=no-member # pylint doesn't recognize type of mymodule
            and mymodule.relative_to_absolute_name(modname, level) == mymodule.name
        ):
            use_cache = False
        else:
            use_cache = True

        # pylint: disable-next=no-member # pylint doesn't recognize type of mymodule
        return mymodule.import_module(
            modname,
            level=level,
            relative_only=bool(level and level >= 1),
            use_cache=use_cache,
        )

    def real_name(self, asname: str) -> str:
        """Get name from 'as' name."""
        for name, _asname in self.names:
            if name == "*":
                return asname
            if not _asname:
                name = name.split(".", 1)[0]
                _asname = name
            if asname == _asname:
                return name
        raise AttributeInferenceError(
            "Could not find original name for {attribute} in {target!r}",
            target=self,
            attribute=asname,
        )


class MultiLineBlockNode(NodeNG):
    """Base node for multi-line blocks, e.g. For and FunctionDef.

    Note that this does not apply to every node with a `body` field.
    For instance, an If node has a multi-line body, but the body of an
    IfExpr is not multi-line, and hence cannot contain Return nodes,
    Assign nodes, etc.
    """

    _multi_line_block_fields: ClassVar[tuple[str, ...]] = ()

    @cached_property
    def _multi_line_blocks(self):
        return tuple(getattr(self, field) for field in self._multi_line_block_fields)

    def _get_return_nodes_skip_functions(self):
        for block in self._multi_line_blocks:
            for child_node in block:
                if child_node.is_function:
                    continue
                yield from child_node._get_return_nodes_skip_functions()

    def _get_yield_nodes_skip_lambdas(self):
        for block in self._multi_line_blocks:
            for child_node in block:
                if child_node.is_lambda:
                    continue
                yield from child_node._get_yield_nodes_skip_lambdas()

    @cached_property
    def _assign_nodes_in_scope(self) -> list[nodes.Assign]:
        children_assign_nodes = (
            child_node._assign_nodes_in_scope
            for block in self._multi_line_blocks
            for child_node in block
        )
        return list(itertools.chain.from_iterable(children_assign_nodes))


class MultiLineWithElseBlockNode(MultiLineBlockNode):
    """Base node for multi-line blocks that can have else statements."""

    @cached_property
    def blockstart_tolineno(self):
        return self.lineno

    def _elsed_block_range(
        self, lineno: int, orelse: list[nodes.NodeNG], last: int | None = None
    ) -> tuple[int, int]:
        """Handle block line numbers range for try/finally, for, if and while
        statements.
        """
        if lineno == self.fromlineno:
            return lineno, lineno
        if orelse:
            if lineno >= orelse[0].fromlineno:
                return lineno, orelse[-1].tolineno
            return lineno, orelse[0].fromlineno - 1
        return lineno, last or self.tolineno


class OperatorNode(NodeNG):
    @staticmethod
    def _filter_operation_errors(
        infer_callable: Callable[
            [InferenceContext | None],
            Generator[InferenceResult | util.BadOperationMessage, None, None],
        ],
        context: InferenceContext | None,
        error: type[util.BadOperationMessage],
    ) -> Generator[InferenceResult, None, None]:
        for result in infer_callable(context):
            if isinstance(result, error):
                # For the sake of .infer(), we don't care about operation
                # errors, which is the job of pylint. So return something
                # which shows that we can't infer the result.
                yield util.Uninferable
            else:
                yield result

    @staticmethod
    def _is_not_implemented(const) -> bool:
        """Check if the given const node is NotImplemented."""
        return isinstance(const, nodes.Const) and const.value is NotImplemented

    @staticmethod
    def _infer_old_style_string_formatting(
        instance: nodes.Const, other: nodes.NodeNG, context: InferenceContext
    ) -> tuple[util.UninferableBase | nodes.Const]:
        """Infer the result of '"string" % ...'.

        TODO: Instead of returning Uninferable we should rely
        on the call to '%' to see if the result is actually uninferable.
        """
        from astroid import helpers

        if isinstance(other, nodes.Tuple):
            if util.Uninferable in other.elts:
                return (util.Uninferable,)
            inferred_positional = [helpers.safe_infer(i, context) for i in other.elts]
            if all(isinstance(i, nodes.Const) for i in inferred_positional):
                values = tuple(i.value for i in inferred_positional)
            else:
                values = None
        elif isinstance(other, nodes.Dict):
            values: dict[Any, Any] = {}
            for pair in other.items:
                key = helpers.safe_infer(pair[0], context)
                if not isinstance(key, nodes.Const):
                    return (util.Uninferable,)
                value = helpers.safe_infer(pair[1], context)
                if not isinstance(value, nodes.Const):
                    return (util.Uninferable,)
                values[key.value] = value.value
        elif isinstance(other, nodes.Const):
            values = other.value
        else:
            return (util.Uninferable,)

        try:
            return (nodes.const_factory(instance.value % values),)
        except (TypeError, KeyError, ValueError):
            return (util.Uninferable,)

    @staticmethod
    def _invoke_binop_inference(
        instance: InferenceResult,
        opnode: nodes.AugAssign | nodes.BinOp,
        op: str,
        other: InferenceResult,
        context: InferenceContext,
        method_name: str,
    ) -> Generator[InferenceResult, None, None]:
        """Invoke binary operation inference on the given instance."""
        methods = dunder_lookup.lookup(instance, method_name)
        context = bind_context_to_node(context, instance)
        method = methods[0]
        context.callcontext.callee = method

        if (
            isinstance(instance, nodes.Const)
            and isinstance(instance.value, str)
            and op == "%"
        ):
            return iter(
                OperatorNode._infer_old_style_string_formatting(
                    instance, other, context
                )
            )

        try:
            inferred = next(method.infer(context=context))
        except StopIteration as e:
            raise InferenceError(node=method, context=context) from e
        if isinstance(inferred, util.UninferableBase):
            raise InferenceError
        if not isinstance(
            instance,
            (nodes.Const, nodes.Tuple, nodes.List, nodes.ClassDef, bases.Instance),
        ):
            raise InferenceError  # pragma: no cover # Used as a failsafe
        return instance.infer_binary_op(opnode, op, other, context, inferred)

    @staticmethod
    def _aug_op(
        instance: InferenceResult,
        opnode: nodes.AugAssign,
        op: str,
        other: InferenceResult,
        context: InferenceContext,
        reverse: bool = False,
    ) -> partial[Generator[InferenceResult, None, None]]:
        """Get an inference callable for an augmented binary operation."""
        from astroid import protocols

        method_name = protocols.AUGMENTED_OP_METHOD[op]
        return partial(
            OperatorNode._invoke_binop_inference,
            instance=instance,
            op=op,
            opnode=opnode,
            other=other,
            context=context,
            method_name=method_name,
        )

    @staticmethod
    def _bin_op(
        instance: InferenceResult,
        opnode: nodes.AugAssign | nodes.BinOp,
        op: str,
        other: InferenceResult,
        context: InferenceContext,
        reverse: bool = False,
    ) -> partial[Generator[InferenceResult, None, None]]:
        """Get an inference callable for a normal binary operation.

        If *reverse* is True, then the reflected method will be used instead.
        """
        from astroid import protocols

        if reverse:
            method_name = protocols.REFLECTED_BIN_OP_METHOD[op]
        else:
            method_name = protocols.BIN_OP_METHOD[op]
        return partial(
            OperatorNode._invoke_binop_inference,
            instance=instance,
            op=op,
            opnode=opnode,
            other=other,
            context=context,
            method_name=method_name,
        )

    @staticmethod
    def _bin_op_or_union_type(
        left: bases.UnionType | nodes.ClassDef | nodes.Const,
        right: bases.UnionType | nodes.ClassDef | nodes.Const,
    ) -> Generator[InferenceResult, None, None]:
        """Create a new UnionType instance for binary or, e.g. int | str."""
        yield bases.UnionType(left, right)

    @staticmethod
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

    @staticmethod
    def _same_type(type1, type2) -> bool:
        """Check if type1 is the same as type2."""
        return type1.qname() == type2.qname()

    @staticmethod
    def _get_aug_flow(
        left: InferenceResult,
        left_type: InferenceResult | None,
        aug_opnode: nodes.AugAssign,
        right: InferenceResult,
        right_type: InferenceResult | None,
        context: InferenceContext,
        reverse_context: InferenceContext,
    ) -> list[partial[Generator[InferenceResult, None, None]]]:
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
        from astroid import helpers

        bin_op = aug_opnode.op.strip("=")
        aug_op = aug_opnode.op
        if OperatorNode._same_type(left_type, right_type):
            methods = [
                OperatorNode._aug_op(left, aug_opnode, aug_op, right, context),
                OperatorNode._bin_op(left, aug_opnode, bin_op, right, context),
            ]
        elif helpers.is_subtype(left_type, right_type):
            methods = [
                OperatorNode._aug_op(left, aug_opnode, aug_op, right, context),
                OperatorNode._bin_op(left, aug_opnode, bin_op, right, context),
            ]
        elif helpers.is_supertype(left_type, right_type):
            methods = [
                OperatorNode._aug_op(left, aug_opnode, aug_op, right, context),
                OperatorNode._bin_op(
                    right, aug_opnode, bin_op, left, reverse_context, reverse=True
                ),
                OperatorNode._bin_op(left, aug_opnode, bin_op, right, context),
            ]
        else:
            methods = [
                OperatorNode._aug_op(left, aug_opnode, aug_op, right, context),
                OperatorNode._bin_op(left, aug_opnode, bin_op, right, context),
                OperatorNode._bin_op(
                    right, aug_opnode, bin_op, left, reverse_context, reverse=True
                ),
            ]
        return methods

    @staticmethod
    def _get_binop_flow(
        left: InferenceResult,
        left_type: InferenceResult | None,
        binary_opnode: nodes.AugAssign | nodes.BinOp,
        right: InferenceResult,
        right_type: InferenceResult | None,
        context: InferenceContext,
        reverse_context: InferenceContext,
    ) -> list[partial[Generator[InferenceResult, None, None]]]:
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
        from astroid import helpers

        op = binary_opnode.op
        if OperatorNode._same_type(left_type, right_type):
            methods = [OperatorNode._bin_op(left, binary_opnode, op, right, context)]
        elif helpers.is_subtype(left_type, right_type):
            methods = [OperatorNode._bin_op(left, binary_opnode, op, right, context)]
        elif helpers.is_supertype(left_type, right_type):
            methods = [
                OperatorNode._bin_op(
                    right, binary_opnode, op, left, reverse_context, reverse=True
                ),
                OperatorNode._bin_op(left, binary_opnode, op, right, context),
            ]
        else:
            methods = [
                OperatorNode._bin_op(left, binary_opnode, op, right, context),
                OperatorNode._bin_op(
                    right, binary_opnode, op, left, reverse_context, reverse=True
                ),
            ]

        if (
            PY310_PLUS
            and op == "|"
            and (
                isinstance(left, (bases.UnionType, nodes.ClassDef))
                or isinstance(left, nodes.Const)
                and left.value is None
            )
            and (
                isinstance(right, (bases.UnionType, nodes.ClassDef))
                or isinstance(right, nodes.Const)
                and right.value is None
            )
        ):
            methods.extend([partial(OperatorNode._bin_op_or_union_type, left, right)])
        return methods

    @staticmethod
    def _infer_binary_operation(
        left: InferenceResult,
        right: InferenceResult,
        binary_opnode: nodes.AugAssign | nodes.BinOp,
        context: InferenceContext,
        flow_factory: GetFlowFactory,
    ) -> Generator[InferenceResult, None, None]:
        """Infer a binary operation between a left operand and a right operand.

        This is used by both normal binary operations and augmented binary
        operations, the only difference is the flow factory used.
        """
        from astroid import helpers

        context, reverse_context = OperatorNode._get_binop_contexts(
            context, left, right
        )
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
                if any(isinstance(result, util.UninferableBase) for result in results):
                    yield util.Uninferable
                    return

                if all(map(OperatorNode._is_not_implemented, results)):
                    continue
                not_implemented = sum(
                    1 for result in results if OperatorNode._is_not_implemented(result)
                )
                if not_implemented and not_implemented != len(results):
                    # Can't infer yet what this is.
                    yield util.Uninferable
                    return

                yield from results
                return

        # The operation doesn't seem to be supported so let the caller know about it
        yield util.BadBinaryOperationMessage(left_type, binary_opnode.op, right_type)


class AttributeNode(NodeNG):
    expr: NodeNG
    """The name that this node represents."""

    @decorators.raise_if_nothing_inferred
    def _infer_attribute(
        self,
        context: InferenceContext | None = None,
        **kwargs: Any,
    ) -> Generator[InferenceResult, None, InferenceErrorInfo]:
        """Infer an Attribute node by using getattr on the associated object."""
        from astroid.constraint import get_constraints

        for owner in self.expr.infer(context):
            if isinstance(owner, util.UninferableBase):
                yield owner
                continue

            context = copy_context(context)
            old_boundnode = context.boundnode
            try:
                context.boundnode = owner
                if isinstance(owner, (nodes.ClassDef, bases.Instance)):
                    frame = (
                        owner if isinstance(owner, nodes.ClassDef) else owner._proxied
                    )
                    context.constraints[self.attrname] = get_constraints(
                        self, frame=frame
                    )
                yield from owner.igetattr(self.attrname, context)
            except (
                AttributeInferenceError,
                InferenceError,
                AttributeError,
            ):
                pass
            finally:
                context.boundnode = old_boundnode
        return InferenceErrorInfo(node=self, context=context)


class AssignNode(NodeNG):
    @decorators.raise_if_nothing_inferred
    @decorators.path_wrapper
    def _infer_assign(
        self,
        context: InferenceContext | None = None,
        **kwargs: Any,
    ) -> Generator[InferenceResult, None, None]:
        """Infer a AssignName/AssignAttr: need to inspect the RHS part of the
        assign node.
        """
        if isinstance(self.parent, nodes.AugAssign):
            return self.parent.infer(context)

        stmts = list(self.assigned_stmts(context=context))
        return bases._infer_stmts(stmts, context)

    def assigned_stmts(
        self: nodes.AssignName | nodes.AssignAttr,
        node: AssignedStmtsPossibleNode = None,
        context: InferenceContext | None = None,
        assign_path: list[int] | None = None,
    ) -> Any:
        """Returns the assigned statement (non inferred) according to the assignment type."""
        return self.parent.assigned_stmts(node=self, context=context)


class NameNode(NodeNG):
    @decorators.raise_if_nothing_inferred
    def _infer_name(
        self,
        context: InferenceContext | None = None,
        **kwargs: Any,
    ) -> Generator[InferenceResult, None, None]:
        """Infer a Name: use name lookup rules."""
        from astroid.constraint import get_constraints
        from astroid.helpers import _higher_function_scope

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
        context.constraints[self.name] = get_constraints(self, frame)

        return bases._infer_stmts(stmts, context, frame)
