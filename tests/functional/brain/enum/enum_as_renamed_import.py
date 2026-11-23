# Originally reported in https://github.com/pylint-dev/pylint/issues/5776.
from enum import Enum as PyEnum
class MyEnum(PyEnum):
    ENUM_KEY = "enum_value"
# +2: inferred: Instance(enum_as_renamed_import.MyEnum.ENUM_KEY)
# +1: inferred._proxied.name: 'ENUM_KEY'
MyEnum.ENUM_KEY
