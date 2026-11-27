# A chained assignment whose target is an attribute names no member.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/3257
import enum

class C(enum.Enum):  # inferred: ClassDef(enum_chained_assignment_attribute_target_no_crash.C)
    x = a.b = 1
