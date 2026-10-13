Inference now narrows values with conditions on their length, like
``if len(x) == 1:`` or ``if len(x) > 2:``. Lists, tuples, sets, dicts, strings
and bytes whose length does not pass the comparison are no longer inferred.

Refs #9999
Closes pylint-dev/pylint#9986
