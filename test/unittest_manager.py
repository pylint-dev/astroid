# copyright 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
# copyright 2003-2010 Sylvain Thenault, all rights reserved.
# contact mailto:thenault@gmail.com
#
# This file is part of logilab-astng.
#
# logilab-astng is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# logilab-astng is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with logilab-astng. If not, see <http://www.gnu.org/licenses/>.
import unittest
import sys
from os.path import join, abspath, dirname
from logilab.astng.manager import ASTNGManager
from logilab.astng.bases import  BUILTINS_NAME

DATA = join(dirname(abspath(__file__)), 'data')

class ASTNGManagerTC(unittest.TestCase):
    def setUp(self):
        self.manager = ASTNGManager()
        
    def test_astng_from_module(self):
        astng = self.manager.astng_from_module(unittest)
        self.assertEqual(astng.pure_python, True)
        import time
        astng = self.manager.astng_from_module(time)
        self.assertEqual(astng.pure_python, False)
        
    def test_astng_from_class(self):
        astng = self.manager.astng_from_class(int)
        self.assertEqual(astng.name, 'int')
        self.assertEqual(astng.parent.frame().name, BUILTINS_NAME)

        astng = self.manager.astng_from_class(object)
        self.assertEqual(astng.name, 'object')
        self.assertEqual(astng.parent.frame().name, BUILTINS_NAME)
        self.failUnless('__setattr__' in astng)
        
    def _test_astng_from_zip(self, archive):
        origpath = sys.path[:]
        sys.modules.pop('mypypa', None)
        sys.path.insert(0, join(DATA, archive))
        try:
            module = self.manager.astng_from_module_name('mypypa')
            self.assertEqual(module.name, 'mypypa')
            self.failUnless(module.file.endswith('%s/mypypa' % archive),
                            module.file)
        finally:
            sys.path = origpath
            # remove the module, else after importing egg, we don't get the zip
            del self.manager._cache['mypypa']
            del self.manager._mod_file_cache[('mypypa', None)]

    def test_astng_from_module_name_egg(self):
        self._test_astng_from_zip('MyPyPa-0.1.0-py2.5.egg')

    def test_astng_from_module_name_zip(self):
        self._test_astng_from_zip('MyPyPa-0.1.0-py2.5.zip')            
        
    def test_from_directory(self):
        obj = self.manager.from_directory(DATA)
        self.assertEqual(obj.name, 'data')
        self.assertEqual(obj.path, DATA)
        
    def test_package_node(self):
        obj = self.manager.from_directory(DATA)
        expected_short = ['SSL1', '__init__', 'all', 'appl', 'format', 'module', 'module2',
                          'noendingnewline', 'nonregr', 'notall']
        expected_long = ['SSL1', 'data', 'data.all', 'appl', 'data.format', 'data.module',
                         'data.module2', 'data.noendingnewline', 'data.nonregr',
                         'data.notall']
        self.assertEqual(obj.keys(), expected_short)
        self.assertEqual([m.name for m in obj.values()], expected_long)
        self.assertEqual([m for m in list(obj)], expected_short)
        self.assertEqual([(name, m.name) for name, m in obj.items()],
                          zip(expected_short, expected_long))
        self.assertEqual([(name, m.name) for name, m in obj.items()],
                          zip(expected_short, expected_long))
        
        self.assertEqual('module' in obj, True)
        self.assertTrue(obj.get('module'))
        self.assertEqual(obj.get('module').name, 'data.module')
        self.assertEqual(obj['module'].name, 'data.module')
        self.assertEqual(obj.get('whatever'), None)
        self.assertEqual(obj.fullname(), 'data')
        # FIXME: test fullname on a subpackage



class BorgASTNGManagerTC(unittest.TestCase):

    def test_borg(self):
        """test that the ASTNGManager is really a borg, i.e. that two different
        instances has same cache"""
        first_manager = ASTNGManager()
        built = first_manager.astng_from_module_name(BUILTINS_NAME)

        second_manager = ASTNGManager()
        second_built = first_manager.astng_from_module_name(BUILTINS_NAME)
        self.assertTrue(built is second_built)


if __name__ == '__main__':
    unittest.main()

    
