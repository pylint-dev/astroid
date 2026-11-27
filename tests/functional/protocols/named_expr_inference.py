if (a := 2) == 2:
    a  # inferred: Const(2)


# Test a function call
def test():
    return 24

if (a := test()):
    a  # inferred: Const(24)

# Normal assignments in sequences
{ (a:= 4) }  # inferred: Set({4})
[ (a:= 5) ]  # inferred: List([5])

# Something more complicated
def test(value=(p := 24)): return p
[ y:= test()]  # inferred: List([24])

# Priority assignment
(x := 1, 2)
x  # inferred: Const(1)
