# Multiple inheritance with subscriptable typing alias
import typing
# +2: inferred: ClassDef(typing_object_subscriptable_2.Derived)
# +1: inferred.mro: typing_object_subscriptable_2.Derived, typing.Hashable, _collections_abc.Hashable, typing.Iterator, _collections_abc.Iterator, _collections_abc.Iterable, builtins.object
class Derived(typing.Hashable, typing.Iterator[int]):
    pass
