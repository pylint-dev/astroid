import inspect
import os
import unittest

from six.moves import builtins # pylint: disable=import-error

from astroid.builder import AstroidBuilder
# from astroid.raw_building import (
#     attach_dummy_node, build_module, build_class, build_function,
#     build_from_import, object_build_function, Parameter
# )
from astroid import nodes
from astroid import raw_building
from astroid import test_utils
from astroid import util
from astroid.bases import BUILTINS


class RawBuildingTC(unittest.TestCase):
    @test_utils.require_version(minver='3.0')
    def test_io_is__io(self):
        # _io module calls itself io. This leads
        # to cyclic dependencies when astroid tries to resolve
        # what io.BufferedReader is. The code that handles this
        # is in astroid.raw_building.imported_member, which verifies
        # the true name of the module.
        import _io

        # builder = AstroidBuilder()
        # module = builder.inspect_build(_io)
        module = raw_building.ast_from_object(_io, name='io')
        buffered_reader = module.getattr('BufferedReader')[0]
        self.assertEqual(buffered_reader.root().name, 'io')

    @unittest.skipUnless(util.JYTHON, 'Requires Jython')
    def test_open_is_inferred_correctly(self):
        # Lot of Jython builtins don't have a __module__ attribute.
        for name, _ in inspect.getmembers(builtins, predicate=inspect.isbuiltin):
            if name == 'print':
                continue
            node = test_utils.extract_node('{0} #@'.format(name))
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.FunctionDef, name)
            self.assertEqual(inferred.root().name, BUILTINS, name)


if __name__ == '__main__':
    unittest.main()
