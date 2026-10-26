Inference now narrows values with ``callable(x)`` conditions. After
``if callable(x):``, ``x`` no longer infers values that cannot be called, and
after ``if not callable(x):`` it no longer infers values that can.

Refs #3391
Refs pylint-dev/pylint#1493
