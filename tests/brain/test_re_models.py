# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# for details: https://github.com/pylint-dev/astroid/blob/main/LICENSE

"""The synthetic re model classes must stay plain trees.

Building them with the default transform pipeline runs the "re" module
extender on every synthetic tree, re-parsing the whole flags module into
its locals. The real re module must keep those flags; the synthetic trees
must not carry them.
"""

# pylint: disable=redefined-outer-name

import pytest

from astroid import nodes
from astroid.brain import brain_re
from astroid.manager import AstroidManager

EXTENDER_LOCALS = (
    "_compiler",
    "NOFLAG",
    "ASCII",
    "IGNORECASE",
    "LOCALE",
    "UNICODE",
    "MULTILINE",
    "DOTALL",
    "VERBOSE",
    "TEMPLATE",
    "DEBUG",
    "A",
    "I",
    "L",
    "U",
    "M",
    "S",
    "X",
    "T",
)


@pytest.fixture()
def fresh_re_manager():
    """A manager whose re build cannot reuse a poisoned global state.

    Other tests (brainless_manager().clear_cache()) may wipe the shared
    ClassVar transform visitor and leave a transform-less "re" tree in the
    shared cache. Force a fresh "re" build and make sure the brains this
    module relies on are registered.
    """
    brain = AstroidManager.brain
    # Mutate the shared dicts strictly in place: replacing them would fork
    # cache objects still bound to earlier managers (e.g. astroid.MANAGER).
    saved_re = brain["astroid_cache"].pop("re", None)
    saved_re_file = brain["_mod_file_cache"].pop("re", None)
    saved_transforms = brain["_transform"].transforms
    manager = AstroidManager()
    # Other tests leave the shared visitor full of empty transform lists;
    # only a non-empty list means the brains this module relies on survived.
    if not any(manager._transform.transforms.values()):
        manager.clear_cache()
    try:
        yield manager
    finally:
        if saved_re is not None:
            brain["astroid_cache"]["re"] = saved_re
        if saved_re_file is not None:
            brain["_mod_file_cache"]["re"] = saved_re_file
        brain["_transform"].transforms = saved_transforms


@pytest.mark.parametrize("name", ["Pattern", "Match", "SRE_Scanner"])
def test_model_tree_is_not_extended(name):
    # Load the real module first so the synthetic parse cannot occupy the
    # "re" cache slot (pre-existing setdefault behavior, out of scope here).
    AstroidManager().ast_from_module_name("re")
    model = brain_re._model_class(name)
    root = model.root()
    for leaked in EXTENDER_LOCALS:
        assert (
            leaked not in root.locals
        ), f"{leaked} leaked into the synthetic {name} tree"
    assert set(root.locals) == {name}
    assert all(method in model.locals for method in brain_re._METHODS[name])


def test_real_re_module_keeps_extender_locals(fresh_re_manager):
    manager = fresh_re_manager
    real = manager.ast_from_module_name("re")
    for flag in EXTENDER_LOCALS:
        assert flag in real.locals
    brain_re._model_class("Pattern")
    brain_re._model_class("Match")
    brain_re._model_class("SRE_Scanner")
    assert manager.ast_from_module_name("re") is real


def test_pattern_model_is_reparented_into_real_re(fresh_re_manager):
    manager = fresh_re_manager
    real = manager.ast_from_module_name("re")
    pattern = next(real.getattr("Pattern")[0].infer())
    assert isinstance(pattern, nodes.ClassDef)
    assert pattern.name == "Pattern"
    assert pattern.root() is real
    assert pattern.qname() == "re.Pattern"
    for flag in ("NOFLAG", "ASCII", "MULTILINE", "A"):
        assert flag in real.locals
