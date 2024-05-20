# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

from astroid import MANAGER
from astroid.nodes.scoped_nodes import ClassDef


class HashlibTest(unittest.TestCase):
    def _assert_hashlib_class(self, class_obj: ClassDef) -> None:
        self.assertIn("update", class_obj)
        self.assertIn("digest", class_obj)
        self.assertIn("hexdigest", class_obj)
        self.assertIn("block_size", class_obj)
        self.assertIn("digest_size", class_obj)
        # usedforsecurity was added in Python 3.9, see 8e7174a9
        self.assertEqual(len(class_obj["__init__"].args.args), 3)
        self.assertEqual(len(class_obj["__init__"].args.defaults), 2)
        self.assertEqual(len(class_obj["update"].args.args), 2)

    def test_hashlib(self) -> None:
        """Tests that brain extensions for hashlib work."""
        hashlib_module = MANAGER.ast_from_module_name("hashlib")
        for class_name in (
            "md5",
            "sha1",
            "sha224",
            "sha256",
            "sha384",
            "sha512",
            "sha3_224",
            "sha3_256",
            "sha3_384",
            "sha3_512",
        ):
            class_obj = hashlib_module[class_name]
            self._assert_hashlib_class(class_obj)
            self.assertEqual(len(class_obj["digest"].args.args), 1)
            self.assertEqual(len(class_obj["hexdigest"].args.args), 1)

    def test_shake(self) -> None:
        """Tests that the brain extensions for the hashlib shake algorithms work."""
        hashlib_module = MANAGER.ast_from_module_name("hashlib")
        for class_name in ("shake_128", "shake_256"):
            class_obj = hashlib_module[class_name]
            self._assert_hashlib_class(class_obj)
            self.assertEqual(len(class_obj["digest"].args.args), 2)
            self.assertEqual(len(class_obj["hexdigest"].args.args), 2)

    def test_blake2(self) -> None:
        """Tests that the brain extensions for the hashlib blake2 hash functions work."""
        hashlib_module = MANAGER.ast_from_module_name("hashlib")
        for class_name in ("blake2b", "blake2s"):
            class_obj = hashlib_module[class_name]
            self.assertEqual(len(class_obj["__init__"].args.args), 2)
            self.assertEqual(len(class_obj["digest"].args.args), 1)
            self.assertEqual(len(class_obj["hexdigest"].args.args), 1)
