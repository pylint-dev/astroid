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

from astroid import context as contextmod
from astroid import exceptions
from astroid.interpreter import runtimeabc
from astroid import manager
from astroid.tree import treeabc
from astroid import util


BUILTINS = six.moves.builtins.__name__


def _build_proxy_class(cls_name, builtins):
    # TODO(cpopa): remove this when merging with modular-locals.
    from astroid import raw_building
    proxy = raw_building.build_class(cls_name)
    proxy.parent = builtins
    return proxy


def _function_type(function, builtins):
    if isinstance(function, treeabc.Lambda):
        if function.root().name == BUILTINS:
            cls_name = 'builtin_function_or_method'
        else:
            cls_name = 'function'
    elif isinstance(function, runtimeabc.BoundMethod):
        if six.PY2:
            cls_name = 'instancemethod'
        else:
            cls_name = 'method'
    elif isinstance(function, runtimeabc.UnboundMethod):
        if six.PY2:
            cls_name = 'instancemethod'
        else:
            cls_name = 'function'
    return _build_proxy_class(cls_name, builtins)


def _object_type(node, context=None):
    astroid_manager = manager.AstroidManager()
    builtins = astroid_manager.astroid_cache[BUILTINS]
    context = context or contextmod.InferenceContext()

    for inferred in node.infer(context=context):
        if isinstance(inferred, treeabc.ClassDef):
            yield inferred.metaclass() or builtins.getattr('type')[0]
        elif isinstance(inferred, (treeabc.Lambda, runtimeabc.UnboundMethod)):
            yield _function_type(inferred, builtins)
        elif isinstance(inferred, treeabc.Module):
            yield _build_proxy_class('module', builtins)
        else:
            yield inferred._proxied


def object_type(node, context=None):
    """Obtain the type of the given node

    This is used to implement the ``type`` builtin, which means that it's
    used for inferring type calls, as well as used in a couple of other places
    in the inference. 
    The node will be inferred first, so this function can support all
    sorts of objects, as long as they support inference.
    """

    try:
        types = set(_object_type(node, context))
    except exceptions.InferenceError:
        return util.YES
    if len(types) > 1 or not types:
        return util.YES
    return list(types)[0]
