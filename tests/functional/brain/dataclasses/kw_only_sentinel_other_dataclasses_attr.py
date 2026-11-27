# Annotating with another ``dataclasses`` attribute (e.g. ``MISSING``)
# that also infers to ``builtins.sentinel`` on Python 3.15+ must not be
# treated as ``KW_ONLY``.
import dataclasses
from dataclasses import dataclass

@dataclass
class C:
    _: dataclasses.MISSING
    y: str

# +2: inferred: UnboundMethod(kw_only_sentinel_other_dataclasses_attr.C.__init__)
# +1: inferred.args: self, _: dataclasses.MISSING, y: str
C.__init__
