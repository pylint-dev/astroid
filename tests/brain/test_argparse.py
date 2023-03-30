# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from astroid import bases, extract_node, nodes


class TestBrainArgparse:
    @staticmethod
    def test_infer_namespace() -> None:
        func = extract_node(
            """
        import argparse
        def make_namespace():  #@
            return argparse.Namespace(debug=True)
        """
        )
        assert isinstance(func, nodes.FunctionDef)
        inferred = next(func.infer_call_result(func))
        assert isinstance(inferred, bases.Instance)
        assert not func.locals
