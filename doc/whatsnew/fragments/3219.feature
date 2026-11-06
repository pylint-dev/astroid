A C accelerator module is now read from the pure Python twin the standard
library ships for it, ``_decimal`` from ``_pydecimal`` and ``_io`` from
``_pyio``, instead of being introspected as a compiled module. Introspection
cannot see signatures, bodies or return values, so ``open("apple.txt")`` and
``Decimal("1").sqrt()`` were uninferable and are not anymore. The ``datetime``
and ``decimal`` brains stay: PyPy ships no ``_decimal`` at all, and there a
redirection has no C module to start from.

The classes of the ``datetime`` module are now named after ``datetime``. They
were named after ``_pydatetime``, the implementation they are read from, so
``datetime.time`` was ``_pydatetime.time`` and anything matching on the name had
to know that. The brain now hands the module to the extender instead of a star
import of it, and the extender adopts the classes it is given.

The classes that the standard library re-exports from a C accelerator module
with a star import are now inferred. ``_ast.AST.__module__`` is ``"ast"``, not
``"_ast"``, so ``AST`` was recorded inside ``_ast`` as an import from ``ast``
while ``ast.py`` only gets the name through ``from _ast import *``. The two
modules pointed at each other and everything defined that way was
``Uninferable``. This also fixes ``decimal.Decimal``, ``ssl.SSLError``,
``sqlite3.Connection`` and ``weakref.ref``, among others. The special case that
``io`` needed before Python 3.12, where the disagreement ran the other way
around, is now handled by the same code.

Refs #3219
Refs pylint-dev/pylint#11252
