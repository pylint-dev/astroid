# +5: as_string(): (a := 1)
# +4: target: AssignName(a)
# +3: target.name: 'a'
# +2: value: Const(1)
# +1: value.value: 1
if __(a := 1):
    pass
# +5: as_string(): (b := test)
# +4: target: AssignName(b)
# +3: target.name: 'b'
# +2: value: Name(test)
# +1: value.name: 'test'
if __(b := test):
    pass
