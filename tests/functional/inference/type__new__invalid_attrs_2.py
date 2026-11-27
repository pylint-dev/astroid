type.__new__(type, 'a', (), {object: 1})  # inferred: ClassDef(type__new__invalid_attrs_2.a)
type.__new__(type, 'a', (), {1:2, "a":5})  # inferred: ClassDef(type__new__invalid_attrs_2.a)
