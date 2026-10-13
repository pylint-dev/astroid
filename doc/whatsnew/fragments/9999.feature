Inference now narrows values after an ``if`` whose body assigns the name. After
``if x is None: x = []``, ``x`` no longer infers the ``None`` it had before the
``if``. This works for names and attributes, such as ``self.x`` or ``cls.x``, with
any condition that inference already narrows on.

Refs #9999
Closes pylint-dev/pylint#5085
Closes pylint-dev/pylint#4121
Closes pylint-dev/pylint#3045
Closes pylint-dev/pylint#2855
