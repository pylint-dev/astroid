from functools import wraps

import astroid.builder
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
        astroid.builder.AstroidBuilder.string_build = roundtrip_builder(astroid.builder.AstroidBuilder.string_build)
        astroid.builder.AstroidBuilder.file_build = roundtrip_builder(astroid.builder.AstroidBuilder.file_build)

def roundtrip_builder(f):
    @wraps(f)
    def func(self, *args, **kwargs):
        node = f(self, *args, **kwargs)
        assert isinstance(node, astroid.Module)
        data = node.dump()
        new_node = astroid.Module.load(data)

        # @TODO: This would probably be handled by the builder
        if self._apply_transforms:
            # We have to handle transformation by ourselves since the
            # rebuilder isn't called for builtin nodes
            new_node = self._manager.visit_transforms(node)
        # return node
        return new_node

    return func
