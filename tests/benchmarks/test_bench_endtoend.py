# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""End-to-end benchmarks: cold import + parse + walk + infer real projects.

These exercise astroid the way pylint does: walking every node of a
real project and calling ``safe_infer`` on the nodes that matter
(``Call``, ``Attribute``, ``Name``).

- ``test_bench_endtoend_cold_lint`` — shells out
  ``python -m pylint <minimal module>`` per iteration. ~98 % of wall
  time is startup (Python import, pylint init, ``import astroid``,
  brain-plugin registration); only ~2 % is actual linting work on the
  one-line target. This captures cold-start cost that the in-process
  benches below miss: within a single pytest session ``astroid`` is
  imported once at module load and stays in ``sys.modules``, so
  optimizations like deferring brain-plugin registration are invisible
  to those benches.

  Scope note: this bench exists to *protect* targeted lazy imports of
  modules that are not on the general code path — brain plugins for
  libraries a given project does not use, and debug-only stdlib
  modules like ``pprint`` / ``logging`` deferred in #3062. Such
  function-local / ``TYPE_CHECKING`` imports work on all supported
  Python versions; they do not depend on PEP 810 lazy imports landing
  in 3.15. It is **not** an argument for lazifying modules astroid
  imports unconditionally — those just trade one fixed cost for
  another and bloat the import graph for marginal wins.

  Cold-lint runs in a dedicated **walltime** CodSpeed workflow
  (``.github/workflows/codspeed-walltime.yaml``) because the
  ``simulation`` mode used by the in-process suite
  (``.github/workflows/codspeed.yaml``) only measures Python-side
  instructions and cannot see into the subprocess.
- Two projects pinned to the SHAs used by pylint's primer corpus so the
  workload composition is stable and directly comparable with what
  pylint sees nightly:

  * **Flask** (~50 ``.py`` files under ``src/flask``) — small,
    well-typed. Parse-only (isolates the rebuilder hot path) and
    full pylint-shaped traversal.
  * **Black** (``src/black``, ``src/blackd``, ``src/blib2to3``,
    ~250 files) — medium, classic AST handling with deep class
    hierarchies.

We deliberately do *not* ship pure-Python microbenchmarks: at
microsecond scale CodSpeed CI shows >40 % StdDev, which is too noisy
for regression detection. End-to-end benches each take milliseconds
to tens of seconds per iteration, so per-run noise becomes a small
fraction of the measurement.

