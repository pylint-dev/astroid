from typing import NamedTuple

class Example(NamedTuple):
    class Foo:
        bar = "bar"

# +3: inferred: ClassDef(__astroid_synthetic.Example)
# +2: inferred.getattr(Foo)[0]: ClassDef(namedtuple_nested_class.Example.Foo)
# +1: inferred.getattr(Foo)[0].getattr(bar)[0].inferred: Const('bar')
Example
