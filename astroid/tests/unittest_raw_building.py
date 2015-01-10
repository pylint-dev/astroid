import unittest

from astroid.raw_building import (attach_dummy_node, build_module, build_class, build_function, build_from_import)

class RawBuildingTC(unittest.TestCase):

    def test_attach_dummy_node(self):
        node = build_module('MyModule')
        dummy = attach_dummy_node(node, 'DummyNode')
        self.assertEqual(1, len(list(node.get_children())))

    def test_build_module(self):
        node = build_module('MyModule')
        self.assertEqual(node.name, 'MyModule')
        self.assertEqual(node.pure_python, False)
        self.assertEqual(node.package, False)
        self.assertEqual(node.parent, None)

    def test_build_class(self):
        node = build_class('MyClass')
        self.assertEqual(node.name, 'MyClass')
        self.assertEqual(node.doc, None)

    def test_build_function(self):
        node = build_function('MyFunction')
        self.assertEqual(node.name, 'MyFunction')
        self.assertEqual(node.doc, None)

    def test_build_function_args(self):
        args = ['myArgs1', 'myArgs2']
        node = build_function('MyFunction', args)
        self.assertEqual('myArgs1', node.args.args[0].name)
        self.assertEqual('myArgs2', node.args.args[1].name)
        self.assertEqual(2, len(node.args.args))

    def test_build_function_defaults(self):
        defaults = ['defaults1', 'defaults2']
        node = build_function('MyFunction', None, defaults)
        self.assertEqual(2, len(node.args.defaults))

    def test_build_from_import(self):
        names = ['exceptions, inference, inspector']
        node = build_from_import('astroid', names)
        self.assertEqual(len(names), len(node.names))


if __name__ == '__main__':
    unittest.main()
