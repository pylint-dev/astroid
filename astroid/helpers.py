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
import types

import six

from astroid import context as contextmod
from astroid import exceptions
from astroid.interpreter import runtimeabc
from astroid import manager
from astroid.tree import treeabc
from astroid import util


def _object_type(node, context=None):
    context = context or contextmod.InferenceContext()

    for inferred in node.infer(context=context):
        if isinstance(inferred, treeabc.ClassDef):
            if inferred.newstyle:
                metaclass = inferred.metaclass()
                if metaclass:
                    yield metaclass
                    continue
            yield raw_building.builtins_ast.getattr('type')[0]
        elif isinstance(inferred, (treeabc.Lambda, runtimeabc.UnboundMethod)):
            if isinstance(inferred, treeabc.Lambda):
                if inferred.root() is raw_building.builtins_ast:
                    yield raw_building.builtins_ast[types.BuiltinFunctionType.__name__]
                else:
                    yield raw_building.builtins_ast[types.FunctionType.__name__]
            elif isinstance(inferred, runtimeabc.BoundMethod):
                yield raw_building.builtins_ast[types.MethodType.__name__]
            elif isinstance(inferred, runtimeabc.UnboundMethod):
                if six.PY2:
                    yield raw_building.builtins_ast[types.MethodType.__name__]
                else:
                    yield raw_building.builtins_ast[types.FunctionType.__name__]
            else:
                raise InferenceError('Function {func!r} inferred from {node!r} '
                                     'has no identifiable type.',
                                     node=node, func=inferred, contex=context)
        elif isinstance(inferred, treeabc.Module):
            yield raw_building.builtins_ast[types.ModuleType.__name__]
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
        return util.Uninferable
    if len(types) > 1 or not types:
        return util.Uninferable
    return list(types)[0]
