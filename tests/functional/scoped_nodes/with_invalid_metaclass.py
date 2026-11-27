class InvalidAsMetaclass: ...

# +2: inferred: ClassDef(with_invalid_metaclass.Invalid)
# +1: inferred.metaclass: with_invalid_metaclass.InvalidAsMetaclass
class Invalid(metaclass=InvalidAsMetaclass()):
    pass
