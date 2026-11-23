# Test that _alias() calls can be inferred.
from typing import _alias
# +4: value: Call(_alias(int, float))
# +3: value.inferred: ClassDef(infer_typing_alias.x)
# +2: value.inferred.bases: [ClassDef(builtins.int)]
# +1: value.inferred.bases[0].name: 'int'
x = _alias(int, float)
