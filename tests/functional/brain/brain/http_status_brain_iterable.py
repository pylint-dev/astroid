# Astroid inference of `http.HTTPStatus` is an iterable subclass of `enum.IntEnum`
import http
# +3: inferred: ClassDef(http.HTTPStatus)
# +2: inferred.ancestors: enum.IntEnum, builtins.int, builtins.object, enum.ReprEnum, enum.Enum
# +1: inferred.getattr(__iter__): BoundMethod(enum.EnumType.__iter__)
http.HTTPStatus
