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
"""Python Abstract Syntax Tree New Generation

The aim of this module is to provide a common base representation of
python source code for projects such as pychecker, pyreverse,
pylint... Well, actually the development of this library is essentially
governed by pylint's needs.

It extends class defined in the python's _ast module with some
additional methods and attributes. Instance attributes are added by a
builder object, which can either generate extended ast (let's call
them astroid ;) by visiting an existent ast tree or by inspecting living
object. Methods are added by monkey patching ast classes.

Main modules are:

* nodes and scoped_nodes for more information about methods and
  attributes added to different node classes

* the manager contains a high level object to get astroid trees from
  source files and living objects. It maintains a cache of previously
  constructed tree for quick access

* builder contains the class responsible to build astroid trees
"""
__doctype__ = "restructuredtext en"

import sys

# WARNING: internal imports order matters !

# make all exception classes accessible from astroid package
from astroid.exceptions import *

# make all node classes accessible from astroid package
from astroid.nodes import *

# trigger extra monkey-patching
from astroid import inference

# more stuff available
from astroid import raw_building
from astroid.bases import YES, Instance, BoundMethod, UnboundMethod
from astroid.node_classes import are_exclusive, unpack_infer
from astroid.scoped_nodes import builtin_lookup

# make a manager instance (borg) as well as Project and Package classes
# accessible from astroid package
from astroid.manager import AstroidManager, Project
MANAGER = AstroidManager()
del AstroidManager

# load brain plugins
from os import listdir
from os.path import join, dirname
BRAIN_MODULES_DIR = join(dirname(__file__), 'brain')
if BRAIN_MODULES_DIR not in sys.path:
    # add it to the end of the list so user path take precedence
    sys.path.append(BRAIN_MODULES_DIR)
# load modules in this directory
for module in listdir(BRAIN_MODULES_DIR):
    if module.endswith('.py'):
        __import__(module[:-3])
