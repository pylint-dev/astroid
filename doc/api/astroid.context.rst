Inference context
=================

Inferring a value can require inferring others, and the same name can be
reached by more than one path. The context carries what is already known down
that chain, so that inference terminates and does not repeat work.

.. autosummary::
   :toctree: context
   :template: autosummary_class.rst

   astroid.context.InferenceContext
   astroid.context.CallContext
