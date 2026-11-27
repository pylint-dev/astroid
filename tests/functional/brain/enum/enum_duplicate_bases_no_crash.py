# An enum class with duplicate bases has no resolvable MRO.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/3065
import enum

class C(enum.Enum, enum.Enum):  # inferred: ClassDef(enum_duplicate_bases_no_crash.C)
    pass
