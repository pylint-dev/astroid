# Copyright (c) 2003-2013 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""
 for the visitors.diadefs module
"""

import unittest


from astroid import nodes, inspector
from astroid.bases import Instance, YES
from astroid.manager import AstroidManager, _silent_no_wrap
from astroid.tests import resources

MANAGER = AstroidManager()

def astroid_wrapper(func, modname):
    return func(modname)


class LinkerTest(resources.SysPathSetup, unittest.TestCase):

    def setUp(self):
        super(LinkerTest, self).setUp()
        self.project = MANAGER.project_from_files(
            [resources.find('data')],
            astroid_wrapper,
            black_list=['joined_strings.py'])
        self.linker = inspector.Linker(self.project)
        self.linker.visit(self.project)

    def test_class_implements(self):
        klass = self.project.get_module('data.clientmodule_test')['Ancestor']
        self.assertTrue(hasattr(klass, 'implements'))
        self.assertEqual(len(klass.implements), 1)
        self.assertTrue(isinstance(klass.implements[0], nodes.Class))
        self.assertEqual(klass.implements[0].name, "Interface")
        klass = self.project.get_module('data.clientmodule_test')['Specialization']
        self.assertTrue(hasattr(klass, 'implements'))
        self.assertEqual(len(klass.implements), 0)

    def test_locals_assignment_resolution(self):
        klass = self.project.get_module('data.clientmodule_test')['Specialization']
        self.assertTrue(hasattr(klass, 'locals_type'))
        type_dict = klass.locals_type
        self.assertEqual(len(type_dict), 2)
        keys = sorted(type_dict.keys())
        self.assertEqual(keys, ['TYPE', 'top'])
        self.assertEqual(len(type_dict['TYPE']), 1)
        self.assertEqual(type_dict['TYPE'][0].value, 'final class')
        self.assertEqual(len(type_dict['top']), 1)
        self.assertEqual(type_dict['top'][0].value, 'class')

    def test_instance_attrs_resolution(self):
        klass = self.project.get_module('data.clientmodule_test')['Specialization']
        self.assertTrue(hasattr(klass, 'instance_attrs_type'))
        type_dict = klass.instance_attrs_type
        self.assertEqual(len(type_dict), 3)
        keys = sorted(type_dict.keys())
        self.assertEqual(keys, ['_id', 'relation', 'toto'])
        self.assertTrue(isinstance(type_dict['relation'][0], Instance), type_dict['relation'])
        self.assertEqual(type_dict['relation'][0].name, 'DoNothing')
        self.assertTrue(isinstance(type_dict['toto'][0], Instance), type_dict['toto'])
        self.assertEqual(type_dict['toto'][0].name, 'Toto')
        self.assertIs(type_dict['_id'][0], YES)


class LinkerTest2(LinkerTest):

    def setUp(self):
        resources.SysPathSetup.setUp(self)
        self.project = MANAGER.project_from_files(
            [resources.find('data')],
            func_wrapper=_silent_no_wrap,
            black_list=['joined_strings.py'])
        self.linker = inspector.Linker(self.project)
        self.linker.visit(self.project)


if __name__ == '__main__':
    unittest.main()
