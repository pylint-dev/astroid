# copyright 2003-2015 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
