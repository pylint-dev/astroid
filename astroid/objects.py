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
Inference objects are a way to represent composite AST nodes,
which are used only as inference results, so they can't be found in the
original AST tree. For instance, inferring the following frozenset use,
leads to an inferred FrozenSet:

    Call(func=Name('frozenset'), args=Tuple(...))
"""

import six

from astroid import bases
from astroid import decorators
from astroid import exceptions
from astroid import MANAGER
from astroid import node_classes
from astroid import scoped_nodes
from astroid import util


BUILTINS = six.moves.builtins.__name__


class FrozenSet(node_classes._BaseContainer):
    """class representing a FrozenSet composite node"""

    def pytype(self):
        return '%s.frozenset' % BUILTINS

    def _infer(self, context=None):
        yield self

    @decorators.cachedproperty
    def _proxied(self): # pylint: disable=method-hidden
        builtins = MANAGER.astroid_cache[BUILTINS]
        return builtins.getattr('frozenset')[0]


class Super(node_classes.NodeNG):
    """Proxy class over a super call.

    This class offers almost the same behaviour as Python's super,
    which is MRO lookups for retrieving attributes from the parents.

    The *mro_pointer* is the place in the MRO from where we should
    start looking, not counting it. *mro_type* is the object which
    provides the MRO, it can be both a type or an instance.
    *self_class* is the class where the super call is, while
    *scope* is the function where the super call is.
    """
    # pylint: disable=super-init-not-called
    def __init__(self, mro_pointer, mro_type, self_class, scope):
        self.type = mro_type
        self.mro_pointer = mro_pointer
        self._class_based = False
        self._self_class = self_class
        self._scope = scope
        self._model = {
            '__thisclass__': self.mro_pointer,
            '__self_class__': self._self_class,
            '__self__': self.type,
            '__class__': self._proxied,
        }

    def _infer(self, context=None):
        yield self

    def super_mro(self):
        """Get the MRO which will be used to lookup attributes in this super."""
        if not isinstance(self.mro_pointer, scoped_nodes.ClassDef):
            raise exceptions.SuperError(
                "The first argument to super must be a subtype of "
                "type, not {mro_pointer}.", super_=self)

        if isinstance(self.type, scoped_nodes.ClassDef):
            # `super(type, type)`, most likely in a class method.
            self._class_based = True
            mro_type = self.type
        else:
            mro_type = getattr(self.type, '_proxied', None)
            if not isinstance(mro_type, (bases.Instance, scoped_nodes.ClassDef)):
                raise exceptions.SuperError(
                    "The second argument to super must be an "
                    "instance or subtype of type, not {type}.",
                    super_=self)

        if not mro_type.newstyle:
            raise exceptions.SuperError("Unable to call super on old-style classes.", super_=self)

        mro = mro_type.mro()
        if self.mro_pointer not in mro:
            raise exceptions.SuperError(
                "The second argument to super must be an "
                "instance or subtype of type, not {type}.",
                super_=self)

        index = mro.index(self.mro_pointer)
        return mro[index + 1:]

    @decorators.cachedproperty
    def _proxied(self):
        builtins = MANAGER.astroid_cache[BUILTINS]
        return builtins.getattr('super')[0]

    def pytype(self):
        return '%s.super' % BUILTINS

    def display_type(self):
        return 'Super of'

    @property
    def name(self):
        """Get the name of the MRO pointer."""
        return self.mro_pointer.name

    def igetattr(self, name, context=None):
        """Retrieve the inferred values of the given attribute name."""

        local_name = self._model.get(name)
        if local_name:
            yield local_name
            return

        try:
            mro = self.super_mro()
        # Don't let invalid MROs or invalid super calls
        # leak out as is from this function.
        except exceptions.SuperError as exc:
            util.reraise(exceptions.AttributeInferenceError(
                ('Lookup for {name} on {target!r} because super call {super!r} '
                 'is invalid.'),
                target=self, attribute=name, context=context, super_=exc.super_))
        except exceptions.MroError as exc:
            util.reraise(exceptions.AttributeInferenceError(
                ('Lookup for {name} on {target!r} failed because {cls!r} has an '
                 'invalid MRO.'),
                target=self, attribute=name, context=context, mros=exc.mros,
                cls=exc.cls))
        found = False
        for cls in mro:
            if name not in cls.locals:
                continue

            found = True
            for inferred in bases._infer_stmts([cls[name]], context, frame=self):
                if not isinstance(inferred, scoped_nodes.FunctionDef):
                    yield inferred
                    continue

                # We can obtain different descriptors from a super depending
                # on what we are accessing and where the super call is.
                if inferred.type == 'classmethod':
                    yield bases.BoundMethod(inferred, cls)
                elif self._scope.type == 'classmethod' and inferred.type == 'method':
                    yield inferred
                elif self._class_based or inferred.type == 'staticmethod':
                    yield inferred
                elif bases._is_property(inferred):
                    # TODO: support other descriptors as well.
                    for value in inferred.infer_call_result(self, context):
                        yield value
                else:
                    yield bases.BoundMethod(inferred, cls)

        if not found:
            raise exceptions.AttributeInferenceError(target=self,
                                                     attribute=name,
                                                     context=context)

    def getattr(self, name, context=None):
        return list(self.igetattr(name, context=context))
