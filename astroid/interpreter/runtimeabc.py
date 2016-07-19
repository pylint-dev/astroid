# Copyright (c) 2015-2016 LOGILAB S.A. (Paris, FRANCE)
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER



import abc

import six


@six.add_metaclass(abc.ABCMeta)
class RuntimeObject(object):
    """Class representing an object that is created at runtime

    These objects aren't AST per se, being created by the action
    of the interpreter when the code executes, which is a total
    different step than the AST creation.
    """


class Instance(RuntimeObject):
    """Class representing an instance."""


class ExceptionInstance(Instance):
    pass


class BuiltinInstance(RuntimeObject):
    """Represents an instance of a builtin."""


class Method(RuntimeObject):
    """Base class for methods."""


class UnboundMethod(Method):
    """Class representing an unbound method."""


class BoundMethod(Method):
    """Class representing a bound method."""


class Generator(RuntimeObject):
    """Class representing a Generator."""


class Super(RuntimeObject):
    """Class representing a super proxy."""


class FrozenSet(RuntimeObject):
    """Class representing a frozenset."""


class DictKeys(RuntimeObject):
    """The class of {}.keys."""


class DictValues(RuntimeObject):
    """The class of {}.values."""


class DictItems(RuntimeObject):
    """The class of {}.items()."""
