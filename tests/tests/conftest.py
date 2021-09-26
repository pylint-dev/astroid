from functools import wraps

import astroid.builder
import astroid.nodes

def roundtrip_builder(f):
    @wraps(f)
    def func(*args, **kwargs):
        node = f(*args, **kwargs)
        assert isinstance(node, astroid.Module)
        data = node.dump()
        new_node = astroid.Module.load(data)
        return node

    return func


astroid.builder.AstroidBuilder.string_build = roundtrip_builder(astroid.builder.AstroidBuilder.string_build)
astroid.builder.AstroidBuilder.module_build = roundtrip_builder(astroid.builder.AstroidBuilder.module_build)
astroid.builder.AstroidBuilder.file_build = roundtrip_builder(astroid.builder.AstroidBuilder.file_build)
astroid.builder.AstroidBuilder.inspect_build = roundtrip_builder(astroid.builder.AstroidBuilder.inspect_build)

