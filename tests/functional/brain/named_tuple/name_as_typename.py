# Reported in https://github.com/pylint-dev/pylint/issues/7429 as a crash.
import collections
# +1: inferred: ClassDef(__astroid_synthetic.MyTuple)
collections.namedtuple(typename="MyTuple", field_names=["birth_date", "city"])
# +1: inferred: ClassDef(__astroid_synthetic.MyTuple)
collections.namedtuple("MyTuple", field_names=["birth_date", "city"])
collections.namedtuple(["birth_date", "city"], typename="MyTuple")  # inferred: Uninferable
