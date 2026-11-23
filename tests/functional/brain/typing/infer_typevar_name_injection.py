# A crafted TypeVar name must not be spliced into the synthesized class.
from typing import TypeVar
TypeVar('T(EvilBase): #')  # inferred: ClassDef(.T(EvilBase): #)  # inferred.bases: []
