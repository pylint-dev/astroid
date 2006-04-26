__revision__ = '$Id: regrtest.py,v 1.8 2006-01-24 19:52:08 syt Exp $'

import unittest

from logilab.astng import ResolveError, MANAGER as m
from logilab.astng.builder import ASTNGBuilder, build_module

import sys
from os.path import abspath
sys.path.insert(1, abspath('regrtest_data'))

class NonRegressionTC(unittest.TestCase):

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

        
class Whatever(object):
    a = property(lambda x: x, lambda x: x)
    
if __name__ == '__main__':
    unittest.main()
