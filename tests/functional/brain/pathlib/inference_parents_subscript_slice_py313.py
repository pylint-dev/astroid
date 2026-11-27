# Test inference of ``pathlib.Path.parents``, accessed by slice.
from pathlib import Path

current_path = Path().resolve()
parent_path = current_path.parents[:2]
parent_path  # inferred: Tuple(())
