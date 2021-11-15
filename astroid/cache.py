# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt
import functools

import wrapt

LRU_CACHES = set()
GENERATOR_CACHES = {}
INFERENCE_CACHE = {}


@wrapt.decorator
def cached_generator(func, instance, args, kwargs):
    node = args[0]
    try:
        result = GENERATOR_CACHES[func, node]
    except KeyError:
        result = GENERATOR_CACHES[func, node] = list(func(*args, **kwargs))
    return iter(result)


def lru_cache(maxsize=128, typed=False):
    if maxsize is None:
        maxsize = 128

    def decorator(f):
        cached_func = functools.lru_cache(maxsize, typed)(f)

        LRU_CACHES.add(cached_func)

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return cached_func(*args, **kwargs)

        return wrapper

    return decorator


def clear_inference_cache():
    INFERENCE_CACHE.clear()


def clear_caches():
    for c in LRU_CACHES:
        c.cache_clear()

    GENERATOR_CACHES.clear()
    INFERENCE_CACHE.clear()
