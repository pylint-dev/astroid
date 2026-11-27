from abc import ABC, abstractmethod
class Base(ABC):
    @abstractmethod
    def get_item(self) -> None: ...
class Middle[*Shape]:
    def get_item(self) -> None:
        raise NotImplementedError
# +2: inferred: ClassDef(ancestor_with_generic_typevartuple.Concrete)
# +1: inferred.ancestors: ancestor_with_generic_typevartuple.Middle, builtins.object, ancestor_with_generic_typevartuple.Base, abc.ABC
class Concrete[*Shape](Middle[*Shape], Base): pass
