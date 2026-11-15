PEP 695 type parameters now live in their own scope (a new
:class:`astroid.nodes.TypeParamScope`), matching CPython's annotation scope.
Type parameter bounds and defaults are resolved lazily, so they may
forward-reference names defined later in an enclosing scope (e.g.
``class Basket[T: Fruit]`` where ``Fruit`` is defined afterwards) and may
reference sibling type parameters. A class's type parameters are now visible in
its method bodies. The names stay registered in the owner's ``locals`` as well,
so consumers building their own scope model out of ``locals`` keep working
unchanged.

Refs #3119
Refs pylint-dev/pylint#11115
