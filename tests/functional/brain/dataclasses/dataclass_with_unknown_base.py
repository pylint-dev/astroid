# Regression test for dataclasses with unknown base classes.
#
# Reported in https://github.com/pylint-dev/pylint/issues/7418
import dataclasses

from unknown import Unknown


@dataclasses.dataclass
class MyDataclass(Unknown):
    pass

MyDataclass()  # inferred: Instance(dataclass_with_unknown_base.MyDataclass)
