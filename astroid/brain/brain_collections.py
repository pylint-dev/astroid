# Copyright (c) 2016, 2018, 2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2016-2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 Derek Gustafson <degustaf@gmail.com>
# Copyright (c) 2018 Ioana Tagirta <ioana.tagirta@gmail.com>
# Copyright (c) 2019 Hugo van Kemenade <hugovk@users.noreply.github.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/LICENSE
import sys

import astroid

PY39 = sys.version_info >= (3, 9)


def _collections_transform():
    return astroid.parse(
        """
    class defaultdict(dict):
        default_factory = None
        def __missing__(self, key): pass
        def __getitem__(self, key): return default_factory

    """
        + _deque_mock()
        + _ordered_dict_mock()
    )


def _deque_mock():
    base_deque_class = """
    class deque(object):
        maxlen = 0
        def __init__(self, iterable=None, maxlen=None):
            self.iterable = iterable or []
        def append(self, x): pass
        def appendleft(self, x): pass
        def clear(self): pass
        def count(self, x): return 0
        def extend(self, iterable): pass
        def extendleft(self, iterable): pass
        def pop(self): return self.iterable[0]
        def popleft(self): return self.iterable[0]
        def remove(self, value): pass
        def reverse(self): return reversed(self.iterable)
        def rotate(self, n=1): return self
        def __iter__(self): return self
        def __reversed__(self): return self.iterable[::-1]
        def __getitem__(self, index): return self.iterable[index]
        def __setitem__(self, index, value): pass
        def __delitem__(self, index): pass
        def __bool__(self): return bool(self.iterable)
        def __nonzero__(self): return bool(self.iterable)
        def __contains__(self, o): return o in self.iterable
        def __len__(self): return len(self.iterable)
        def __copy__(self): return deque(self.iterable)
        def copy(self): return deque(self.iterable)
        def index(self, x, start=0, end=0): return 0
        def insert(self, x, i): pass
        def __add__(self, other): pass
        def __iadd__(self, other): pass
        def __mul__(self, other): pass
        def __imul__(self, other): pass
        def __rmul__(self, other): pass"""
    if PY39:
        base_deque_class += """
        @classmethod
        def __class_getitem__(self, item): return cls"""
    return base_deque_class


def _ordered_dict_mock():
    base_ordered_dict_class = """
    class OrderedDict(dict):
        def __reversed__(self): return self[::-1]
        def move_to_end(self, key, last=False): pass"""
    if PY39:
        base_ordered_dict_class += """
        @classmethod
        def __class_getitem__(cls, item): return cls"""
    return base_ordered_dict_class


astroid.register_module_extender(astroid.MANAGER, "collections", _collections_transform)


def _looks_like_subscriptable(node: astroid.nodes.ClassDef) -> bool:
    """
    Returns True if the node corresponds to a ClassDef of the Collections.abc module that
    supports subscripting

    :param node: ClassDef node
    """
    if node.qname().startswith("_collections") or node.qname().startswith(
        "collections"
    ):
        try:
            node.getattr("__class_getitem__")
            return True
        except astroid.AttributeInferenceError:
            pass
    return False


CLASS_GET_ITEM_TEMPLATE = """
@classmethod
def __class_getitem__(cls, item):
    return cls
"""


def easy_class_getitem_inference(node, context=None):
    # Here __class_getitem__ exists but is quite a mess to infer thus
    # put an easy inference tip
    func_to_add = astroid.extract_node(CLASS_GET_ITEM_TEMPLATE)
    node.locals["__class_getitem__"] = [func_to_add]


if PY39:
    # Starting with Python39 some objects of the collection module are subscriptable
    # thanks to the __class_getitem__ method but the way it is implemented in
    # _collection_abc makes it difficult to infer. (We would have to handle AssignName inference in the
    # getitem method of the ClassDef class) Instead we put here a mock of the __class_getitem__ method
    astroid.MANAGER.register_transform(
        astroid.nodes.ClassDef, easy_class_getitem_inference, _looks_like_subscriptable
    )
