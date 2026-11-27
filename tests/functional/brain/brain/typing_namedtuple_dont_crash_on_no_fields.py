from typing import NamedTuple

Bar = NamedTuple("bar", [])

Bar()  # inferred: Instance(__astroid_synthetic.bar)
