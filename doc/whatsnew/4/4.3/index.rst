***************************
 What's New in astroid 4.3
***************************

.. towncrier release notes start

What's new in astroid 4.3.1?
----------------------------
Release date: 2026-08-17

* Fix inference of the attributes of a ``namedtuple`` created with
  ``rename=True``. The renamed fields were applied to ``_fields`` and to the
  class body, but the instance kept the field names as written, so an instance
  of ``namedtuple("Tuple", "abc def", rename=True)`` was inferred as having a
  ``def`` attribute instead of ``_1``, and duplicate field names collapsed into
  a single attribute instead of being renamed.

  Closes #242

What's new in astroid 4.3.0?
----------------------------
Release date: 2026-08-07

Version 4.2.0 was skipped: a ``v4.2.0`` tag was created by mistake during an
aborted release attempt, so the changes from the ``4.2.0`` betas are released
as ``4.3.0``.

* Fix a crash on a functional ``namedtuple`` whose field name changes under NFKC
  normalization, such as ``namedtuple("mu", ["µ"])``. Python normalizes
  identifiers, so the parsed class stores the field under ``"μ"`` while the
  brain looked it up as written, raising ``KeyError`` on a definition that
  ``namedtuple`` itself accepts.

  Closes pylint-dev/pylint#8746

* Fix inference of a method's first argument (``self`` or ``cls``) when the
  method's return value is stored on an unrelated object. This avoids inferring
  ``cls`` as the caller's class when indexing a tuple returned by a
  classmethod such as ``A.c()[0]``.

  Closes pylint-dev/pylint#11101

* ``super()`` with no argument now resolves against the class of the object the
  method was called on, instead of the class the method is written in. One consequence
  is that a ``typing.Self`` return value survives a chain of ``super()`` calls.

  Closes #2852
  Closes pylint-dev/pylint#10807

* ``typing.overload`` stubs no longer shadow the implementation when a special
  method is looked up in the MRO.

  Closes #2448

* Fix a crash when the field names of a functional ``Enum`` or ``namedtuple``
  call are bytes, as in ``Enum("", b"")``. Such a definition is invalid, so
  inference now falls back to its default instead of raising ``TypeError``.

  Closes #3189

* Fix a crash when the body of a ``typing.NamedTuple`` subclass contains an
  assignment whose target is not a single name, such as ``cat.color = "black"``,
  ``basket[0] = "apple"`` or ``apple, banana = "red", "yellow"``. The names bound
  by unpacking are now copied to the inferred class as well.

  Closes #3190

* Fix a crash when a binary operation involves a class whose metaclass is not a
  class, as in ``class C(metaclass=sum)`` followed by ``C | None``. The type of
  such a class is a function, which has no bases, so ``has_known_bases()`` now
  returns ``False`` for anything that is not a class.

  Closes #3191

* Fix a crash when a dataclass inherits from a dataclass that annotates
  ``__init__`` as a field, as in ``__init__: int``. Such a base binds
  ``__init__`` to a name instead of a function, so it no longer contributes
  arguments to the generated ``__init__``.

  Closes #3200

* The documentation build now fails on any Sphinx warning, so a cross-reference
  that does not resolve is caught by CI instead of quietly rendering as plain
  text. ``Uninferable``, ``Position`` and the ``BadOperationMessage`` classes
  are documented as part of the public API, and a number of docstrings that
  Sphinx could not parse were repaired.

* The ``>>>`` examples in the documentation are run when the documentation is
  built, so one that stops being true is noticed. Most of them could not run
  before: they printed node addresses recorded in 2018, and the multi-line ones
  were missing the ``...`` continuation prompt. The example for ``Decorators``
  reported the wrong line numbers.

* Fix the example in the docstring of ``BoolOp``, which showed the node it was
  copied from: ``astroid.extract_node("a and b")`` gives a ``BoolOp``, not a
  ``BinOp``.

* Names written between single backticks in the ChangeLog render as code again,
  rather than as italics.

* Prevent crashes while processing extension-module classes whose bases cannot
  be resolved when applying enum inference transformations.

  Closes pylint-dev/pylint#11179

* The API documentation now covers the proxies, the objects with no node of
  their own, the inference context, the manager, the object models and the
  extension call signatures. The ``EvaluatedObject``, ``Interpolation``,
  ``NamedExpr`` and ``TemplateStr`` nodes were missing from the list of nodes
  and are listed now.

