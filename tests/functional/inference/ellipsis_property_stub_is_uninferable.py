# Regression test for https://github.com/pylint-dev/pylint/issues/8138.
from typing import TYPE_CHECKING, Type

class Banana:
    pass

class Basket:
    if TYPE_CHECKING:
        @property
        def banana(self) -> Type[Banana]: ...

Basket().banana  # inferred: Uninferable
