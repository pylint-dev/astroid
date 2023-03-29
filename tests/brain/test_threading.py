# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

import astroid
from astroid import builder
from astroid.bases import Instance


class ThreadingBrainTest(unittest.TestCase):
    def test_lock(self) -> None:
        lock_instance = builder.extract_node(
            """
        import threading
        threading.Lock()
        """
        )
        inferred = next(lock_instance.infer())
        self.assert_is_valid_lock(inferred)

        acquire_method = inferred.getattr("acquire")[0]
        parameters = [param.name for param in acquire_method.args.args[1:]]
        assert parameters == ["blocking", "timeout"]

        assert inferred.getattr("locked")

    def test_rlock(self) -> None:
        self._test_lock_object("RLock")

    def test_semaphore(self) -> None:
        self._test_lock_object("Semaphore")

    def test_boundedsemaphore(self) -> None:
        self._test_lock_object("BoundedSemaphore")

    def _test_lock_object(self, object_name: str) -> None:
        lock_instance = builder.extract_node(
            f"""
        import threading
        threading.{object_name}()
        """
        )
        inferred = next(lock_instance.infer())
        self.assert_is_valid_lock(inferred)

    def assert_is_valid_lock(self, inferred: Instance) -> None:
        self.assertIsInstance(inferred, astroid.Instance)
        self.assertEqual(inferred.root().name, "threading")
        for method in ("acquire", "release", "__enter__", "__exit__"):
            self.assertIsInstance(next(inferred.igetattr(method)), astroid.BoundMethod)
