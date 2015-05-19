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
code tree. For instance, inferring the following frozenset use, leads to an
inferred FrozenSet:

    CallFunc(func=Name('frozenset'), args=Tuple(...))

"""

from logilab.common.decorators import cachedproperty

from astroid import MANAGER
from astroid.bases import BUILTINS, NodeNG, Instance
from astroid.node_classes import const_factory
from astroid.mixins import ParentAssignTypeMixin


class FrozenSet(NodeNG, Instance, ParentAssignTypeMixin):
    """class representing a FrozenSet composite node"""

    def __init__(self, elts=None):
        if elts is None:
            self.elts = []
        else:
            self.elts = [const_factory(e) for e in elts]

    def pytype(self):
        return '%s.frozenset' % BUILTINS

    def itered(self):
        return self.elts

    def _infer(self, context=None):
        yield self

    @cachedproperty
    def _proxied(self):
        builtins = MANAGER.astroid_cache[BUILTINS]
        return builtins.getattr('frozenset')[0]
