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

import unittest

from astroid import bases
from astroid import nodes
from astroid import objects
from astroid import test_utils


class ObjectsTest(unittest.TestCase):

    def test_frozenset(self):
        node = test_utils.extract_node("""
        frozenset({1: 2, 2: 3}) #@
        """)
        infered = next(node.infer())
        self.assertIsInstance(infered, objects.FrozenSet)

        self.assertEqual(infered.pytype(), "%s.frozenset" % bases.BUILTINS)

        itered = infered.itered()
        self.assertEqual(len(itered), 2)
        self.assertIsInstance(itered[0], nodes.Const)
        self.assertEqual([const.value for const in itered], [1, 2])

        proxied = infered._proxied
        self.assertEqual(infered.qname(), "%s.frozenset" % bases.BUILTINS)
        self.assertIsInstance(proxied, nodes.Class)


if __name__ == '__main__':
    unittest.main()
