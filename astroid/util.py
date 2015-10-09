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

import importlib
import sys

import lazy_object_proxy
import six

from astroid import exceptions


def lazy_import(module_name):
    return lazy_object_proxy.Proxy(lambda: importlib.import_module(module_name))

def reraise(exception):
    '''Reraises an exception with the traceback from the current exception
    block.'''
    six.reraise(type(exception), exception, sys.exc_info()[2])


@object.__new__
class YES(object):
    """Special inference object, which is returned when inference fails."""
    def __repr__(self):
        return 'YES'

    def __getattribute__(self, name):
        if name == 'next':
            raise AttributeError('next method should not be called')
        if name.startswith('__') and name.endswith('__'):
            return object.__getattribute__(self, name)
        return self

    def __call__(self, *args, **kwargs):
        return self
