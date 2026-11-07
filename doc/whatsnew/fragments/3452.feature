The targets a ``for`` loop or comprehension unpacks from a generator are now
inferred from the values the generator yields. ``os.walk()`` is modelled as
yielding a path and two lists, the path being ``bytes`` if ``top`` is ``bytes``
and ``str`` otherwise. In ``for dirpath, dirnames, filenames in os.walk(".")``,
``dirnames`` now infers to a list, so pylint can report
``modified-iterating-list`` when the loop removes items from it.

Refs #3452
Refs pylint-dev/pylint#9192
