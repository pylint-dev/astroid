
from logilab.common.testlib import unittest_main, TestCase

from logilab.astng import ResolveError, MANAGER as m, Instance, YES, InferenceError
from logilab.astng.builder import ASTNGBuilder, build_module

import sys
from os.path import abspath
sys.path.insert(1, abspath('regrtest_data'))

class NonRegressionTC(TestCase):

##     def test_resolve1(self):
##         mod = m.astng_from_module_name('data.nonregr')
##         cls = mod['OptionParser']
##         self.assertRaises(ResolveError, cls.resolve_dotted, cls.basenames[0])
##         #self.assert_(cls is not cls.resolve_dotted(cls.basenames[0]))

    def test_module_path(self):
        mod = m.astng_from_module_name('import_package_subpackage_module')
        package = mod.igetattr('package').next()
        self.failUnlessEqual(package.name, 'package')
        subpackage = package.igetattr('subpackage').next()
        self.failUnlessEqual(subpackage.name, 'package.subpackage')
        module = subpackage.igetattr('module').next()
        self.failUnlessEqual(module.name, 'package.subpackage.module')


    def test_living_property(self):
        builder = ASTNGBuilder()
        builder._done = {}
        builder._module = sys.modules[__name__]
        builder.object_build(build_module('module_name', ''), Whatever)

    def test_new_style_class_detection(self):
        try:
            import pygtk
        except ImportError:
            self.skip('test skipped: pygtk is not available')
        else:
            # XXX may fail on some pygtk version, because objects in
            # gobject._gobject have __module__ set to gobject :(
            builder = ASTNGBuilder()
            data = """
import pygtk
pygtk.require("2.6")
import gobject

class A(gobject.GObject):
    def __init__(self, val):
        gobject.GObject.__init__(self)
        self._val = val
    def _get_val(self):
        print "get"
        return self._val
    def _set_val(self, val):
        print "set"
        self._val = val
    val = property(_get_val, _set_val)


if __name__ == "__main__":
    print gobject.GObject.__bases__
    a = A(7)
    print a.val
    a.val = 6
    print a.val
"""
            astng = builder.string_build(data, __name__, __file__)
            a = astng['A']
            self.failUnless(a.newstyle)


    def test_pylint_config_attr(self):
        try:
            from pylint import lint
        except ImportError:
            self.skip('pylint not available')
        mod = m.astng_from_module_name('pylint.lint')
        pylinter = mod['PyLinter']
        self.assertEquals([c.name for c in pylinter.ancestors()],
                          ['OptionsManagerMixIn', 'object', 'MessagesHandlerMixIn',
                           'ReportsHandlerMixIn', 'BaseRawChecker', 'BaseChecker',
                           'OptionsProviderMixIn', 'ASTWalker'])
        
        self.assert_(list(Instance(pylinter).getattr('config')))
        infered = list(Instance(pylinter).igetattr('config'))
        self.assertEquals(len(infered), 2)
        infered = [c for c in infered if not c is YES]
        self.assertEquals(len(infered), 1)
        self.assertEquals(infered[0].root().name, 'optparse')
        self.assertEquals(infered[0].name, 'Values')
        
    def test_numpy_crash(self):
        try:
            import numpy
        except ImportError:
            self.skip('test skipped: numpy is not available')
        else:
            builder = ASTNGBuilder()
            data = """
from numpy import multiply

multiply(1, 2, 3)
"""
            astng = builder.string_build(data, __name__, __file__)
            callfunc = astng.node.nodes[1].expr
            # well, InferenceError instead of a crash is better
            self.assertRaises(InferenceError, list, callfunc.infer())

        
class Whatever(object):
    a = property(lambda x: x, lambda x: x)
    
if __name__ == '__main__':
    unittest_main()
