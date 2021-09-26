from functools import wraps

import astroid.builder
import astroid.nodes

def pytest_addoption(parser):
    parser.addoption(
        "--test-roundtrip-persistence", type=bool, default=True,
        help="run tests with modules having been serialized and then deserialized",
    )

def pytest_runtest_setup(item):
    use_roundtrip_build = item.config.getoption("--test-roundtrip-persistence")
    if use_roundtrip_build:
        astroid.builder.AstroidBuilder.string_build = roundtrip_builder(astroid.builder.AstroidBuilder.string_build)
        astroid.builder.AstroidBuilder.module_build = roundtrip_builder(astroid.builder.AstroidBuilder.module_build)
        astroid.builder.AstroidBuilder.file_build = roundtrip_builder(astroid.builder.AstroidBuilder.file_build)
        astroid.builder.AstroidBuilder.inspect_build = roundtrip_builder(astroid.builder.AstroidBuilder.inspect_build)

def roundtrip_builder(f):
    @wraps(f)
    def func(*args, **kwargs):
        node = f(*args, **kwargs)
        assert isinstance(node, astroid.Module)
        data = node.dump()
        new_node = astroid.Module.load(data)
        return node

    return func
