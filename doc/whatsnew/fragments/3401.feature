Inference now narrows values with conditions that use an assignment expression.
After ``if (x := f()) is not None:``, ``x`` no longer infers ``None``, and the
same goes for the other supported conditions, like ``if x := f():``,
``isinstance(x := f(), int)`` or the later operands of ``(x := f()) and x``.

Refs #3401
