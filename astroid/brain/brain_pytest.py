# Copyright (c) 2014-2016 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2016 Cara Vinson <ceridwenv@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""Astroid hooks for pytest."""
from __future__ import absolute_import
from astroid import MANAGER, register_module_extender
from astroid.builder import AstroidBuilder


def pytest_transform():
    return AstroidBuilder(MANAGER).string_build('''

try:
    import _pytest.mark
    import _pytest.recwarn
    import _pytest.runner
    import _pytest.python
    import _pytest.freeze_support
    import _pytest.skipping
    import _pytest.assertion
    import _pytest.debugging
    import _pytest.fixtures
except ImportError:
    pass
else:
    deprecated_call = _pytest.recwarn.deprecated_call
    warns = _pytest.recwarn.warns
    xfail = _pytest.skipping.xfail
    exit = _pytest.runner.exit
    fail = _pytest.runner.fail
    fixture = _pytest.fixtures.fixture
    importorskip = _pytest.runner.importorskip
    mark = _pytest.mark.MarkGenerator()
    raises = _pytest.python.raises
    approx = _pytest.python.approx
    skip = _pytest.runner.skip
    freeze_includes = _pytest.freeze_support.freeze_includes
    yield_fixture = _pytest.fixtures.yield_fixture
    register_assert_rewrite = _pytest.assertion.register_assert_rewrite
    set_trace = _pytest.debugging.pytestPDB().set_trace
''')

register_module_extender(MANAGER, 'pytest', pytest_transform)
register_module_extender(MANAGER, 'py.test', pytest_transform)
