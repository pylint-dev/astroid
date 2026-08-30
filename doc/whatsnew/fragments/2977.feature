Inference now narrows values through conditions joined by ``and`` and ``or``.
A variable tested by several constraints at once, as in
``if isinstance(apple, int) and apple != 3``, keeps only the values satisfying
every operand, and the ``or`` and negated forms are handled too. Inference stays
conservative when an operand cannot be inferred or does not constrain the
variable.

Closes #2977
