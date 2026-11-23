# Test that equality constraint is satisfied when both operands are fractions.
from fractions import Fraction

x = Fraction(1, 3)
y = Fraction(1, 3)

if x == y:
    # +3: inferred: Instance(fractions.Fraction)
    # +2: inferred._proxied: ClassDef(fractions.Fraction)
    # +1: inferred._proxied.name: 'Fraction'
    x
    # +3: inferred: Instance(fractions.Fraction)
    # +2: inferred._proxied: ClassDef(fractions.Fraction)
    # +1: inferred._proxied.name: 'Fraction'
    y

if x != y:
    # +3: inferred: Instance(fractions.Fraction)
    # +2: inferred._proxied: ClassDef(fractions.Fraction)
    # +1: inferred._proxied.name: 'Fraction'
    x
    # +3: inferred: Instance(fractions.Fraction)
    # +2: inferred._proxied: ClassDef(fractions.Fraction)
    # +1: inferred._proxied.name: 'Fraction'
    y
