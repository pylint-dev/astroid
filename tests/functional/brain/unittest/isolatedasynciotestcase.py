# Tests that the IsolatedAsyncioTestCase class is statically imported
# thanks to the brain_unittest module.
from unittest import IsolatedAsyncioTestCase

# +1: ancestors: unittest.async_case.IsolatedAsyncioTestCase, unittest.case.TestCase, builtins.object
class TestClass(IsolatedAsyncioTestCase):
    pass
