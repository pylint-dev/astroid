# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt
import os
import tempfile
import unittest

from astroid import modutils


class TestModUtilsRelativePath(unittest.TestCase):

    def setUp(self):
        self.cwd = os.getcwd()

    def _run_relative_path_test(self, target, base, expected):
        if not target or not base:
            result = None
        else:
            base_dir = os.path.join(self.cwd, base)
            target_path = os.path.join(self.cwd, target)
            result = modutils._get_relative_base_path(target_path, base_dir)
        self.assertEqual(result, expected)

    def test_similar_prefixes_no_match(self):

        cases = [
            ("something", "some", None),
            ("some-thing", "some", None),
            ("some2", "some", None),
            ("somedir", "some", None),
            ("some_thing", "some", None),
            ("some.dir", "some", None),
        ]
        for target, base, expected in cases:
            with self.subTest(target=target, base=base):
                self._run_relative_path_test(target, base, expected)

    def test_valid_subdirectories(self):

        cases = [
            ("some/sub", "some", ["sub"]),
            ("some/foo/bar", "some", ["foo", "bar"]),
            ("some/foo-bar", "some", ["foo-bar"]),
            ("some/foo/bar-ext", "some/foo", ["bar-ext"]),
            ("something/sub", "something", ["sub"]),
        ]
        for target, base, expected in cases:
            with self.subTest(target=target, base=base):
                self._run_relative_path_test(target, base, expected)

    def test_path_format_variations(self):

        cases = [
            ("some", "some", []),
            ("some/", "some", []),
            ("../some", "some", None),
        ]

        if os.path.isabs("/abs/path"):
            cases.append(("/abs/path/some", "/abs/path", ["some"]))

        for target, base, expected in cases:
            with self.subTest(target=target, base=base):
                self._run_relative_path_test(target, base, expected)

    def test_case_sensitivity(self):

        cases = [
            ("Some/sub", "some", None if os.path.sep == "/" else ["sub"]),
            ("some/Sub", "some", ["Sub"]),
        ]
        for target, base, expected in cases:
            with self.subTest(target=target, base=base):
                self._run_relative_path_test(target, base, expected)

    def test_special_path_components(self):

        cases = [
            ("some/.hidden", "some", [".hidden"]),
            ("some/with space", "some", ["with space"]),
            ("some/unicode_ø", "some", ["unicode_ø"]),
        ]
        for target, base, expected in cases:
            with self.subTest(target=target, base=base):
                self._run_relative_path_test(target, base, expected)

    def test_nonexistent_paths(self):

        cases = [("nonexistent", "some", None), ("some/sub", "nonexistent", None)]
        for target, base, expected in cases:
            with self.subTest(target=target, base=base):
                self._run_relative_path_test(target, base, expected)

    def test_empty_paths(self):

        cases = [("", "some", None), ("some", "", None), ("", "", None)]
        for target, base, expected in cases:
            with self.subTest(target=target, base=base):
                self._run_relative_path_test(target, base, expected)

    def test_symlink_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = os.path.join(tmpdir, "some")
            os.makedirs(base_dir, exist_ok=True)

            real_file = os.path.join(base_dir, "real.py")
            with open(real_file, "w", encoding="utf-8") as f:
                f.write("# dummy content")

            symlink_path = os.path.join(tmpdir, "symlink.py")
            os.symlink(real_file, symlink_path)

            result = modutils._get_relative_base_path(symlink_path, base_dir)
            self.assertEqual(result, ["real"])


if __name__ == "__main__":
    unittest.main()
