# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt
import pytest

import astroid.cache
from astroid.cache import LRUCache


class TestLRUCache:
    """
    Test astroid.cache.LRUCache
    """

    def test_set_and_get(self):
        """
        Test __setitem__, __getitem__, and __contains__
        """
        cache = LRUCache()
        cache["a"] = 123

        assert cache["a"] == 123
        assert "a" in cache
        assert "b" not in cache

    def test_clear(self):
        """
        Test LRUCache.clear()
        """
        cache = LRUCache()
        cache["c"] = 789

        assert "c" in cache

        cache.clear()

        assert "c" not in cache

    @pytest.fixture
    def reduce_cache_capacity(self):
        """
        A fixture to temporarily decrease the cache capactiy
        """
        astroid.cache.LRU_CACHE_CAPACITY = 3
        yield
        astroid.cache.LRU_CACHE_CAPACITY = 128

    def test_eviction(self, reduce_cache_capacity):
        """
        Test cache eviction behavior
        """
        cache = LRUCache()
        cache["a"] = 1
        cache["b"] = 2
        cache["c"] = 3

        assert "a" in cache
        assert "b" in cache
        assert "c" in cache

        cache["d"] = 3

        # "a" is evicted since it's the least recelty used item
        assert "a" not in cache
        assert "b" in cache
        assert "c" in cache
        assert "d" in cache

        assert cache["b"] == 2
        cache["e"] = 4
        assert "b" in cache
        # "c" is evicted since "b" was recently referenced
        assert "c" not in cache
        assert "d" in cache
        assert "e" in cache

    def test_clear_caches(self):
        """
        Test clear_caches() (global cache flush)
        """
        cache1 = LRUCache()
        cache1["abc"] = 123

        cache2 = LRUCache()
        cache2["def"] = 456

        assert "abc" in cache1
        assert "def" in cache2

        astroid.cache.clear_caches()

        assert "abc" not in cache1
        assert "def" not in cache2
