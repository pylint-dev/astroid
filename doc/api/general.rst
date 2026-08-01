General API
------------

.. Exceptions are re-exported by ``astroid`` but documented on their own page.
   Listing them here as well would give every exception two pages, and Sphinx
   would then not know which one ``:exc:`AstroidError``` points at.

.. automodule:: astroid
   :exclude-members: AstroidBuildingError, AstroidError, AstroidImportError,
      AstroidIndexError, AstroidSyntaxError, AstroidTypeError,
      AstroidValueError, AttributeInferenceError, DuplicateBasesError,
      InconsistentMroError, InferenceError, InferenceOverwriteError, MroError,
      NameInferenceError, NoDefault, NotFoundError, ParentMissingError,
      ResolveError, StatementMissing, SuperArgumentTypeError, SuperError,
      TooManyLevelsError, UnresolvableName, UseInferenceDefault

.. Autodoc skips module-level data, so the singleton needs its own directive.

.. autodata:: astroid.Uninferable
   :no-value:
