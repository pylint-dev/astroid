Inference now narrows values through conditions negated with ``not``.
``not isinstance(x, int)``, ``not (x is None)`` and
``not (isinstance(x, int) and x == 3)`` used to constrain nothing; they now
behave like the inverted condition in ``if`` statements, conditional
expressions, comprehensions and boolean operations.

Refs #3368
Refs pylint-dev/pylint#8331
