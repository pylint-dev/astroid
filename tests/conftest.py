import contextlib
import functools

import astroid
import astroid.builder
import astroid.nodes


# Unit testing persistence is quite difficult due to some of the idiosyncrocies of
# astroid's implementation.
# Ideally, we'd be able to run the existing tests with some instrumented code that returns
# a copy of module which has undergone a roundtrip through JSON. This ensures that the roundtrip
# process doesn't lose any information (and we're able to thoroughly test this fact by leveraging the
# existing tests).
#
# This is difficult for two reasons, both of which exist to handle populating information from imports:
#   - Partially constructed modules must be added to the cache to avoid infinite recursion
#   - The builder holds on to references to nodes inside the module's tree.
#
# This makes things difficult because if we roundtrip the module too soon, the builder will be holding
# references to nodes that are no longer relevant. If we roundtrip too late, then the module pulled
# from the cache for circular referencing is the old module.
def pytest_addoption(parser):
    parser.addoption(
        "--test-roundtrip-persistence",
        type=bool,
        default=True,
        help="run tests with modules having been serialized and then deserialized",
    )


@contextlib.contextmanager
def cache_module(manager: astroid.manager.AstroidManager, module: astroid.nodes.Module):
    cache = manager.astroid_cache
    key = module.name
    roundtrip = False
    if key not in cache:
        roundtrip = True
    # Put the original module in the cache to begin with,
    # since the recusrive importing won't be extracting any references
    # to nodes (just info about the module) this should be safe
    cache[key] = module
    yield

    if roundtrip:
        cache[key] = astroid.nodes.Module.load(module.dump())


def rountrip_extracton(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        module = f(*args, **kwargs)
        data = module.dump()
        new_module = astroid.nodes.Module.load(data)

        # Need to opt out of transforming enums, the original module's transform
        # has already stored the appropriate info, and re-transforming would
        # alter the data to a state that doesn't reflect the truth
        astroid.MANAGER.unregister_transform(
            astroid.nodes.ClassDef, infer_enum_class, predicate=_is_enum_subclass
        )

        # From brain_namedtuple_enum.py
        # AstroidManager().register_transform(
        #   nodes.ClassDef, infer_enum_class, predicate=_is_enum_subclass
        # )

        new_module = astroid.MANAGER.visit_transforms(new_module)
        # Copy the file_bytes. This shouldn't be persisted
        new_module.file_bytes = module.file_bytes
        return module

    return func


def pytest_collection(session):
    use_roundtrip_build = session.config.getoption("--test-roundtrip-persistence")
    if use_roundtrip_build:
        astroid.builder.parse = rountrip_extracton(astroid.builder.parse)
