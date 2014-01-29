# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
from textwrap import dedent

from logilab.common.testlib import TestCase, unittest_main, require_version

from astroid.node_classes import Assign
from astroid.manager import AstroidManager
from astroid.builder import AstroidBuilder
from astroid.scoped_nodes import Class


class Python3TC(TestCase):
    def setUp(self):
        self.manager = AstroidManager()
        self.builder = AstroidBuilder(self.manager)
        self.manager.astroid_cache.clear()

    @require_version('3.0')
    def test_starred_notation(self):
        astroid = self.builder.string_build("*a, b = [1, 2, 3]", 'test', 'test')

        # Get the star node
        node = next(next(next(astroid.get_children()).get_children()).get_children())

        self.assertTrue(isinstance(node.ass_type(), Assign))

    # metaclass tests

    @require_version('3.0')
    def test_simple_metaclass(self):
        astroid = self.builder.string_build("class Test(metaclass=type): pass")
        klass = astroid.body[0]

        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, Class)
        self.assertEqual(metaclass.name, 'type')

    @require_version('3.0')
    def test_metaclass_error(self):
        astroid = self.builder.string_build("class Test(metaclass=typ): pass")
        klass = astroid.body[0]
        self.assertFalse(klass.metaclass())

    @require_version('3.0')
    def test_metaclass_imported(self): 
        astroid = self.builder.string_build(dedent("""
        from abc import ABCMeta 
        class Test(metaclass=ABCMeta): pass"""))
        klass = astroid.body[1]

        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, Class)
        self.assertEqual(metaclass.name, 'ABCMeta')       

    @require_version('3.0')
    def test_as_string(self):
        body = dedent("""
        from abc import ABCMeta 
        class Test(metaclass=ABCMeta): pass""")
        astroid = self.builder.string_build(body)
        klass = astroid.body[1]

        self.assertEqual(klass.as_string(), 
                         '\n\nclass Test(metaclass=ABCMeta):\n    pass\n')

    @require_version('3.0')
    def test_old_syntax_works(self):
        astroid = self.builder.string_build(dedent("""
        class Test:
            __metaclass__ = type
        class SubTest(Test): pass
        """))
        klass = astroid['SubTest']
        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, Class)
        self.assertEqual(metaclass.name, 'type')
                         
if __name__ == '__main__':
    unittest_main()
