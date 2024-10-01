# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for understanding ``boto3.ServiceRequest()``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from astroid.builder import extract_node
from astroid.nodes.scoped_nodes import ClassDef

if TYPE_CHECKING:
    from astroid.manager import AstroidManager


BOTO_SERVICE_FACTORY_QUALIFIED_NAME = "boto3.resources.base.ServiceResource"


def service_request_transform(node: ClassDef) -> ClassDef:
    """Transform ServiceResource to look like dynamic classes."""
    code = """
    def __getattr__(self, attr):
        return 0
    """
    func_getattr = extract_node(code)
    node.locals["__getattr__"] = [func_getattr]
    return node


def _looks_like_boto3_service_request(node: ClassDef) -> bool:
    return node.qname() == BOTO_SERVICE_FACTORY_QUALIFIED_NAME


def register(manager: AstroidManager) -> None:
    manager.register_transform(
        ClassDef,
        service_request_transform,
        _looks_like_boto3_service_request,
    )
