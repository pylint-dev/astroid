# Copyright (c) 2006-2013, 2015 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2014 Eevee (Alex Munroe) <amunroe@yelp.com>
# Copyright (c) 2015-2016, 2018, 2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015-2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2016 Derek Gustafson <degustaf@gmail.com>
# Copyright (c) 2016 Moises Lopez <moylop260@vauxoo.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2019 Nick Drozd <nicholasdrozd@gmail.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE

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

from importlib import import_module
from pathlib import Path

# isort: off
# We have an isort: off on '__version__' because the packaging need to access
# the version before the dependencies are installed (in particular 'wrapt'
# that is imported in astroid.inference)
from astroid.__pkginfo__ import __version__, version

# isort: on

from astroid import inference, raw_building
from astroid.astroid_manager import MANAGER
from astroid.bases import BaseInstance, BoundMethod, Instance, UnboundMethod
from astroid.brain.helpers import register_module_extender
from astroid.builder import extract_node, parse
from astroid.const import Context, Del, Load, Store
from astroid.exceptions import *
from astroid.inference_tip import _inference_tip_cached, inference_tip
from astroid.node_classes import are_exclusive, unpack_infer
from astroid.nodes import *  # pylint: disable=redefined-builtin (Ellipsis)
from astroid.scoped_nodes import builtin_lookup
from astroid.util import Uninferable

# load brain plugins
ASTROID_INSTALL_DIRECTORY = Path(__file__).parent
BRAIN_MODULES_DIRECTORY = ASTROID_INSTALL_DIRECTORY / "brain"
for module in BRAIN_MODULES_DIRECTORY.iterdir():
    if module.suffix == ".py":
        import_module(f"astroid.brain.{module.stem}")
