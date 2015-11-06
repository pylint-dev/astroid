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
#
# The code in this file was originally part of logilab-common, licensed under
# the same license.

import sys
import warnings

import lazy_object_proxy
import six


def reraise(exception):
    '''Reraises an exception with the traceback from the current exception
    block.'''
    six.reraise(type(exception), exception, sys.exc_info()[2])


@object.__new__
class Uninferable(object):
    """Special inference object, which is returned when inference fails."""
    def __repr__(self):
        return 'Uninferable'

    def __getattribute__(self, name):
        if name == 'next':
            raise AttributeError('next method should not be called')
        if name.startswith('__') and name.endswith('__'):
            return object.__getattribute__(self, name)
        return self

    def __call__(self, *args, **kwargs):
        return self


def _instancecheck(cls, other):
    wrapped = cls.__wrapped__
    other_cls = other.__class__
    is_instance_of = wrapped is other_cls or issubclass(other_cls, wrapped)
    warnings.warn("%r is deprecated and slated for removal in astroid "
                  "2.0, use %r instead" % (cls.__class__.__name__,
                                           wrapped.__name__),
                  PendingDeprecationWarning, stacklevel=2)
    return is_instance_of


def proxy_alias(alias_name, node_type):
    """Get a Proxy from the given name to the given node type."""
    proxy = type(alias_name, (lazy_object_proxy.Proxy,),
                 {'__class__': object.__dict__['__class__'],
                  '__instancecheck__': _instancecheck})
    return proxy(lambda: node_type)


# Backwards-compatibility aliases
YES = Uninferable
