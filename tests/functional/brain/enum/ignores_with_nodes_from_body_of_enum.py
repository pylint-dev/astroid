import enum

# +3: inferred: ClassDef(ignores_with_nodes_from_body_of_enum.Error)
# +2: inferred.locals: Bar, Foo, __annotations__, __members__, __module__, __qualname__, _value2member_map_, err, name
# +1: inferred.locals['err']: [AssignName(err)]
class Error(enum.Enum):
    Foo = "foo"
    Bar = "bar"
    with "error" as err:
        pass
