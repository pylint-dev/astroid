# Regression test for https://github.com/pylint-dev/pylint/issues/5935
import six
from enum import Enum, EnumMeta

class PetEnumPy2Metaclass(six.with_metaclass(EnumMeta, Enum)):  # local_attr_ancestors('DOG'):
    DOG = "dog"
