Extending Astroid Syntax Tree
=============================

Sometimes Astroid will miss some potentially important information you may wish
you add, as content of the standard library `hashlib` module. In some other
cases, you may want to customize the way inference work, for instance to explain
Astroid that `collections.namedtuple` is returning a class with some known
attributes.

The good news is that you can do it using the transformation API. You'll find
examples in the `brain/` subdirectory. Those come from the `pylint-brain`_ project.

Transformation functions are registered using the `register_transform` method of
the Astroid manager:

.. automethod:: astroid.manager.AstroidManager.register_transform

You may want to use :class:`astroid.AsStringRegexpPredicate` predicate objects
to filter on the `as_string` representation of the node.

.. autoclass:: astroid.AsStringRegexpPredicate

Last but not least, the :func:`inference_tip` function is there to register
custom inference function.

.. autofunction:: astroid.inference_tip

.. _`pylint-brain`: https://bitbucket.org/logilab/pylint-brain