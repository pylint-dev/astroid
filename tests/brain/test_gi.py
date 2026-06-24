# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import unittest

try:
    import gi  # pylint: disable=unused-import

    HAS_GI = True
except ImportError:
    HAS_GI = False

from astroid import builder, nodes, typing


class _Param:
    def __init__(
        self,
        name: str,
        *,
        argtype: str | None = None,
        default: str | None = None,
    ):
        self.name = name
        self.type = argtype
        self.default = default


@unittest.skipUnless(HAS_GI, "This test requires the gobject introspection library.")
class GiBrainClassificationTest(unittest.TestCase):
    """Test that gi functions are correctly classified."""

    def _inferred_gi_symbol(self, namespace, version, symbol):
        node = builder.extract_node(f"""
        import gi

        gi.require_version("{namespace}", "{version}")
        from gi.repository import {namespace}
        {namespace}.{symbol}
        """)
        return node.inferred()

    def _check_class_and_signature(
        self,
        inferred: typing.InferenceResult,
        args: list[_Param],
        ret: None | str = None,
        is_method: bool = False,
    ):
        funcdef = inferred.frame()
        self.assertIsInstance(funcdef, nodes.FunctionDef)

        def_name = "Method" if is_method else "Function"
        class_type = "builtins.instancemethod" if is_method else "builtins.function"

        # check classifcation
        self.assertEqual(
            inferred.pytype(),
            class_type,
            f"{def_name} is not classified as '{class_type}'",
        )

        # check number of arguments
        self.assertEqual(
            len(args),
            len(funcdef.argnames()),
            f"{def_name} has unexpected number of arguments",
        )

        # check argument names, types, and default values
        default_pos = -1
        for arg_pos, arg in enumerate(args):
            self.assertEqual(
                funcdef.argnames()[arg_pos],
                arg.name,
                f"{def_name} does not accept '{arg.name}' as argument{arg_pos}",
            )

            if arg.type is None:
                self.assertIsNone(funcdef.args.annotations[arg_pos])
            else:
                self.assertGreaterEqual(len(funcdef.args.annotations), arg_pos + 1)
                self.assertIsNotNone(funcdef.args.annotations[arg_pos])
                self.assertEqual(
                    funcdef.args.annotations[arg_pos].as_string(),
                    arg.type,
                    f"{def_name}'s argument{arg_pos} is not of type '{arg.type}'",
                )

            if arg.default is not None:
                default_pos += 1
                self.assertGreaterEqual(len(funcdef.args.defaults), default_pos + 1)
                self.assertIsNotNone(funcdef.args.defaults[default_pos])
                self.assertEqual(
                    funcdef.args.defaults[default_pos].as_string(),
                    arg.default,
                    f"{def_name} argument{arg_pos}'s default value is not '{arg.default}'",
                )

        # check return type
        if ret is None:
            self.assertIsNone(funcdef.returns)
        else:
            self.assertIsNotNone(funcdef.returns)
            self.assertEqual(
                funcdef.returns.as_string(),
                ret,
                f"{def_name}'s return type is not of type '{ret}'",
            )

    def test_gi_function_classification(self):
        """Test that global functions are correctly classified without the 'self' argument."""
        inferred = self._inferred_gi_symbol("GLib", "2.0", "get_tmp_dir")
        self.assertEqual(len(inferred), 1)
        self._check_class_and_signature(inferred[0], args=[], ret="str")

    def test_gi_function_classification_with_arguments(self):
        """Test that global functions are correctly classified with function arguments."""
        inferred = self._inferred_gi_symbol("GLib", "2.0", "ascii_strdown")
        self.assertEqual(len(inferred), 1)
        self._check_class_and_signature(
            inferred[0],
            args=[
                _Param("str", argtype="str"),
                _Param("len", argtype="int"),
            ],
            ret="str",
        )

    def test_gi_method_classification(self):
        """Test that methods are correctly classified and accept 'self' as first argument."""
        inferred = self._inferred_gi_symbol("GLib", "2.0", "String.append")
        self.assertEqual(len(inferred), 1)
        self._check_class_and_signature(
            inferred[0],
            args=[
                _Param("self"),
                _Param("val", argtype="str"),
            ],
            ret="gi.repository.GLib.String",
            is_method=True,
        )

    def test_gi_method_classification_with_default_values(self):
        """Test that methods are correctly classified and accept arguments with default values."""
        inferred = self._inferred_gi_symbol("Gtk", "3.0", "Table.attach")
        self.assertEqual(len(inferred), 1)
        self._check_class_and_signature(
            inferred[0],
            args=[
                _Param("self"),
                _Param("child"),
                _Param("left_attach"),
                _Param("right_attach"),
                _Param("top_attach"),
                _Param("bottom_attach"),
                _Param(  # expect replacement of <AttachOptions.EXPAND|FILL: 5> by None
                    "xoptions", default="None"
                ),
                _Param(  # expect replacement of <AttachOptions.EXPAND|FILL: 5> by None
                    "yoptions", default="None"
                ),
                _Param("xpadding", default="0"),
                _Param("ypadding", default="0"),
            ],
            is_method=True,
        )
