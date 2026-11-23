# A first arg that is neither Instance nor ClassDef falls back to default inference.
#
# ``replace(<module>)`` raises TypeError at runtime, and the stdlib body the
# fallback walks cannot infer a return value either, so this is Uninferable.
import os
import dataclasses
dataclasses.replace(os)  # inferred: Uninferable
