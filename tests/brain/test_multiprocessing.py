# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import queue
import sys
import unittest

import astroid
from astroid import builder, nodes

try:
    import multiprocessing  # pylint: disable=unused-import

    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False


@unittest.skipUnless(
    HAS_MULTIPROCESSING,
    "multiprocesing is required for this test, but "
    "on some platforms it is missing "
    "(Jython for instance)",
)
class MultiprocessingBrainTest(unittest.TestCase):
    def test_multiprocessing_module_attributes(self) -> None:
        # Test that module attributes are working,
        # especially on Python 3.4+, where they are obtained
        # from a context.
        module = builder.extract_node(
            """
        import multiprocessing
        """
        )
        assert isinstance(module, nodes.Import)
        module = module.do_import_module("multiprocessing")
        cpu_count = next(module.igetattr("cpu_count"))
        self.assertIsInstance(cpu_count, astroid.BoundMethod)

    def test_module_name(self) -> None:
        module = builder.extract_node(
            """
        import multiprocessing
        multiprocessing.SyncManager()
        """
        )
        inferred_sync_mgr = next(module.infer())
        module = inferred_sync_mgr.root()
        self.assertEqual(module.name, "multiprocessing.managers")

    def test_multiprocessing_manager(self) -> None:
        # Test that we have the proper attributes
        # for a multiprocessing.managers.SyncManager
        module = builder.parse(
            """
        import multiprocessing
        manager = multiprocessing.Manager()
        queue = manager.Queue()
        joinable_queue = manager.JoinableQueue()
        event = manager.Event()
        rlock = manager.RLock()
        lock = manager.Lock()
        bounded_semaphore = manager.BoundedSemaphore()
        condition = manager.Condition()
        barrier = manager.Barrier()
        pool = manager.Pool()
        list = manager.list()
        dict = manager.dict()
        value = manager.Value()
        array = manager.Array()
        namespace = manager.Namespace()
        """
        )
        ast_queue = next(module["queue"].infer())
        self.assertEqual(ast_queue.qname(), f"{queue.__name__}.Queue")

        joinable_queue = next(module["joinable_queue"].infer())
        self.assertEqual(joinable_queue.qname(), f"{queue.__name__}.Queue")

        event = next(module["event"].infer())
        event_name = "threading.Event"
        self.assertEqual(event.qname(), event_name)

        rlock = next(module["rlock"].infer())
        rlock_name = "threading._RLock"
        self.assertEqual(rlock.qname(), rlock_name)

        lock = next(module["lock"].infer())
        lock_name = "threading.lock"
        self.assertEqual(lock.qname(), lock_name)

        bounded_semaphore = next(module["bounded_semaphore"].infer())
        semaphore_name = "threading.BoundedSemaphore"
        self.assertEqual(bounded_semaphore.qname(), semaphore_name)

        pool = next(module["pool"].infer())
        pool_name = "multiprocessing.pool.Pool"
        self.assertEqual(pool.qname(), pool_name)

        for attr in ("list", "dict"):
            obj = next(module[attr].infer())
            self.assertEqual(obj.qname(), f"builtins.{attr}")

        # pypy's implementation of array.__spec__ return None. This causes problems for this inference.
        if not hasattr(sys, "pypy_version_info"):
            array = next(module["array"].infer())
            self.assertEqual(array.qname(), "array.array")

        manager = next(module["manager"].infer())
        # Verify that we have these attributes
        self.assertTrue(manager.getattr("start"))
        self.assertTrue(manager.getattr("shutdown"))