Source of truth for URL + SHA:
https://github.com/pylint-dev/pylint/blob/main/tests/primer/packages_to_prime.json
"""

# Fixture-name / argument-name match is the standard pytest idiom.
# pylint: disable=redefined-outer-name

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

from astroid import helpers, manager, nodes


class _Project(NamedTuple):
    url: str
    sha: str
    subdirs: tuple[tuple[str, ...], ...]


# Mirrors tests/primer/packages_to_prime.json in pylint.
_PROJECTS: dict[str, _Project] = {
    "flask": _Project(
        url="https://github.com/pallets/flask",
        sha="4cae5d8e411b1e69949d8fae669afeacbd3e5908",
        subdirs=(("src", "flask"),),
    ),
    "black": _Project(
        url="https://github.com/psf/black",
        sha="acc73dc4ff97d2c1d5999914a9a182b6e2728b8a",
        subdirs=(("src", "black"), ("src", "blackd"), ("src", "blib2to3")),
    ),
}

_INFERABLE = (nodes.Call, nodes.Attribute, nodes.Name)


def _clone_primer_project(
    name: str, tmp_path_factory: pytest.TempPathFactory
) -> list[Path]:
    """Sparse-clone a primer project at its pinned SHA, return its ``.py`` files.

    ``--filter=blob:none`` skips fetching file contents until they are
    needed; ``sparse-checkout`` restricts that fetch to the project's
    declared source subdirs (essential for huge repos like pandas).
    """
    project = _PROJECTS[name]
    clone_root = tmp_path_factory.mktemp(f"{name}-bench")
    subprocess.run(
        [
            "git",
            "clone",
            "--no-checkout",
            "--filter=blob:none",
            "--no-tags",
            "--single-branch",
            project.url,
            str(clone_root),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(clone_root),
            "sparse-checkout",
            "set",
            *("/".join(parts) for parts in project.subdirs),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(clone_root), "checkout", project.sha],
        check=True,
        capture_output=True,
    )
    files: list[Path] = []
    for subdir in project.subdirs:
        files.extend(clone_root.joinpath(*subdir).rglob("*.py"))
    return sorted(files)


@pytest.fixture(scope="session")
def flask_files(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    return _clone_primer_project("flask", tmp_path_factory)


@pytest.fixture(scope="session")
def black_files(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    return _clone_primer_project("black", tmp_path_factory)


def _parse_all(files: list[Path], mgr: manager.AstroidManager) -> int:
    """Cold-cache parse of every file (rebuilder hot path)."""
    mgr.clear_cache()
    for f in files:
        mgr.ast_from_file(str(f))
    return len(files)


def _walk_and_infer(files: list[Path], mgr: manager.AstroidManager) -> int:
    """Pylint-shaped traversal: parse, walk, safe_infer call sites."""
    mgr.clear_cache()
    count = 0
    for f in files:
        mod = mgr.ast_from_file(str(f))
        for node in mod.nodes_of_class(nodes.NodeNG):
            if isinstance(node, _INFERABLE):
                helpers.safe_infer(node)
                count += 1
    return count


# -- Cold start: pylint a tiny module in a fresh subprocess. --


_MINIMAL_LINT_TARGET = '''\
"""Minimal module for the cold-start benchmark.

Intentionally tiny but exercises brain_builtin_inference (always-on,
loaded by both the eager and lazy registration paths) without
triggering any optional brain plugin: no stdlib imports, no
dataclasses, no typing, no enum. That keeps cold-start cost dominated
by Python + pylint + astroid startup, which is the point.
"""


def add(a, b):
    return a + b


result = add(len("ab"), 2)
'''


@pytest.fixture(scope="session")
def minimal_module(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Tiny Python file used as the lint target for cold-start runs."""
    path = tmp_path_factory.mktemp("lint-target") / "minimal.py"
    path.write_text(_MINIMAL_LINT_TARGET, encoding="utf-8")
    return path


def _pylint_one_file(target: Path) -> None:
    """Run ``python -m pylint <target>`` in a fresh subprocess.

    pylint exits non-zero whenever it emits any message (warnings,
    refactor hints, etc.), which is expected on most files. We don't
    care about the exit code here, only the wall time.
    """
    subprocess.run(
        [sys.executable, "-m", "pylint", str(target)],
        check=False,
        capture_output=True,
    )


def test_bench_endtoend_cold_lint(benchmark, minimal_module: Path) -> None:
    benchmark(_pylint_one_file, minimal_module)


# -- Flask: small, parse + walk_infer (parse isolates rebuilder cost). --


def test_bench_endtoend_parse_flask(benchmark, flask_files: list[Path]) -> None:
    assert flask_files, "Expected at least one .py file in flask"
    mgr = manager.AstroidManager()
    benchmark(_parse_all, flask_files, mgr)


def test_bench_endtoend_walk_infer_flask(benchmark, flask_files: list[Path]) -> None:
    assert flask_files, "Expected at least one .py file in flask"
    mgr = manager.AstroidManager()
    benchmark(_walk_and_infer, flask_files, mgr)


# -- Black: medium, walk_infer only. --


def test_bench_endtoend_walk_infer_black(benchmark, black_files: list[Path]) -> None:
    assert black_files, "Expected at least one .py file in black"
    mgr = manager.AstroidManager()
    benchmark(_walk_and_infer, black_files, mgr)
