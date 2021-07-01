# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
"""
Astroid hook for the dataclasses library
"""
from astroid.manager import AstroidManager
from astroid.node_classes import (
    AnnAssign,
    Assign,
    Attribute,
    Call,
    Name,
    Subscript,
    Unknown,
)
from astroid.scoped_nodes import ClassDef

DATACLASSES_DECORATORS = frozenset(("dataclasses.dataclass", "dataclass"))


def is_decorated_with_dataclass(node, decorator_names=DATACLASSES_DECORATORS):
    """Return True if a decorated node has a `dataclass` decorator applied."""
    if not node.decorators:
        return False
    for decorator_attribute in node.decorators.nodes:
        if isinstance(decorator_attribute, Call):  # decorator with arguments
            decorator_attribute = decorator_attribute.func
        if decorator_attribute.as_string() in decorator_names:
            return True
    return False


def dataclass_transform(node):
    """Rewrite a dataclass to be easily understood by pylint"""

    for assign_node in node.body:
        if not isinstance(assign_node, (AnnAssign, Assign)):
            continue

        if (
            isinstance(assign_node, AnnAssign)
            and isinstance(assign_node.annotation, Subscript)
            and (
                isinstance(assign_node.annotation.value, Name)
                and assign_node.annotation.value.name == "ClassVar"
                or isinstance(assign_node.annotation.value, Attribute)
                and assign_node.annotation.value.attrname == "ClassVar"
            )
        ):
            continue

        targets = (
            assign_node.targets
            if hasattr(assign_node, "targets")
            else [assign_node.target]
        )
        for target in targets:
            rhs_node = Unknown(
                lineno=assign_node.lineno,
                col_offset=assign_node.col_offset,
                parent=assign_node,
            )
            node.instance_attrs[target.name] = [rhs_node]
            node.locals[target.name] = [rhs_node]


AstroidManager().register_transform(
    ClassDef, dataclass_transform, is_decorated_with_dataclass
)
