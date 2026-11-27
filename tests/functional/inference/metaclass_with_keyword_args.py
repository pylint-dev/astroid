class TestMetaKlass(type):
    def __new__(mcs, name, bases, ns, kwo_arg):
        return super().__new__(mcs, name, bases, ns)

# +1: inferred: ClassDef(metaclass_with_keyword_args.TestKlass)
class TestKlass(metaclass=TestMetaKlass, kwo_arg=42):
    pass
