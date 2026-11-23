# Multiple inheritance with subscriptable collection class
import collections.abc
# +2: inferred: ClassDef(collections_object_subscriptable_4.Derived)
# +1: inferred.mro: collections_object_subscriptable_4.Derived, _collections_abc.Hashable, _collections_abc.Iterator, _collections_abc.Iterable, builtins.object
class Derived(collections.abc.Hashable, collections.abc.Iterator[int]):
    pass
