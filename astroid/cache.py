# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

""" Caching utilities used in various places."""


from collections import OrderedDict
from weakref import WeakSet

import wrapt

LRU_CACHE_CAPACITY = 128


class LRUCache:
    """An LRU cache that keeps track of its instances."""

    instances = WeakSet()

    def __init__(self):
        self.cache = OrderedDict()
        LRUCache.instances.add(self)

    def __setitem__(self, key, value):
        self.cache[key] = value

        if len(self.cache) > LRU_CACHE_CAPACITY:
            self.cache.popitem(last=False)

    def __getitem__(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)

        return self.cache[key]

    def __contains__(self, key):
        return key in self.cache

    def clear(self):
        self.cache.clear()

    @classmethod
    def clear_all(cls):
        """Clears all LRUCache instances."""
        for cache in cls.instances:
            cache.clear()


def lru_cache(arg=None):
    """A decorator to cache the results of a function. Similar to
    functools.lru_cache but uses astroid.cache.LRUCache as its internal cache.
    """
    cache = LRUCache()

    @wrapt.decorator
    def decorator(func, instance, args, kwargs):
        key = (instance,) + args

        for kv in kwargs:
            key += kv

        if key in cache:
            result = cache[key]
        else:
            result = cache[key] = func(*args, **kwargs)

        return result

    if callable(arg):
        # pylint: disable=no-value-for-parameter
        return decorator(arg)

    return decorator


_GENERATOR_CACHE = LRUCache()


def cached_generator(arg=None):
    """A decorator to cache the elements returned by a generator. The input
    generator is consumed and cached as a list.
    """

    @wrapt.decorator
    def decorator(func, instance, args, kwargs):
        key = func, args[0]

        if key in _GENERATOR_CACHE:
            result = _GENERATOR_CACHE[key]
        else:
            result = _GENERATOR_CACHE[key] = list(func(*args, **kwargs))

        return iter(result)

    if callable(arg):
        # pylint: disable=no-value-for-parameter
        return decorator(arg)

    return decorator


def clear_caches():
    """Clears all caches."""
    LRUCache.clear_all()
