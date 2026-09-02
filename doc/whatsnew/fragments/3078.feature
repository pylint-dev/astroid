``.pyi`` stub files are now loaded and used during inference. Stub
function bodies (``...`` or ``pass``) infer the return type from the
annotation, annotated assignments produce instances of the annotated type,
and compiled extensions with an adjacent stub use the stub instead of
runtime introspection.

Closes #3078
