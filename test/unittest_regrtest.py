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

from logilab.common.testlib import unittest_main, TestCase, require_version

from astroid import ResolveError, MANAGER, Instance, nodes, YES, InferenceError
from astroid.builder import AstroidBuilder
from astroid.raw_building import build_module
from astroid.manager import AstroidManager

import sys
from os.path import join, abspath, dirname

class NonRegressionTC(TestCase):

    def setUp(self):
        sys.path.insert(0, join(dirname(abspath(__file__)), 'regrtest_data'))

    def tearDown(self):
        # Since we may have created a brainless manager, leading
        # to a new cache builtin module and proxy classes in the constants,
        # clear out the global manager cache.
        MANAGER.clear_cache()
        sys.path.pop(0)

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
        package = mod.igetattr('package').next()
        self.assertEqual(package.name, 'package')
        subpackage = package.igetattr('subpackage').next()
        self.assertIsInstance(subpackage, nodes.Module)
        self.assertTrue(subpackage.package)
        self.assertEqual(subpackage.name, 'package.subpackage')
        module = subpackage.igetattr('module').next()
        self.assertEqual(module.name, 'package.subpackage.module')


    def test_package_sidepackage(self):
        manager = self.brainless_manager()
        assert 'package.sidepackage' not in MANAGER.astroid_cache
        package = manager.ast_from_module_name('absimp')
        self.assertIsInstance(package, nodes.Module)
        self.assertTrue(package.package)
        subpackage = package.getattr('sidepackage')[0].infer().next()
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
            import pygtk
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
            from pylint import lint
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
            import numpy
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
        self.assertIsInstance(infered[0], Instance)

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

class Whatever(object):
    a = property(lambda x: x, lambda x: x)

if __name__ == '__main__':
    unittest_main()
