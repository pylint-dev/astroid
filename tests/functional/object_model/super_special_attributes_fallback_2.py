class Base:
    def method(self):
        return super().__thisclass__
Base().method()  # inferred: ClassDef(super_special_attributes_fallback_2.Base)
