# copyright 2003-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.
import sys
import unittest
import textwrap

from astroid import MANAGER, Instance, nodes
from astroid.builder import AstroidBuilder
from astroid.raw_building import build_module
from astroid.manager import AstroidManager
from astroid.test_utils import require_version
from astroid.tests import resources

class NonRegressionTests(resources.AstroidCacheSetupMixin,
                         unittest.TestCase):

    def setUp(self):
        sys.path.insert(0, resources.find('data'))
        MANAGER.always_load_extensions = True

    def tearDown(self):
        # Since we may have created a brainless manager, leading
        # to a new cache builtin module and proxy classes in the constants,
        # clear out the global manager cache.
        MANAGER.clear_cache(self._builtins)
        MANAGER.always_load_extensions = False
        sys.path.pop(0)
        sys.path_importer_cache.pop(resources.find('data'), None)

    def brainless_manager(self):
        manager = AstroidManager()
        # avoid caching into the AstroidManager borg since we get problems
        # with other tests :
        manager.__dict__ = {}
        manager.astroid_cache = {}
        manager._mod_file_cache = {}
        manager.transforms = {}
        manager.clear_cache() # trigger proper bootstraping
        return manager

    def test_module_path(self):
        man = self.brainless_manager()
        mod = man.ast_from_module_name('package.import_package_subpackage_module')
        package = next(mod.igetattr('package'))
        self.assertEqual(package.name, 'package')
        subpackage = next(package.igetattr('subpackage'))
        self.assertIsInstance(subpackage, nodes.Module)
        self.assertTrue(subpackage.package)
        self.assertEqual(subpackage.name, 'package.subpackage')
        module = next(subpackage.igetattr('module'))
        self.assertEqual(module.name, 'package.subpackage.module')


    def test_package_sidepackage(self):
        manager = self.brainless_manager()
        assert 'package.sidepackage' not in MANAGER.astroid_cache
        package = manager.ast_from_module_name('absimp')
        self.assertIsInstance(package, nodes.Module)
        self.assertTrue(package.package)
        subpackage = next(package.getattr('sidepackage')[0].infer())
        self.assertIsInstance(subpackage, nodes.Module)
        self.assertTrue(subpackage.package)
        self.assertEqual(subpackage.name, 'absimp.sidepackage')


    def test_living_property(self):
        builder = AstroidBuilder()
        builder._done = {}
        builder._module = sys.modules[__name__]
        builder.object_build(build_module('module_name', ''), Whatever)


    def test_new_style_class_detection(self):
        try:
            import pygtk # pylint: disable=unused-variable
        except ImportError:
            self.skipTest('test skipped: pygtk is not available')
        # XXX may fail on some pygtk version, because objects in
        # gobject._gobject have __module__ set to gobject :(
        builder = AstroidBuilder()
        data = """
import pygtk
pygtk.require("2.6")
import gobject

class A(gobject.GObject):
    pass
"""
        astroid = builder.string_build(data, __name__, __file__)
        a = astroid['A']
        self.assertTrue(a.newstyle)


    def test_pylint_config_attr(self):
        try:
            from pylint import lint # pylint: disable=unused-variable
        except ImportError:
            self.skipTest('pylint not available')
        mod = MANAGER.ast_from_module_name('pylint.lint')
        pylinter = mod['PyLinter']
        expect = ['OptionsManagerMixIn', 'object', 'MessagesHandlerMixIn',
                  'ReportsHandlerMixIn', 'BaseTokenChecker', 'BaseChecker',
                  'OptionsProviderMixIn']
        self.assertListEqual([c.name for c in pylinter.ancestors()],
                             expect)
        self.assertTrue(list(Instance(pylinter).getattr('config')))
        infered = list(Instance(pylinter).igetattr('config'))
        self.assertEqual(len(infered), 1)
        self.assertEqual(infered[0].root().name, 'optparse')
        self.assertEqual(infered[0].name, 'Values')

    def test_numpy_crash(self):
        """test don't crash on numpy"""
        #a crash occured somewhere in the past, and an
        # InferenceError instead of a crash was better, but now we even infer!
        try:
            import numpy # pylint: disable=unused-variable
        except ImportError:
            self.skipTest('test skipped: numpy is not available')
        builder = AstroidBuilder()
        data = """
from numpy import multiply

multiply(1, 2, 3)
"""
        astroid = builder.string_build(data, __name__, __file__)
        callfunc = astroid.body[1].value.func
        infered = callfunc.infered()
        self.assertEqual(len(infered), 1)

    @require_version('3.0')
    def test_nameconstant(self):
        # used to fail for Python 3.4
        builder = AstroidBuilder()
        astroid = builder.string_build("def test(x=True): pass")
        default = astroid.body[0].args.args[0]
        self.assertEqual(default.name, 'x')
        self.assertEqual(next(default.infer()).value, True)

    @require_version('2.7')
    def test_with_infer_assnames(self):
        builder = AstroidBuilder()
        data = """
with open('a.txt') as stream, open('b.txt'):
    stream.read()
"""
        astroid = builder.string_build(data, __name__, __file__)
        # Used to crash due to the fact that the second
        # context manager didn't use an assignment name.
        list(astroid.nodes_of_class(nodes.CallFunc))[-1].infered()

    def test_recursion_regression_issue25(self):
        builder = AstroidBuilder()
        data = """
import recursion as base

_real_Base = base.Base

class Derived(_real_Base):
    pass

def run():
    base.Base = Derived
"""
        astroid = builder.string_build(data, __name__, __file__)
        # Used to crash in _is_metaclass, due to wrong
        # ancestors chain
        classes = astroid.nodes_of_class(nodes.Class)
        for klass in classes:
            # triggers the _is_metaclass call
            klass.type

    def test_decorator_callchain_issue42(self):
        builder = AstroidBuilder()
        data = """

def test():
    def factory(func):
        def newfunc():
            func()
        return newfunc
    return factory

@test()
def crash():
    pass
"""
        astroid = builder.string_build(data, __name__, __file__)
        self.assertEqual(astroid['crash'].type, 'function')

    def test_filter_stmts_scoping(self):
        builder = AstroidBuilder()
        data = """
def test():
    compiler = int()
    class B(compiler.__class__):
        pass
    compiler = B()
    return compiler
"""
        astroid = builder.string_build(data, __name__, __file__)
        test = astroid['test']
        result = next(test.infer_call_result(astroid))
        self.assertIsInstance(result, Instance)
        base = next(result._proxied.bases[0].infer())
        self.assertEqual(base.name, 'int')

    def test_ancestors_patching_class_recursion(self):
        node = AstroidBuilder().string_build(textwrap.dedent("""
        import string
        Template = string.Template

        class A(Template):
            pass

        class B(A):
            pass

        def test(x=False):
            if x:
                string.Template = A
            else:
                string.Template = B
        """))
        klass = node['A']
        ancestors = list(klass.ancestors())
        self.assertEqual(ancestors[0].qname(), 'string.Template')


class Whatever(object):
    a = property(lambda x: x, lambda x: x)

if __name__ == '__main__':
    unittest.main()
