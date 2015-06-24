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

"""
Various helper utilities.
"""

import six

from astroid import bases
from astroid import exceptions
from astroid import manager
from astroid import raw_building
from astroid import scoped_nodes


BUILTINS = six.moves.builtins.__name__


def _build_proxy_class(cls_name, builtins):
    proxy = raw_building.build_class(cls_name)
    proxy.parent = builtins
    return proxy


def _function_type(function, builtins):
    if isinstance(function, scoped_nodes.Lambda):
        if function.root().name == BUILTINS:
            cls_name = 'builtin_function_or_method'
        else:
            cls_name = 'function'
    elif isinstance(function, bases.BoundMethod):
        if six.PY2:
            cls_name = 'instancemethod'
        else:
            cls_name = 'method'
    elif isinstance(function, bases.UnboundMethod):
        if six.PY2:
            cls_name = 'instancemethod'
        else:
            cls_name = 'function'
    return _build_proxy_class(cls_name, builtins)


def _object_type(node, context=None):
    astroid_manager = manager.AstroidManager()
    builtins = astroid_manager.astroid_cache[BUILTINS]
    context = context or bases.InferenceContext()

    for inferred in node.infer(context=context):
        if isinstance(inferred, scoped_nodes.Class):
            if inferred.newstyle:
                metaclass = inferred.metaclass()
                if metaclass:
                    yield metaclass
                    continue
            yield builtins.getattr('type')[0]
        elif isinstance(inferred, (scoped_nodes.Lambda, bases.UnboundMethod)):
            yield _function_type(inferred, builtins)
        elif isinstance(inferred, scoped_nodes.Module):
            yield _build_proxy_class('module', builtins)
        else:
            yield inferred._proxied


def object_type(node, context=None):
    """Obtain the type of the given node

    The node will be inferred first, so this function can support all
    sorts of objects, as long as they support inference. It will try to
    retrieve the Python type, as returned by the builtin `type`.
    """

    try:
        types = set(_object_type(node, context))
    except exceptions.InferenceError:
        return bases.YES
    if len(types) > 1:
        return bases.YES
    return list(types)[0]
