# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Benchmarks for astroid parsing and tree building."""

from __future__ import annotations

import astroid
from astroid import builder, manager, parse


# -- Small expression parsing --

SIMPLE_EXPRESSION = """\
x = 1 + 2
y = [i for i in range(10)]
z = {k: v for k, v in items.items()}
"""


def test_bench_parse_simple_expression(benchmark):
    """Benchmark parsing a small expression."""
    benchmark(parse, SIMPLE_EXPRESSION)


# -- Module-level parsing --

MODULE_CODE = """\
import os
import sys
from collections import defaultdict
from typing import Any, Optional

CONSTANT = 42
NAMES = ["alice", "bob", "charlie"]


def helper(x: int, y: int = 0) -> int:
    if x > 0:
        return x + y
    return -x + y


class MyClass:
    class_var: int = 10

    def __init__(self, value: int) -> None:
        self.value = value
        self._cache: dict[str, Any] = {}

    def compute(self, factor: int = 1) -> int:
        return self.value * factor

    @property
    def doubled(self) -> int:
        return self.value * 2

    @staticmethod
    def static_method() -> str:
        return "static"

    @classmethod
    def from_string(cls, s: str) -> "MyClass":
        return cls(int(s))


class ChildClass(MyClass):
    def __init__(self, value: int, extra: str) -> None:
        super().__init__(value)
        self.extra = extra

    def compute(self, factor: int = 1) -> int:
        return super().compute(factor) + len(self.extra)


def process_items(items: list[dict[str, Any]]) -> list[str]:
    results = []
    for item in items:
        if "name" in item:
            results.append(item["name"].upper())
    return results
"""


def test_bench_parse_module(benchmark):
    """Benchmark parsing a module with classes, functions, and imports."""
    benchmark(parse, MODULE_CODE)


# -- Complex class hierarchy --

CLASS_HIERARCHY_CODE = """\
from abc import ABC, abstractmethod


class Base(ABC):
    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def validate(self):
        pass


class Mixin:
    def log(self, msg):
        print(msg)


class Intermediate(Base, Mixin):
    def validate(self):
        return True


class Concrete(Intermediate):
    def execute(self):
        self.log("executing")
        return 42

    def validate(self):
        return super().validate() and self.execute() > 0


class Extended(Concrete):
    def execute(self):
        base = super().execute()
        return base * 2
"""


def test_bench_parse_class_hierarchy(benchmark):
    """Benchmark parsing a complex class hierarchy with MRO."""
    benchmark(parse, CLASS_HIERARCHY_CODE)


# -- Decorator and meta-programming patterns --

DECORATOR_CODE = """\
import functools


def retry(max_attempts=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator


def cache_result(func):
    _cache = {}
    @functools.wraps(func)
    def wrapper(*args):
        if args not in _cache:
            _cache[args] = func(*args)
        return _cache[args]
    return wrapper


class Validated:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for key, value in cls.__dict__.items():
            if callable(value) and not key.startswith('_'):
                setattr(cls, key, retry()(value))


@cache_result
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""


def test_bench_parse_decorators(benchmark):
    """Benchmark parsing code with decorators and meta-programming."""
    benchmark(parse, DECORATOR_CODE)


# -- Builder string_build --


def test_bench_builder_string_build(benchmark):
    """Benchmark the AstroidBuilder.string_build method."""
    mgr = manager.AstroidManager()
    b = builder.AstroidBuilder(mgr)
    benchmark(b.string_build, MODULE_CODE)


# -- extract_node --

EXTRACT_CODE = """\
class Foo:
    def bar(self):
        return 42  #@
"""


def test_bench_extract_node(benchmark):
    """Benchmark extract_node for pulling out a specific node."""
    benchmark(builder.extract_node, EXTRACT_CODE)
