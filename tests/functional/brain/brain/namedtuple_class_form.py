from typing import NamedTuple

class Example(NamedTuple):
    CLASS_ATTR = "class_attr"
    mything: int

# +3: inferred: Instance(__astroid_synthetic.Example)
# +2: inferred.getattr(CLASS_ATTR)[0]: AssignName(CLASS_ATTR)
# +1: inferred.getattr(CLASS_ATTR)[0].inferred: Const('class_attr')
Example(mything=1)
