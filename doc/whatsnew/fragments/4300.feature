A module that defines a module level ``__getattr__`` (:pep:`562`) can now serve
names that are not defined statically. Looking up such a name infers the value
the ``__getattr__`` returns for it, with the name bound, instead of raising
``AttributeInferenceError``, so the deprecation shim pattern infers to the
aliased value. Names starting with ``__`` are left alone, as for classes.
``Module.dynamic_getattr()`` and ``Module.has_dynamic_getattr()`` expose the
``__getattr__`` a module defines.

Closes pylint-dev/pylint#4300
