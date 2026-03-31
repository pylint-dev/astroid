# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Benchmarks for the AstroidManager and module utilities."""

from __future__ import annotations

from astroid import manager, modutils


def _fresh_manager():
    """Create a fresh AstroidManager with empty caches."""
    mgr = manager.AstroidManager()
    mgr.clear_cache()
    return mgr


# -- ast_from_module_name (stdlib) --


def test_bench_ast_from_module_name_stdlib(benchmark):
    """Benchmark building AST from a standard library module name."""
    mgr = _fresh_manager()

    def do_build():
        mgr.clear_cache()
        return mgr.ast_from_module_name("collections")

    benchmark(do_build)


# -- ast_from_module_name (small module) --


def test_bench_ast_from_module_name_os_path(benchmark):
    """Benchmark building AST from os.path."""
    mgr = _fresh_manager()

    def do_build():
        mgr.clear_cache()
        return mgr.ast_from_module_name("os.path")

    benchmark(do_build)


# -- ast_from_string --

SAMPLE_CODE = """\
def greet(name: str) -> str:
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, prefix: str = "Hi"):
        self.prefix = prefix

    def greet(self, name: str) -> str:
        return f"{self.prefix}, {name}!"
"""


def test_bench_ast_from_string(benchmark):
    """Benchmark AstroidManager.ast_from_string."""
    mgr = _fresh_manager()
    benchmark(mgr.ast_from_string, SAMPLE_CODE)


# -- modutils: file_from_modpath --


def test_bench_file_from_modpath(benchmark):
    """Benchmark resolving a module path to a file."""
    benchmark(modutils.file_from_modpath, ["os", "path"])


# -- modutils: modpath_from_file --


def test_bench_modpath_from_file(benchmark):
    """Benchmark resolving a file path to a module path."""
    import os

    filepath = os.__file__
    benchmark(modutils.modpath_from_file, filepath)
