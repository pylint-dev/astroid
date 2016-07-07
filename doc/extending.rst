Extending Astroid Syntax Tree
=============================

Sometimes Astroid will miss some potentially important information
users may wish to add, for instance with the standard library
`hashlib` module. In some other cases, users may want to customize the
way inference works, for instance to explain Astroid that calls to
`collections.namedtuple` are returning a class with some known
attributes.

Modifications in the AST are now possible using the using the generic
transformation API. You can find examples in the `brain/`
subdirectory, which are taken from the `pylint-brain`_ project.

Transformation functions are registered using the `register_transform` method of
the Astroid manager:


To add filtering based on the `as_string` representation of the node
in addition to the type, the :class:`astroid.AsStringRegexpPredicate`
predicate object can be used.

Last but not least, the :func:`inference_tip` function is there to register
a custom inference function.


.. _`pylint-brain`: https://bitbucket.org/logilab/pylint-brain
