# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

""" Caching utilities used in various places."""

import typing
from collections import OrderedDict
from weakref import WeakSet

import wrapt

LRU_CACHE_CAPACITY = 128

K = typing.TypeVar("K")
V = typing.TypeVar("V")


class LRUCache(typing.Generic[K, V]):
    """An LRU cache that keeps track of its instances."""

    instances: "WeakSet[LRUCache[typing.Any, typing.Any]]" = WeakSet()

    def __init__(self) -> None:
        self.cache: typing.OrderedDict[K, V] = OrderedDict()
        LRUCache.instances.add(self)

    def __setitem__(self, key: K, value: V) -> None:
        self.cache[key] = value

        if len(self.cache) > LRU_CACHE_CAPACITY:
            self.cache.popitem(last=False)

    def __getitem__(self, key: K) -> V:
        if key in self.cache:
            self.cache.move_to_end(key)

        return self.cache[key]

    def __contains__(self, key: K) -> bool:
        return key in self.cache

    def clear(self) -> None:
        self.cache.clear()

    @classmethod
    def clear_all(cls) -> None:
        """Clears all LRUCache instances."""
        for cache in cls.instances:
            cache.clear()


F = typing.TypeVar("F", bound=typing.Callable[..., typing.Any])


def lru_cache_astroid(arg: typing.Optional[F] = None) -> F:
    """A decorator to cache the results of a function. Similar to
    functools.lru_cache but uses astroid.cache.LRUCache as its internal cache.
    """
    cache: LRUCache[typing.Tuple[typing.Any, ...], typing.Any] = LRUCache()

    @wrapt.decorator
    def decorator(
        func: F,
        instance: typing.Any,
        args: typing.Tuple[typing.Any, ...],
        kwargs: typing.Dict[typing.Any, typing.Any],
    ) -> typing.Any:
        key: typing.Tuple[typing.Any, ...] = (instance,) + args

        for kv in kwargs:
            key += kv

        if key in cache:
            result = cache[key]
        else:
            result = cache[key] = func(*args, **kwargs)

        return result

    if callable(arg):
        # pylint: disable=no-value-for-parameter
        return typing.cast(F, decorator(arg))

    return typing.cast(F, decorator)


_GENERATOR_CACHE: LRUCache[typing.Any, typing.Any] = LRUCache()


def cached_generator(arg: typing.Optional[F] = None) -> F:
    """A decorator to cache the elements returned by a generator. The input
    generator is consumed and cached as a list.
    """

    @wrapt.decorator
    def decorator(
        func: F,
        instance: typing.Any,
        args: typing.Tuple[typing.Any, ...],
        kwargs: typing.Dict[typing.Any, typing.Any],
    ) -> typing.Any:
        key = func, args[0]

        if key in _GENERATOR_CACHE:
            result = _GENERATOR_CACHE[key]
        else:
            result = _GENERATOR_CACHE[key] = list(func(*args, **kwargs))

        return iter(result)

    if callable(arg):
        # pylint: disable=no-value-for-parameter
        return typing.cast(F, decorator(arg))

    return typing.cast(F, decorator)


def clear_caches() -> None:
    """Clears all caches."""
    LRUCache.clear_all()