* Add ``__required_keys__`` and ``__optional_keys__`` to the inferred
  ``TypedDict`` base class, so subclasses no longer raise a ``no-member``
  false positive in pylint when accessing those attributes at runtime.

  Closes pylint-dev/pylint#10158

* Comprehension conditions now constrain the inference of names used in the
  comprehension, like ``if`` statement conditions already did:
  ``[x for x in lst if x is not None]`` no longer infers ``None`` for ``x``
  in the element expression.

  Refs #3094

* Fix ``isinstance()`` constraints only filtering the first inferred value of
  a variable: checking a value made the ``isinstance`` classinfo uninferable
  for the checks of the following values.

* Remove Python 2 era dead code and outdated comments.
  Notably: the internal ``TreeRebuilder`` constructor no longer takes a
  ``parser_module`` argument.

  Refs #3154

* Fix inference of a starred target that is not last in a ``for`` loop, such as
  ``for a, *b, c in ...``. The elements following the starred one were counted
  from the target's own arity rather than from the end of the iterable, so
  ``b`` was truncated whenever the iterable was longer than the target.

* Add ``qname()`` method to the ``Slice`` node class, returning
  ``"builtins.slice"``, so that the node can be used in contexts
  that require a qualified name (e.g. pylint's ``basic_checker``).

  Closes #3115

* Add brain tip for ``numpy.fromfile`` so that calls to
  ``np.fromfile(...)`` are correctly inferred as returning
  ``numpy.ndarray`` instead of ``Uninferable``.

  Closes #600

* Add brain for `decimal` that gets applied if `_decimal` isn't available.

* Removed the `**kwargs` argument from all `infer` functions.
  Users upgrading their `astroid` versions should ensure they do no pass values other than
  `context` to `infer`.

* Deduplicate keys when inferring ``dict.fromkeys``. ``dict.fromkeys("aab")``
  now infers a dict with keys ``"a"``, ``"b"`` instead of ``"a"``, ``"a"``,
  ``"b"``, matching the runtime. This also stops ``dict.fromkeys`` from
  materializing one ``Const`` node per character for a repeated string such as
  ``dict.fromkeys("x" * 10 ** 8)``, which is a single-key dict.

* Bound str/bytes and list/tuple concatenation (``a + b``) during inference.

* Bound oversized old-style (``%``) string/bytes formatting during inference.
  A tiny literal such as ``"%1000000000d" % 1`` made
  ``_infer_old_style_string_formatting`` eagerly build a multi-gigabyte
  ``Const`` while inferring otherwise untrusted source. The width and
  precision are now read out of the conversion specifiers (including ``*``
  fields) and the interpolation infers as ``Uninferable`` past ``1e8``,
  mirroring the repetition, concatenation and ``str.format`` caps. Bytes
  ``%`` formatting is routed through the same handler so it is bounded too;
  small format strings keep inferring their exact value.

* Fix crash (``TypeError: 'UninferableBase' object is not iterable``) in the
  ``multiprocessing`` brain when a local package shadows the stdlib
  ``multiprocessing`` module.

  Closes pylint-dev/pylint#10014

* Bound the number of nodes built when inferring ``list``/``set``/``tuple``/
  ``frozenset`` and ``dict.fromkeys`` from a ``str``/``bytes`` constant. These
  built one ``Const`` node per character with no cap, so ``list(("a" * 10 ** 8)
  + "b")`` (concatenation is not size-bounded) materialized hundreds of millions
  of nodes. They now fall back to the default inference past ``1e8`` characters,
  matching the sequence-repetition guard.

Refs #3127

* Bound string/bytes multiplication (``"x" * n``) and integer left shifts
  (``1 << n``) in ``const_infer_binary_op`` the same way list/tuple
  multiplication and ``**`` already are. Inferring a constant such as
  ``"A" * 10 ** 10`` previously materialized the multi-gigabyte result
  eagerly; these operations now infer as ``Uninferable`` when the result
  would be oversized.

  Refs #3107

* Bound the field width and precision when inferring ``str.format`` calls.
  A template such as ``"{:>2000000000}".format("x")`` (or a width/precision
  supplied through a nested ``{}`` field) previously built the padded
  multi-gigabyte string eagerly during inference; such calls now infer as
  ``Uninferable`` when the field size would be oversized.

  Refs #3131

* Remove the ``asname`` keyword argument from ``Import._infer`` and
  ``ImportFrom._infer``. The alias-to-real-name translation that
  ``asname=True`` performed is now hoisted into ``ImportNode._infer_name``,
  which runs in ``_infer_stmts`` before ``_infer`` is dispatched. Direct
  callers of ``Import.infer`` / ``ImportFrom.infer`` (previously the
  ``asname=False`` path) now consistently resolve the lookup name as-is.

  The two flows used to collapse into a single inference cache entry
  because the ``asname`` kwarg was not part of the cache key, so the
  second call returned the cached result of the first regardless of
  which one ran. With the translation hoisted upstream, the two flows
  set different ``lookupname`` values and therefore land on distinct
  cache keys, eliminating the collision.

  Refs pylint-dev/pylint#10193
  Closes #3007

* Avoid materializing a multi-gigabyte string while inferring a small literal
  such as ``"{:>2000000000}".format("x")`` or ``f"{1.5:.2000000000f}"``.
  ``_infer_str_format_call`` and ``FormattedValue._infer`` now yield
  ``Uninferable`` when a format spec asks for a width or precision over 1e8,
  mirroring the sequence/repetition caps in ``astroid.protocols``.

Refs #3108

* Fix uncaught ``IndentationError`` when parsing code whose lines end in
  ``\r``: the slice of source tokenized to compute a class or function
  ``position`` is split on ``\n`` only and could be misaligned with the AST
  line numbers. Such nodes now simply have no position information, as
  already done when ``tokenize`` raises ``TokenError``.

  Closes #3091

* Support PEP 810 lazy imports (new in Python 3.15). ``Import`` and
  ``ImportFrom`` nodes gain an ``is_lazy`` integer attribute, mirroring
  the ``ast`` field of the same name.

* Support PEP 798 comprehension unpacking (``{**d for d in dicts}``,
  new in Python 3.15).

* Fix astroid bootstrap crash on PyPy 7.3.22 (``TypeError: expected str, got
  getset_descriptor object``) by also catching ``TypeError`` from
  ``getattr(obj, alias)`` in ``InspectBuilder.object_build``. PyPy 7.3.22
  raises ``TypeError`` instead of ``AttributeError`` for unset getset
  descriptors like ``types.FunctionType.__text_signature__``, which made
  ``_astroid_bootstrapping()`` blow up on any call into astroid.

  Refs pylint-dev/pylint#10999

* Shorten ``import astroid`` by deferring imports only needed on cold paths.
  ``logging`` (used by ``modutils`` and ``raw_building`` solely to report
  stderr/stdout captured while importing a module) and ``pprint`` (used only
  to format debug ``__repr__`` / ``repr_tree`` output) are now imported
  lazily, and ``astroid.exceptions`` imports ``astroid.typing`` under
  ``TYPE_CHECKING``.

* Fix ``AttributeError`` crash in ``starred_assigned_stmts`` when a starred
  unpacking target is an attribute (e.g. ``for *o.attr, x in ...``) rather
  than a simple name.

  Closes #2646

* Fix ``AttributeError`` crash in the ``Arguments`` ``assigned_stmts``
  protocol when called without an inference context (the public
  ``assigned_stmts`` API defaults ``context`` to ``None``). Resolving a
  function's first parameter dereferenced ``context.boundnode`` while the
  matching ``context and ...`` guard a few lines below was missing; it now
  degrades to Uninferable.

* Fix ``AttributeError`` crash in ``ClassDef.infer_call_result`` when called
  through the public API without a context (it defaults to ``None``) for a
  class whose metaclass defines ``__call__``: the callee was assigned to
  ``context.callcontext.callee`` without checking that a call context exists.
  It is now guarded, matching the surrounding code.

* Wrap assignment expressions (``:=``) in parentheses when emitting
  ``as_string`` output so the rendered code remains syntactically valid in
  contexts such as comparisons, where Python requires the walrus expression
  to be parenthesized.

  Closes #2668

* Catch ``MemoryError``/``RecursionError`` (and ``ValueError``) when validating
  type comments with ``ast.parse``. Pathological type comments produced by
  fuzzers (e.g. ``# type: i{{{{{{{...``) previously crashed parsing with a
  ``MemoryError`` or ``RecursionError`` depending on the runtime; astroid now
  treats them as invalid type comments and skips them, mirroring the f-string
  fix from #2762.

  Closes #2993

* Bypass ``__init__`` in ``InferenceContext.clone()`` and write the slots
  directly. ``clone()`` is called ~85k times per pandas/frame.py pylint run;
  skipping the conditional defaults shaves measurable time off the hottest
  constructor in inference.

  Refs #1115

* Fix ``TypeError`` in ``brain_random`` when ``random.sample`` is called with a
  sequence containing nodes whose ``__init__`` does not accept ``lineno``
  (e.g. ``Module``). The clone helper now filters init params to those the
  class actually accepts.

  Closes #3043

* Fix ``RecursionError`` in ``_compute_mro()`` when circular class hierarchies
  are created through runtime name rebinding. Circular bases are now resolved
  to the original class instead of recursing.

  Closes #3023
  Closes pylint-dev/pylint#10821

* Changed `block_range` to consider `else` its own block, allowing `pylint` to apply
  disables to just the block.

  References pylint-dev/pylint#872

* Fix uncaught ``TokenError`` when building a class or function whose source
  slice is malformed. ``tokenize.generate_tokens`` may raise (e.g. on an
  unterminated bracket on Python < 3.12); position computation now treats such
  a node as having no position information instead of crashing.

  Closes #2527

* ``str()`` of a constant argument now infers the actual string value instead
  of always inferring ``""``. When every inference path of the argument
  resolves to ``Const`` values that stringify to the same string, ``infer_str``
  returns that string; otherwise it keeps falling back to ``Const("")``.

  Closes #2994

* Fix ``AttributeError`` crash when looking up a special method on a class
  whose explicit metaclass infers to a non-class node (e.g. a function). Such
  a metaclass has no MRO, so the dunder lookup now raises
  ``AttributeInferenceError`` instead of crashing.

  Closes #3063

* Fix ``AttributeError`` crash in ``ClassDef.getitem`` when ``__class_getitem__``
  resolves to a non-callable node (e.g. an ``AssignName``). ``getitem`` now
  raises ``AstroidTypeError`` in that case, consistent with its documented
  behaviour.

  Closes #3064

* Fix ``DuplicateBasesError`` crash in the enum brain when inferring an enum
  class with duplicate bases (e.g. ``class C(enum.Enum, enum.Enum)``).
  ``infer_enum_class`` now catches ``MroError`` and leaves such a malformed
  class untransformed.

  Closes #3065

* Fix ``InferenceError`` crash in ``ClassDef.slots()`` when ``__slots__`` is
  declared as an annotation without a value (e.g. ``__slots__: None``). Such a
  ``__slots__`` cannot be inferred, so ``slots()`` now returns ``None``.

  Closes #3067

* Fix ``TypeError`` crash in the enum brain when a functional ``Enum`` call
  has a non-string member name (e.g. ``Enum("e", (1,))``). Such a definition
  is invalid, so inference now falls back to the default instead of crashing.

  Closes #3068

* Fix detecting static/class methods and inspecting IntFlag types in
  GObject-based libraries (GLib, Gtk etc)

* Only inject the ``_HAS_DEFAULT_FACTORY`` sentinel into a module's locals when
  the generated dataclass ``__init__`` actually references it. Parsing a module
  containing a dataclass without any ``field(default_factory=...)`` no longer
  exposes an unexpected ``_HAS_DEFAULT_FACTORY`` name.

  Closes #2808

  * Fix a crash when inferring ``__func__`` on a bound method that proxies its  function directly,
    such as ``A.method.__func__`` for a classmethod, or a lambda assigned to a class attribute
    such as ``A().lam.__func__``.

  Closes pylint-dev/pylint#11198

* Add ``qname()`` and ``pytype()`` to the ``TypeVar``, ``ParamSpec``,
  ``TypeVarTuple`` and ``TypeAlias`` node classes, returning
  ``"typing.TypeVar"``, ``"typing.ParamSpec"``, ``"typing.TypeVarTuple"``
  and ``"typing.TypeAliasType"``. PEP 695 type parameters and type aliases
  are inferred as themselves, so callers that ask an inferred value for its
  type crashed with an ``AttributeError``, as ``FunctionDef.decoratornames()``
  did for ``@T`` inside ``class Basket[T]``.

  Refs #3115

* Infer the value of a data descriptor of a C-implemented class as unknown
  instead of as a class named after the attribute. Reading such an attribute,
  for instance ``exc.__traceback__.tb_frame`` or ``gen.gi_frame``, inferred a
  class, so the attributes of the value the descriptor returns were reported as
  missing. ``raw_building.object_build_datadescriptor()`` now returns an
  ``EmptyNode``.

  Closes pylint-dev/pylint#11218
