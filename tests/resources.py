# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import os
import sys
from pathlib import Path

from astroid import builder
from astroid.nodes.scoped_nodes import Module

DATA_DIR = Path("testdata") / "python3"
RESOURCE_PATH = Path(__file__).parent / DATA_DIR / "data"


def find(name: str) -> str:
    return os.path.normpath(os.path.join(os.path.dirname(__file__), DATA_DIR, name))


def build_file(path: str, modname: str | None = None) -> Module:
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
