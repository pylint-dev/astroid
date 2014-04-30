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

from astroid.node_classes import Assign, Discard, YieldFrom
from astroid.manager import AstroidManager
from astroid.builder import AstroidBuilder
from astroid.scoped_nodes import Class, Function


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

    @require_version('3.3')
    def test_yield_from(self):
        body = dedent("""
        def func():
            yield from iter([1, 2])
        """)
        astroid = self.builder.string_build(body)
        func = astroid.body[0]
        self.assertIsInstance(func, Function)
        yieldfrom_stmt = func.body[0]

        self.assertIsInstance(yieldfrom_stmt, Discard)
        self.assertIsInstance(yieldfrom_stmt.value, YieldFrom)
        self.assertEqual(yieldfrom_stmt.as_string(),
                         'yield from iter([1, 2])')

    @require_version('3.3')
    def test_yield_from_is_generator(self):
        body = dedent("""
        def func():
            yield from iter([1, 2])
        """)
        astroid = self.builder.string_build(body)
        func = astroid.body[0]
        self.assertIsInstance(func, Function)
        self.assertTrue(func.is_generator())

    @require_version('3.3')
    def test_yield_from_as_string(self):
        body = dedent("""
        def func():
            yield from iter([1, 2])
            value = yield from other()
        """)
        astroid = self.builder.string_build(body)
        func = astroid.body[0]
        self.assertEqual(func.as_string().strip(), body.strip())

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

    @require_version('3.0')
    def test_metaclass_yes_leak(self):
        astroid = self.builder.string_build(dedent("""
        # notice `ab` instead of `abc`
        from ab import ABCMeta

        class Meta(metaclass=ABCMeta): pass
        """))
        klass = astroid['Meta']
        self.assertIsNone(klass.metaclass())

    @require_version('3.0')
    def test_metaclass_ancestors(self):
        astroid = self.builder.string_build(dedent("""
        from abc import ABCMeta

        class FirstMeta(metaclass=ABCMeta): pass
        class SecondMeta(metaclass=type):
            pass

        class Simple:
            pass

        class FirstImpl(FirstMeta): pass
        class SecondImpl(FirstImpl): pass
        class ThirdImpl(Simple, SecondMeta):
            pass
        """))
        classes = {
            'ABCMeta': ('FirstImpl', 'SecondImpl'),
            'type': ('ThirdImpl', )
        }
        for metaclass, names in classes.items():
            for name in names:
                impl = astroid[name]
                meta = impl.metaclass()
                self.assertIsInstance(meta, Class)
                self.assertEqual(meta.name, metaclass)
                         
if __name__ == '__main__':
    unittest_main()
