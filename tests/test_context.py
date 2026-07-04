# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for ``astroid.context.InferenceContext``.

The hot-path ``clone()`` implementation bypasses ``__init__`` and writes
slots directly. These tests pin down each field's clone semantics so a
future refactor of either ``__init__`` or ``clone()`` can't silently
diverge them.
"""

from __future__ import annotations

import pytest

from astroid import extract_node, nodes
from astroid.context import CallContext, InferenceContext


def _populated_context() -> InferenceContext:
    """Return a context with every clonable slot set to a distinctive value."""
    node = extract_node("x = 1; x #@")
    ctx = InferenceContext()
    ctx.path.add((node, "x"))
    ctx.lookupname = "x"
    ctx.callcontext = CallContext(args=[node])
    ctx.boundnode = node
    ctx.extra_context = {node: InferenceContext()}
    # ``_nodes_inferred`` is a 1-element list used as a mutable counter
    # shared across clones, so put a recognizable value in it.
    ctx._nodes_inferred[0] = 7
    return ctx


class TestInferenceContextInit:
    """``__init__`` slow path — no longer exercised by ``clone()``."""

    def test_init_with_explicit_nodes_inferred(self) -> None:
        """An explicitly passed counter cell is adopted, not copied.

        The old ``clone()`` used this parameter to share the counter;
        the fast path writes the slot directly, so this keeps the
        ``__init__`` contract covered for external callers.
        """
        cell = [7]
        ctx = InferenceContext(nodes_inferred=cell)
        assert ctx._nodes_inferred is cell
        assert ctx.nodes_inferred == 7
        ctx.nodes_inferred = 42
        assert cell[0] == 42

    def test_init_default_nodes_inferred(self) -> None:
        """Without the parameter, each context gets its own zeroed cell."""
        ctx = InferenceContext()
        other = InferenceContext()
        assert ctx.nodes_inferred == 0
        assert ctx._nodes_inferred is not other._nodes_inferred


class TestInferenceContextClone:
    """The clone() fast-path must preserve the semantics of the slow path."""

    def test_clone_path_is_independent_copy(self) -> None:
        """``path`` is copied — mutating the clone's path must not affect the original."""
        original = _populated_context()
        clone = original.clone()
        assert clone.path == original.path
        assert clone.path is not original.path
        clone.path.clear()
        assert original.path, "clearing the clone leaked back to the original"

    def test_clone_lookupname_is_reset(self) -> None:
        """``clone()`` deliberately drops the original's ``lookupname``."""
        original = _populated_context()
        assert original.lookupname == "x"
        clone = original.clone()
        assert clone.lookupname is None

    def test_clone_shares_nodes_inferred_counter(self) -> None:
        """``_nodes_inferred`` is a mutable cell shared across the clone family.

        Otherwise the per-inference budget enforced by ``max_inferred``
        would reset on every clone and the ``nodes_inferred`` property
        would not see writes made through the clone.
        """
        original = _populated_context()
        clone = original.clone()
        assert clone._nodes_inferred is original._nodes_inferred
        clone.nodes_inferred = 42
        assert original.nodes_inferred == 42

    def test_clone_propagates_callcontext_and_boundnode(self) -> None:
        """Call-site state and bound node are passed through by identity."""
        original = _populated_context()
        clone = original.clone()
        assert clone.callcontext is original.callcontext
        assert clone.boundnode is original.boundnode
        assert clone.extra_context is original.extra_context

    def test_clone_constraints_is_independent_copy(self) -> None:
        """Constraints dict is shallow-copied so per-branch state can diverge."""
        node = extract_node("if x: pass #@")
        original = InferenceContext()
        original.constraints["x"] = {node: set()}
        clone = original.clone()
        assert clone.constraints == original.constraints
        assert clone.constraints is not original.constraints
        clone.constraints["y"] = {}
        assert "y" not in original.constraints

    def test_clone_skips_init(self) -> None:
        """The fast path goes through ``__new__``, not ``__init__``.

        Subclasses that override ``__init__`` for side effects (none today,
        but plausible) would notice this, and so would profilers — the
        whole point of the change is to avoid the ``__init__`` body.
        """
        # The patch/restore dance below trips ``redefined-variable-type``
        # because ``__init__`` flips between a plain function and a bound
        # method. That's the whole point of the test.
        # pylint: disable=redefined-variable-type
        called = []

        original_init = InferenceContext.__init__

        def tracking_init(self, *args, **kwargs):
            called.append((args, kwargs))
            original_init(self, *args, **kwargs)

        InferenceContext.__init__ = tracking_init
        try:
            ctx = InferenceContext()
            assert called, "sanity check: instantiation should call __init__"
            called.clear()
            ctx.clone()
            assert not called, f"clone() must bypass __init__; got calls: {called!r}"
        finally:
            InferenceContext.__init__ = original_init

    def test_clone_returns_inference_context_instance(self) -> None:
        """Type identity is preserved (regression guard against ``__new__`` misuse)."""
        ctx = InferenceContext()
        clone = ctx.clone()
        # We deliberately want exact-type identity here, not ``isinstance``,
        # because ``__new__`` mis-applied to a subclass would yield a wrong
        # concrete type that ``isinstance`` would still accept.
        assert type(clone) is InferenceContext  # pylint: disable=unidiomatic-typecheck

    def test_clone_is_not_is_empty_when_seeded(self) -> None:
        """End-to-end check: a populated clone still reports as non-empty."""
        original = _populated_context()
        clone = original.clone()
        # ``lookupname`` is reset and ``nodes_inferred`` would be cleared,
        # but ``path`` / ``callcontext`` / ``boundnode`` carry over and
        # keep the clone non-empty.
        assert not clone.is_empty()


@pytest.mark.parametrize(
    "node_source",
    [
        "x = 1\nx #@",
        "def f(): return 1\nf() #@",
    ],
)
def test_clone_keeps_inference_working(node_source: str) -> None:
    """End-to-end sanity: inference through a cloned context still resolves."""
    node = extract_node(node_source)
    ctx = InferenceContext()
    clone = ctx.clone()
    inferred = next(node.infer(context=clone))
    assert isinstance(inferred, (nodes.Const, nodes.FunctionDef, nodes.NodeNG))
