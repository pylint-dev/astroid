"""Astroid hooks for pytest."""

from astroid import MANAGER
from astroid import nodes
from astroid.builder import AstroidBuilder


MODULE_TRANSFORMS = {}


def transform(module):
    try:
        tr = MODULE_TRANSFORMS[module.name]
    except KeyError:
        pass
    else:
        tr(module)


def pytest_transform(module):
    fake = AstroidBuilder(MANAGER).string_build('''

try:
    import _pytest.mark
    import _pytest.recwarn
    import _pytest.runner
    import _pytest.python
except ImportError:
    pass
else:
    deprecated_call = _pytest.recwarn.deprecated_call
    exit = _pytest.runner.exit
    fail = _pytest.runner.fail
    fixture = _pytest.python.fixture
    importorskip = _pytest.runner.importorskip
    mark = _pytest.mark.MarkGenerator()
    raises = _pytest.python.raises
    skip = _pytest.runner.skip
    yield_fixture = _pytest.python.yield_fixture

''')

    for item_name, item in fake.locals.items():
        module.locals[item_name] = item


MODULE_TRANSFORMS['pytest'] = pytest_transform
MODULE_TRANSFORMS['py.test'] = pytest_transform

MANAGER.register_transform(nodes.Module, transform)
