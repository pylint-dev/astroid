class First(object): pass
class Second(First): pass
class Third(First):
    def test(self):
        # +5: inferred: Super
        # +4: inferred.mro_pointer: ClassDef(super_simple_cases.Third)
        # +3: inferred.mro_pointer.name: 'Third'
        # +2: inferred.type: Instance(super_simple_cases.Third)
        # +1: inferred.type.name: 'Third'
        super(Third, self)
        # +4: inferred: Super
        # +3: inferred.mro_pointer.name: 'Second'
        # +2: inferred.type: Instance(super_simple_cases.Third)
        # +1: inferred.type.name: 'Third'
        super(Second, self)

        # mro position and the type
        # +5: inferred: Super
        # +4: inferred.mro_pointer: ClassDef(super_simple_cases.Third)
        # +3: inferred.mro_pointer.name: 'Third'
        # +2: inferred.type: ClassDef(super_simple_cases.Third)
        # +1: inferred.type.name: 'Third'
        super(Third, Third)
        # +5: inferred: Super
        # +4: inferred.mro_pointer: ClassDef(super_simple_cases.Third)
        # +3: inferred.mro_pointer.name: 'Third'
        # +2: inferred.type: ClassDef(super_simple_cases.Second)
        # +1: inferred.type.name: 'Second'
        super(Third, Second)
        # +5: inferred: Super
        # +4: inferred.mro_pointer: ClassDef(super_simple_cases.Fourth)
        # +3: inferred.mro_pointer.name: 'Fourth'
        # +2: inferred.type: ClassDef(super_simple_cases.Fourth)
        # +1: inferred.type.name: 'Fourth'
        super(Fourth, Fourth)

class Fourth(Third):
    pass
