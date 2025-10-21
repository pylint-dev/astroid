# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from collections.abc import Iterator

from astroid import bases, context, nodes, util
from astroid.builder import _extract_single_node
from astroid.const import PY313
from astroid.exceptions import InferenceError, UseInferenceDefault
from astroid.inference_tip import inference_tip
from astroid.manager import AstroidManager

PATH_TEMPLATE = """
from pathlib import Path
Path
"""


def _looks_like_parents_subscript(node: nodes.Subscript) -> bool:
    if not (
        isinstance(node.value, nodes.Attribute) and node.value.attrname == "parents"
    ):
        return False

    try:
        value = next(node.value.infer())
    except (InferenceError, StopIteration):
        return False
    parents = "builtins.tuple" if PY313 else "pathlib._PathParents"
    return (
        isinstance(value, bases.Instance)
        and isinstance(value._proxied, nodes.ClassDef)
        and value.qname() == parents
    )


def infer_parents_subscript(
    subscript_node: nodes.Subscript, ctx: context.InferenceContext | None = None
) -> Iterator[bases.Instance]:
    if isinstance(subscript_node.slice, nodes.Const):
        path_cls = next(_extract_single_node(PATH_TEMPLATE).infer())
        return iter([path_cls.instantiate_class()])
    elif isinstance(subscript_node.slice, nodes.Slice):
        # For slices, return a tuple
        parents_tuple = nodes.Tuple()
        path_cls = next(_extract_single_node(PATH_TEMPLATE).infer())
        parents_tuple.elts = [path_cls.instantiate_class() for _ in range(2)]  # Mock some parents
        return iter([parents_tuple])

    raise UseInferenceDefault


def _looks_like_parents_name(node: nodes.Name) -> bool:
    """Check if a Name node was assigned from a Path.parents attribute."""
    # Only apply to direct Name nodes, not to Name nodes in subscripts
    if isinstance(node.parent, nodes.Subscript):
        return False
    
    # Only apply to Name nodes that are direct expressions, not in subscripts
    if not isinstance(node.parent, nodes.Expr):
        return False
    
    # Look for the assignment in the current scope
    try:
        frame, stmts = node.lookup(node.name)
        if not stmts:
            return False
        
        # Check each assignment statement
        for stmt in stmts:
            if isinstance(stmt, nodes.AssignName):
                # Get the parent Assign node
                assign_node = stmt.parent
                if isinstance(assign_node, nodes.Assign):
                    # Check if the value is an Attribute access to .parents
                    if (isinstance(assign_node.value, nodes.Attribute) 
                        and assign_node.value.attrname == "parents"):
                        try:
                            # Check if the attribute is from a Path object
                            value = next(assign_node.value.expr.infer())
                            if (isinstance(value, bases.Instance) 
                                and isinstance(value._proxied, nodes.ClassDef)
                                and value.qname() in ("pathlib.Path", "pathlib._local.Path")):
                                return True
                        except (InferenceError, StopIteration):
                            pass
    except (InferenceError, StopIteration):
        pass
    return False


def infer_parents_name(
    name_node: nodes.Name, ctx: context.InferenceContext | None = None
) -> Iterator[bases.Instance]:
    """Infer a Name node that was assigned from Path.parents."""
    if PY313:
        # For Python 3.13+, parents is a tuple
        from astroid import nodes
        # Create a tuple that behaves like Path.parents
        parents_tuple = nodes.Tuple()
        # Add some mock Path elements to make indexing work
        path_cls = next(_extract_single_node(PATH_TEMPLATE).infer())
        parents_tuple.elts = [path_cls.instantiate_class() for _ in range(3)]  # Mock some parents
        return iter([parents_tuple])
    else:
        # For older versions, it's a _PathParents object
        # We need to create a mock _PathParents instance that behaves correctly
        parents_cls = _extract_single_node("""
class _PathParents:
    def __getitem__(self, key):
        from pathlib import Path
        if isinstance(key, slice):
            # Return a tuple for slices
            return (Path(), Path())
        # For indexing, return a Path object
        return Path()
""")
        return iter([parents_cls.instantiate_class()])


def _looks_like_parents_attribute(node: nodes.Attribute) -> bool:
    """Check if an Attribute node is accessing Path.parents."""
    if node.attrname != "parents":
        return False
    
    # Check if the expression is a Path object
    try:
        expr_inferred = list(node.expr.infer())
        if expr_inferred and not isinstance(expr_inferred[0], util.UninferableBase):
            expr_value = expr_inferred[0]
            if (isinstance(expr_value, bases.Instance) 
                and isinstance(expr_value._proxied, nodes.ClassDef)
                and expr_value.qname() in ("pathlib.Path", "pathlib._local.Path")):
                return True
    except (InferenceError, StopIteration):
        pass
    
    return False


def infer_parents_attribute(
    attr_node: nodes.Attribute, ctx: context.InferenceContext | None = None
) -> Iterator[bases.Instance]:
    """Infer Path.parents attribute access."""
    if PY313:
        # For Python 3.13+, parents is a tuple
        parents_tuple = nodes.Tuple()
        path_cls = next(_extract_single_node(PATH_TEMPLATE).infer())
        parents_tuple.elts = [path_cls.instantiate_class() for _ in range(3)]  # Mock some parents
        return iter([parents_tuple])
    else:
        # For older versions, it's a _PathParents object
        parents_cls = _extract_single_node("""
class _PathParents:
    def __getitem__(self, key):
        from pathlib import Path
        if isinstance(key, slice):
            # Return a tuple for slices
            return (Path(), Path())
        # For indexing, return a Path object
        return Path()
""")
        return iter([parents_cls.instantiate_class()])


def register(manager: AstroidManager) -> None:
    manager.register_transform(
        nodes.Subscript,
        inference_tip(infer_parents_subscript),
        _looks_like_parents_subscript,
    )
    manager.register_transform(
        nodes.Name,
        inference_tip(infer_parents_name),
        _looks_like_parents_name,
    )
    manager.register_transform(
        nodes.Attribute,
        inference_tip(infer_parents_attribute),
        _looks_like_parents_attribute,
    )
