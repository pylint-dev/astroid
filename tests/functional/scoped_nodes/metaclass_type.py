def with_metaclass(meta, base=object):
    return meta("NewBase", (base, ), {})

# +1: ancestors: metaclass_type.with_metaclass.NewBase, builtins.object
class ClassWithMeta(with_metaclass(type)):
    pass
