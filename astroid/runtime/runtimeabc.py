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


class UnboundMethod(RuntimeObject):
    """Class representing an unbound method."""


class BoundMethod(UnboundMethod):
    """Class representing a bound method."""


class Generator(RuntimeObject):
    """Class representing a Generator."""
