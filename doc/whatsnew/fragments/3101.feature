Inference now narrows values through the preceding operands of ``and`` and
``or``. In ``x is not None and x``, the last ``x`` no longer infers ``None``.
In ``x is None or x``, the last ``x`` is only evaluated when ``x is None`` is
false, so that condition is applied inverted. Constraints from several
preceding operands, including nested boolean operations, are combined.

Refs #3101
Refs pylint-dev/pylint#1498
