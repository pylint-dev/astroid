Add a brain for ``numpy.dtypes``, whose DType classes (``StringDType``, ``Float64DType``, ...) NumPy attaches at import time, so they can now be inferred. This fixes ``no-member`` false positives in pylint on code that uses them.

Closes #3289
Refs pylint-dev/pylint#9956
