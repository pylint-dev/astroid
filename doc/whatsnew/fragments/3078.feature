When ``--prefer-stubs`` is enabled in Pylint, ``.pyi`` stub files are now loaded
and used during inference, and compiled extensions with an adjacent stub use
the stub instead of runtime introspection. Stub functions whose bodies contain
only ``...``, ``pass``, or a docstring infer the return type from the annotation.

Closes #3078
