from functools import wraps

import astroid.rebuilder
import astroid.nodes


def pytest_addoption(parser):
    parser.addoption(
        "--test-roundtrip-persistence",
        type=bool,
        default=True,
        help="run tests with modules having been serialized and then deserialized",
    )


def pytest_runtest_setup(item):
    use_roundtrip_build = item.config.getoption("--test-roundtrip-persistence")
    if use_roundtrip_build:
        astroid.rebuilder.TreeRebuilder.visit_module = roundtrip_builder(astroid.rebuilder.TreeRebuilder.visit_module)

def roundtrip_builder(f):
    @wraps(f)
    def func(self, *args, **kwargs):
        node = f(self, *args, **kwargs)
        assert isinstance(node, astroid.Module)
        data = node.dump()
        new_node = astroid.Module.load(data)

        return new_node

    return func
