# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.
"""this module contains exceptions used in the astroid library
"""
from astroid import util


class AstroidError(Exception):
    """base exception class for all astroid related exceptions

    AstroidError and its subclasses are structured, intended to hold
    objects representing state when the exception is thrown.  Field
    values are passed to the constructor as keyword-only arguments.
    Each subclass has its own set of standard fields, but use your
    best judgment to decide whether a specific exception instance
    needs more or fewer fields for debugging.  Field values may be
    used to lazily generate the error message: self.message.format()
    will be called with the field names and values supplied as keyword
    arguments.
    """
    def __init__(self, message='', **kws):
        self.message = message
        for key, value in kws.items():
            setattr(self, key, value)

    def __str__(self):
        return self.message.format(**vars(self))


class AstroidBuildingError(AstroidError):
    """exception class when we are unable to build an astroid representation

    Standard attributes:
        modname: Name of the module that AST construction failed for.
        error: Exception raised during construction.
    """

    def __init__(self, message='Failed to import module {modname}.', **kws):
        super(AstroidBuildingError, self).__init__(message, **kws)


class AstroidImportError(AstroidBuildingError):
    """Exception class used when a module can't be imported by astroid."""


class TooManyLevelsError(AstroidImportError):
    """Exception class which is raised when a relative import was beyond the top-level.

    Standard attributes:
        level: The level which was attempted.
        name: the name of the module on which the relative import was attempted.
    """
    level = None
    name = None

    def __init__(self, message='Relative import with too many levels '
                               '({level}) for module {name!r}', **kws):
        super(TooManyLevelsError, self).__init__(message, **kws)


class AstroidSyntaxError(AstroidBuildingError):
    """Exception class used when a module can't be parsed."""


class NoDefault(AstroidError):
    """raised by function's `default_value` method when an argument has
    no default value

    Standard attributes:
        func: Function node.
        name: Name of argument without a default.
    """
    func = None
    name = None

    def __init__(self, message='{func!r} has no default for {name!r}.', **kws):
        super(NoDefault, self).__init__(message, **kws)


class ResolveError(AstroidError):
    """Base class of astroid resolution/inference error.

    ResolveError is not intended to be raised.

    Standard attributes:
        context: InferenceContext object.
    """
    context = None


class MroError(ResolveError):
    """Error raised when there is a problem with method resolution of a class.

    Standard attributes:
        mros: A sequence of sequences containing ClassDef nodes.
        cls: ClassDef node whose MRO resolution failed.
        context: InferenceContext object.
    """
    mros = ()
    cls = None

    def __str__(self):
        mro_names = ", ".join("({})".format(", ".join(b.name for b in m))
                              for m in self.mros)
        return self.message.format(mros=mro_names, cls=self.cls)


class DuplicateBasesError(MroError):
    """Error raised when there are duplicate bases in the same class bases."""


class InconsistentMroError(MroError):
    """Error raised when a class's MRO is inconsistent."""


class SuperError(ResolveError):

    """Error raised when there is a problem with a super call.

    Standard attributes:
        super_: The Super instance that raised the exception.
        context: InferenceContext object.
    """
    super_ = None

    def __str__(self):
        return self.message.format(**vars(self.super_))


class InferenceError(ResolveError):
    """raised when we are unable to infer a node

    Standard attributes:
        node: The node inference was called on.
        context: InferenceContext object.
    """
    node = None
    context = None

    def __init__(self, message='Inference failed for {node!r}.', **kws):
        super(InferenceError, self).__init__(message, **kws)


# Why does this inherit from InferenceError rather than ResolveError?
# Changing it causes some inference tests to fail.
class NameInferenceError(InferenceError):
    """Raised when a name lookup fails, corresponds to NameError.

    Standard attributes:
        name: The name for which lookup failed, as a string.
        scope: The node representing the scope in which the lookup occurred.
        context: InferenceContext object.
    """
    name = None
    scope = None

    def __init__(self, message='{name!r} not found in {scope!r}.', **kws):
        super(NameInferenceError, self).__init__(message, **kws)


class AttributeInferenceError(ResolveError):
    """Raised when an attribute lookup fails, corresponds to AttributeError.

    Standard attributes:
        target: The node for which lookup failed.
        attribute: The attribute for which lookup failed, as a string.
        context: InferenceContext object.
    """
    target = None
    attribute = None

    def __init__(self, message='{attribute!r} not found on {target!r}.', **kws):
        super(AttributeInferenceError, self).__init__(message, **kws)


class UseInferenceDefault(Exception):
    """exception to be raised in custom inference function to indicate that it
    should go back to the default behaviour
    """

class NotSupportedError(AstroidError):
    """Exception raised whenever a capability is accessed on a node
    which doesn't provide it.
    """


class UnaryOperationNotSupportedError(NotSupportedError):
    """Internal exception raised by the inference when an object does not
    suport unary operands.
    """


class BinaryOperationNotSupportedError(NotSupportedError):
    """Internal exception raised by the inference when an object does
    not support binary operations.
    """


# Backwards-compatibility aliases
OperationError = util.BadOperationMessage
UnaryOperationError = util.BadUnaryOperationMessage
BinaryOperationError = util.BadBinaryOperationMessage

SuperArgumentTypeError = SuperError
UnresolvableName = NameInferenceError
NotFoundError = AttributeInferenceError
