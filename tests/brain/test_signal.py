# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Unit Tests for the signal brain module."""


import sys

import pytest

from astroid import builder, nodes

# Define signal enums
ENUMS = ["Signals", "Handlers", "Sigmasks"]
if sys.platform == "win32":
    ENUMS.remove("Sigmasks")  # Sigmasks do not exist on Windows


@pytest.mark.parametrize("enum_name", ENUMS)
def test_enum(enum_name):
    """Tests that the signal module enums are handled by the brain."""
    # Extract node for signal module enum from code
    node = builder.extract_node(
        f"""
        import signal
        signal.{enum_name}
        """
    )

    # Check the extracted node
    assert isinstance(node, nodes.NodeNG)
    node_inf = node.inferred()[0]
    assert isinstance(node_inf, nodes.ClassDef)
    assert node_inf.display_type() == "Class"
    assert node_inf.is_subtype_of("enum.IntEnum")
    assert node_inf.qname() == f"signal.{enum_name}"

    # Check enum members
    for member in node_inf.body:
        assert isinstance(member, nodes.Assign)
        for target in member.targets:
            assert isinstance(target, nodes.AssignName)
