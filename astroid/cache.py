# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from collections import OrderedDict
from weakref import WeakSet

import wrapt

LRU_CACHE_CAPACITY = 128
GENERATOR_CACHES = {}


class LRUCache:
    instances = WeakSet()

    def __init__(self):
        self.cache = OrderedDict()
        type(self).instances.add(self)

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
        for cache in cls.instances:
            cache.clear()


def lru_cache():
    cache = LRUCache()

    @wrapt.decorator
    def decorator(func, instance, args, kwargs):
        key = (instance,) + args

        for kv in kwargs:
            key += kv

        if key in cache:
            return cache[key]

        result = cache[key] = func(*args, **kwargs)

        return result

    return decorator


@wrapt.decorator
def cached_generator(func, instance, args, kwargs):
    node = args[0]
    try:
        result = GENERATOR_CACHES[func, node]
    except KeyError:
        result = GENERATOR_CACHES[func, node] = list(func(*args, **kwargs))
    return iter(result)


def clear_caches():
    LRUCache.clear_all()
    GENERATOR_CACHES.clear()
