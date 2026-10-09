Inference now narrows values after guard statements. After
``if x is None: return``, ``x`` no longer infers ``None``, and
``assert isinstance(x, int)`` keeps only the ``int`` values of ``x`` for the
code after it. A branch is a guard when it always ends with ``return``,
``raise``, ``continue``, ``break``, or a call to ``exit()``, ``quit()``,
``sys.exit()`` or ``os._exit()``. An assignment between the guard and the use
is not narrowed, and neither is a function, lambda or class defined after the
guard.

Refs #3369
Closes pylint-dev/pylint#9809
