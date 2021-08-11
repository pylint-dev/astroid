"""Astroid hooks for unittest module"""
from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.manager import AstroidManager


def IsolatedAsyncioTestCaseImport():
    return parse("""
    from .async_case import IsolatedAsyncioTestCase
    """)


register_module_extender(AstroidManager(), "unittest", IsolatedAsyncioTestCaseImport)