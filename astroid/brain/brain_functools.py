# Copyright (c) 2016 LOGILAB S.A. (Paris, FRANCE)
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""Astroid hooks for understanding functools library module."""

import astroid
from astroid import BoundMethod
from astroid import extract_node
from astroid import helpers
from astroid.interpreter import objectmodel
from astroid import MANAGER


LRU_CACHE = 'functools.lru_cache'


class LruWrappedModel(objectmodel.FunctionModel):
    """Special attribute model for functions decorated with functools.lru_cache.

    The said decorators patches at decoration time some functions onto
    the decorated function.
    """

    @property
    def py__wrapped__(self):
        return self._instance

    @property
    def pycache_info(self):
        cache_info = extract_node('''
        from functools import _CacheInfo
        _CacheInfo(0, 0, 0, 0)
        ''')
        class CacheInfoBoundMethod(BoundMethod):
            def infer_call_result(self, caller, context=None):
                yield helpers.safe_infer(cache_info)

        return CacheInfoBoundMethod(proxy=self._instance, bound=self._instance)

    @property
    def pycache_clear(self):
        node = extract_node('''def cache_clear(): pass''')
        return BoundMethod(proxy=node, bound=self._instance.parent.scope())



class LruWrappedFunctionDef(astroid.FunctionDef):
    special_attributes = LruWrappedModel()


def _transform_lru_cache(node, context=None):
    # TODO: this needs the zipper, because the new node's attributes
    # will still point to the old node.
    new_func = LruWrappedFunctionDef(name=node.name, doc=node.name,
                                     lineno=node.lineno, col_offset=node.col_offset,
                                     parent=node.parent)
    new_func.postinit(node.args, node.body, node.decorators, node.returns)
    return new_func


def _looks_like_lru_cache(node):
    """Check if the given function node is decorated with lru_cache."""
    if not node.decorators:
        return False

    for decorator in node.decorators.nodes:
        if not isinstance(decorator, astroid.Call):
            continue

        func = helpers.safe_infer(decorator.func)
        if func in (None, astroid.Uninferable):
            continue

        if isinstance(func, astroid.FunctionDef) and func.qname() == LRU_CACHE:
            return True
    return False


MANAGER.register_transform(astroid.FunctionDef, _transform_lru_cache,
                           _looks_like_lru_cache)
