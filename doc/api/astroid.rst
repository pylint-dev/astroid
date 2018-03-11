:mod:`astroid`
==============

.. automodule:: astroid

Submodules
----------
.. autosummary::
   :toctree:

   astroid.exceptions
   astroid.nodes

Exceptions
----------
.. currentmodule:: astroid.exceptions

.. autosummary::

   AstroidBuildingError
   AstroidBuildingException
   AstroidError
   AstroidImportError
   AstroidIndexError
   AstroidSyntaxError
   AstroidTypeError
   AttributeInferenceError
   BinaryOperationError
   DuplicateBasesError
   InconsistentMroError
   InferenceError
   MroError
   NameInferenceError
   NoDefault
   NotFoundError
   OperationError
   ResolveError
   SuperArgumentTypeError
   SuperError
   TooManyLevelsError
   UnaryOperationError
   UnresolvableName
   UseInferenceDefault

.. currentmodule:: astroid

.. data:: MANAGER

   The manager for doing stuff.

   :type: astroid.manager.AstroidManager


.. autoclass:: Uninferable

.. autofunction:: are_exclusive

.. autofunction:: builtin_lookup

.. autofunction:: extract_node

.. autofunction:: parse

.. autofunction:: unpack_infer
