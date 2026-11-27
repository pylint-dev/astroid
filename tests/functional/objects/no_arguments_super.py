class First(object): pass
class Second(First):
    def test(self):
        # +5: inferred: Super
        # +4: inferred.mro_pointer: ClassDef(no_arguments_super.Second)
        # +3: inferred.mro_pointer.name: 'Second'
        # +2: inferred.type: Instance(no_arguments_super.Second)
        # +1: inferred.type.name: 'Second'
        super()
    @classmethod
    def test_classmethod(cls):
        # +5: inferred: Super
        # +4: inferred.mro_pointer: ClassDef(no_arguments_super.Second)
        # +3: inferred.mro_pointer.name: 'Second'
        # +2: inferred.type: ClassDef(no_arguments_super.Second)
        # +1: inferred.type.name: 'Second'
        super()
