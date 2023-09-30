# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

from astroid import builder
from astroid.manager import AstroidManager
from astroid.nodes.scoped_nodes import Module

DATA_DIR = Path("testdata") / "python3"
RESOURCE_PATH = Path(__file__).parent / DATA_DIR / "data"


def find(name: str) -> str:
    return os.path.normpath(os.path.join(os.path.dirname(__file__), DATA_DIR, name))


def build_file(path: str, modname: str | None = None) -> Module:
    return builder.AstroidBuilder(AstroidManager()).file_build(find(path), modname)


class SysPathSetup:
    def setUp(self) -> None:
        sys.path.insert(0, find(""))

    def tearDown(self) -> None:
        del sys.path[0]
        datadir = find("")
        for key in list(sys.path_importer_cache):
            if key.startswith(datadir):
                del sys.path_importer_cache[key]


def _augment_sys_path(additional_paths: Sequence[str]) -> list[str]:
    original = list(sys.path)
    changes = []
    seen = set()
    for additional_path in additional_paths:
        if additional_path not in seen:
            changes.append(additional_path)
            seen.add(additional_path)

    sys.path[:] = changes + sys.path
    return original


@contextlib.contextmanager
def augmented_sys_path(additional_paths: Sequence[str]) -> Iterator[None]:
    """Augment 'sys.path' by adding entries from additional_paths."""
    original = _augment_sys_path(additional_paths)
    try:
        yield
    finally:
        sys.path[:] = original
