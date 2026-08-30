Proxies
=======

Inference does not only yield nodes. When a value has no node of its own — an
instance of a class, a bound method, a running generator — it is represented by
a proxy that forwards attribute lookups to the node it wraps.

:class:`~astroid.Instance`, :class:`~astroid.BoundMethod` and
:class:`~astroid.UnboundMethod` are the ones you meet most often, and are part
of the :doc:`general API <general>`.

.. autosummary::
   :toctree: bases
   :template: autosummary_class.rst

   astroid.bases.Proxy
   astroid.bases.Generator
   astroid.bases.AsyncGenerator
   astroid.bases.UnionType
