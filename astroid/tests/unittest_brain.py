# Copyright 2013 Google Inc. All Rights Reserved.
#
# This file is part of astroid.
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
"""Tests for basic functionality in astroid.brain."""
import sys
import unittest
from textwrap import dedent

import six

from astroid import MANAGER
from astroid import bases
from astroid import nodes
from astroid import test_utils
from astroid.builder import AstroidBuilder
import astroid


try:
    import nose # pylint: disable=unused-import
    HAS_NOSE = True
except ImportError:
    HAS_NOSE = False

try:
    import multiprocessing # pylint: disable=unused-import
    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False


class HashlibTest(unittest.TestCase):
    def test_hashlib(self):
        """Tests that brain extensions for hashlib work."""
        hashlib_module = MANAGER.ast_from_module_name('hashlib')
        for class_name in ['md5', 'sha1']:
            class_obj = hashlib_module[class_name]
            self.assertIn('update', class_obj)
            self.assertIn('digest', class_obj)
            self.assertIn('hexdigest', class_obj)
            self.assertIn('block_size', class_obj)
            self.assertIn('digest_size', class_obj)
            self.assertEqual(len(class_obj['__init__'].args.args), 2)
            self.assertEqual(len(class_obj['__init__'].args.defaults), 1)
            self.assertEqual(len(class_obj['update'].args.args), 2)
            self.assertEqual(len(class_obj['digest'].args.args), 1)
            self.assertEqual(len(class_obj['hexdigest'].args.args), 1)


class NamedTupleTest(unittest.TestCase):
    def test_namedtuple_base(self):
        klass = test_utils.extract_node("""
        from collections import namedtuple

        class X(namedtuple("X", ["a", "b", "c"])):
           pass
        """)
        self.assertEqual(
            [anc.name for anc in klass.ancestors()],
            ['X', 'tuple', 'object'])
        for anc in klass.ancestors():
            self.assertFalse(anc.parent is None)

    def test_namedtuple_inference(self):
        klass = test_utils.extract_node("""
        from collections import namedtuple

        name = "X"
        fields = ["a", "b", "c"]
        class X(namedtuple(name, fields)):
           pass
        """)
        for base in klass.ancestors():
            if base.name == 'X':
                break
        self.assertSetEqual({"a", "b", "c"}, set(base.instance_attrs))

    def test_namedtuple_inference_failure(self):
        klass = test_utils.extract_node("""
        from collections import namedtuple

        def foo(fields):
           return __(namedtuple("foo", fields))
        """)
        self.assertIs(bases.YES, next(klass.infer()))


    @unittest.skipIf(sys.version_info[0] > 2,
                     'namedtuple inference is broken on Python 3')
    def test_namedtuple_advanced_inference(self):
        # urlparse return an object of class ParseResult, which has a
        # namedtuple call and a mixin as base classes
        result = test_utils.extract_node("""
        import urlparse

        result = __(urlparse.urlparse('gopher://'))
        """)
        instance = next(result.infer())
        self.assertEqual(len(instance.getattr('scheme')), 1)
        self.assertEqual(len(instance.getattr('port')), 1)
        with self.assertRaises(astroid.NotFoundError):
            instance.getattr('foo')


class ModuleExtenderTest(unittest.TestCase):
    def testExtensionModules(self):
        for extender, _ in MANAGER.transforms[nodes.Module]:
            n = nodes.Module('__main__', None)
            extender(n)


@unittest.skipUnless(HAS_NOSE, "This test requires nose library.")
class NoseBrainTest(unittest.TestCase):

    def test_nose_tools(self):
        methods = test_utils.extract_node("""
        from nose.tools import assert_equal
        from nose.tools import assert_true
        assert_equal = assert_equal #@
        assert_true = assert_true #@
        """)

        assert_equal = next(methods[0].value.infer())
        assert_true = next(methods[1].value.infer())

        self.assertIsInstance(assert_equal, astroid.BoundMethod)
        self.assertIsInstance(assert_true, astroid.BoundMethod)
        self.assertEqual(assert_equal.qname(),
                         'unittest.case.TestCase.assertEqual')
        self.assertEqual(assert_true.qname(),
                         'unittest.case.TestCase.assertTrue')


@unittest.skipUnless(HAS_MULTIPROCESSING,
                     'multiprocesing is required for this test, but '
                     'on some platforms it is missing '
                     '(Jython for instance)')
class MultiprocessingBrainTest(unittest.TestCase):

    def test_multiprocessing_module_attributes(self):
        # Test that module attributes are working,
        # especially on Python 3.4+, where they are obtained
        # from a context.
        module = test_utils.extract_node("""
        import multiprocessing
        """)        
        module = module.do_import_module('multiprocessing')
        cpu_count = next(module.igetattr('cpu_count'))
        if six.PY2:
            self.assertIsInstance(cpu_count, nodes.Function)
        else:
            self.assertIsInstance(cpu_count, astroid.BoundMethod)

    def test_multiprocessing_manager(self):
        # Test that we have the proper attributes
        # for a multiprocessing.managers.SyncManager
        module = AstroidBuilder().string_build(dedent("""
        import multiprocessing
        manager = multiprocessing.Manager()
        queue = manager.Queue()
        joinable_queue = manager.JoinableQueue()
        event = manager.Event()
        rlock = manager.RLock()
        bounded_semaphore = manager.BoundedSemaphore()
        condition = manager.Condition()
        barrier = manager.Barrier()
        pool = manager.Pool()
        list = manager.list()
        dict = manager.dict()
        value = manager.Value()
        array = manager.Array()
        namespace = manager.Namespace()
        """))
        queue = next(module['queue'].infer())
        self.assertEqual(queue.qname(),
                         "{}.Queue".format(six.moves.queue.__name__))

        joinable_queue = next(module['joinable_queue'].infer())
        self.assertEqual(joinable_queue.qname(),
                         "{}.Queue".format(six.moves.queue.__name__))

        event = next(module['event'].infer())
        event_name = "threading.{}".format("Event" if six.PY3 else "_Event")
        self.assertEqual(event.qname(), event_name)

        rlock = next(module['rlock'].infer())
        rlock_name = "threading._RLock"
        self.assertEqual(rlock.qname(), rlock_name)

        bounded_semaphore = next(module['bounded_semaphore'].infer())
        semaphore_name = "threading.{}".format(
            "BoundedSemaphore" if six.PY3 else "_BoundedSemaphore")
        self.assertEqual(bounded_semaphore.qname(), semaphore_name)

        pool = next(module['pool'].infer())
        pool_name = "multiprocessing.pool.Pool"
        self.assertEqual(pool.qname(), pool_name)

        for attr in ('list', 'dict'):
            obj = next(module[attr].infer())
            self.assertEqual(obj.qname(),
                             "{}.{}".format(bases.BUILTINS, attr))

        array = next(module['array'].infer())
        self.assertEqual(array.qname(), "array.array")


if __name__ == '__main__':
    unittest.main()
