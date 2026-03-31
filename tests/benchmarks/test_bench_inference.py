# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Benchmarks for astroid inference engine."""

from __future__ import annotations

from astroid import builder, helpers, parse


# -- Simple attribute inference --

ATTR_INFERENCE_CODE = """\
class Foo:
    x = 1
    y = "hello"

foo = Foo()
foo.x  #@
"""


def test_bench_infer_simple_attribute(benchmark):
    """Benchmark inferring a simple attribute access."""
    node = builder.extract_node(ATTR_INFERENCE_CODE)

    def do_infer():
        return list(node.infer())

    benchmark(do_infer)


# -- Function return type inference --

FUNC_RETURN_CODE = """\
def add(a, b):
    return a + b

add(1, 2)  #@
"""


def test_bench_infer_function_call(benchmark):
    """Benchmark inferring the return value of a function call."""
    node = builder.extract_node(FUNC_RETURN_CODE)

    def do_infer():
        return list(node.infer())

    benchmark(do_infer)


# -- Class instantiation inference --

CLASS_INSTANCE_CODE = """\
class MyClass:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

obj = MyClass(42)
obj  #@
"""


def test_bench_infer_class_instance(benchmark):
    """Benchmark inferring a class instance."""
    node = builder.extract_node(CLASS_INSTANCE_CODE)

    def do_infer():
        return list(node.infer())

    benchmark(do_infer)


# -- MRO resolution --

MRO_CODE = """\
class A:
    pass

class B(A):
    pass

class C(A):
    pass

class D(B, C):
    pass

D  #@
"""


def test_bench_infer_mro(benchmark):
    """Benchmark MRO computation on a diamond hierarchy."""
    node = builder.extract_node(MRO_CODE)

    def do_mro():
        cls = next(node.infer())
        return cls.mro()

    benchmark(do_mro)


# -- Scope lookup --

SCOPE_LOOKUP_CODE = """\
x = 1

def outer():
    y = 2
    def inner():
        z = 3
        result = x + y + z
        result  #@
    return inner
"""


def test_bench_infer_scope_lookup(benchmark):
    """Benchmark inference that requires scope chain lookup."""
    node = builder.extract_node(SCOPE_LOOKUP_CODE)

    def do_infer():
        return list(node.infer())

    benchmark(do_infer)


# -- List comprehension inference --

LISTCOMP_CODE = """\
result = [x * 2 for x in range(10)]
result  #@
"""


def test_bench_infer_list_comprehension(benchmark):
    """Benchmark inferring a list comprehension result."""
    node = builder.extract_node(LISTCOMP_CODE)

    def do_infer():
        return list(node.infer())

    benchmark(do_infer)


# -- Standard library module inference --

STDLIB_CODE = """\
import os
os.path.join("a", "b")  #@
"""


def test_bench_infer_stdlib_call(benchmark):
    """Benchmark inferring a standard library function call."""
    node = builder.extract_node(STDLIB_CODE)

    def do_infer():
        return list(node.infer())

    benchmark(do_infer)


# -- safe_infer helper --

SAFE_INFER_CODE = """\
class Config:
    DEBUG = True
    VERSION = "1.0"
    MAX_RETRIES = 3

Config.DEBUG  #@
"""


def test_bench_safe_infer(benchmark):
    """Benchmark the safe_infer helper on attribute access."""
    node = builder.extract_node(SAFE_INFER_CODE)

    def do_safe_infer():
        return helpers.safe_infer(node)

    benchmark(do_safe_infer)
