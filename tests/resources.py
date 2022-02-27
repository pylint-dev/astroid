# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2015-2016, 2018-2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2018 Nick Drozd <nicholasdrozd@gmail.com>
# Copyright (c) 2019 Ashley Whetter <ashley@awhetter.co.uk>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 David Cain <davidjosephcain@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE

import os
import sys
from pathlib import Path
from typing import Optional

from astroid import builder
from astroid.manager import AstroidManager
from astroid.nodes.scoped_nodes import Module

DATA_DIR = Path("testdata") / "python3"
RESOURCE_PATH = Path(__file__).parent / DATA_DIR / "data"


def find(name: str) -> str:
    return os.path.normpath(os.path.join(os.path.dirname(__file__), DATA_DIR, name))


def build_file(path: str, modname: Optional[str] = None) -> Module:
    return builder.AstroidBuilder().file_build(find(path), modname)


class SysPathSetup:
    def setUp(self) -> None:
        sys.path.insert(0, find(""))

    def tearDown(self) -> None:
        del sys.path[0]
        datadir = find("")
        for key in list(sys.path_importer_cache):
            if key.startswith(datadir):
                del sys.path_importer_cache[key]


class AstroidCacheSetupMixin:
    """Mixin for handling the astroid cache problems.

    When clearing the astroid cache, some tests fails due to
    cache inconsistencies, where some objects had a different
    builtins object referenced.
    This saves the builtins module and makes sure to add it
    back to the astroid_cache after the tests finishes.
    The builtins module is special, since some of the
    transforms for a couple of its objects (str, bytes etc)
    are executed only once, so astroid_bootstrapping will be
    useless for retrieving the original builtins module.
    """

    @classmethod
    def setup_class(cls):
        cls._builtins = AstroidManager().astroid_cache.get("builtins")

    @classmethod
    def teardown_class(cls):
        if cls._builtins:
            AstroidManager().astroid_cache["builtins"] = cls._builtins
