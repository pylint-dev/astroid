# Test inference of ``pathlib.Path.parents``, accessed by slice.
from pathlib import Path

current_path = Path().resolve()
parent_path = current_path.parents[:2]
# +2: <3.13: inferred: Instance(builtins.tuple)
# +1: >=3.14: inferred: Instance(builtins.tuple)
parent_path
