Inference now narrows values with ``while`` conditions, like it does with ``if``
conditions. After ``while x is not None:``, ``x`` no longer infers ``None`` in the
loop body, and the ``else`` branch of the loop applies the inverted condition.

Refs #9999
