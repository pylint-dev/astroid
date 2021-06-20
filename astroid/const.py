import enum
import sys

PY37 = sys.version_info >= (3, 7)
PY38 = sys.version_info >= (3, 8)
PY39 = sys.version_info >= (3, 9)
PY310 = sys.version_info >= (3, 10)


class Context(enum.Enum):
    Load = 1
    Store = 2
    Del = 3


# TODO Remove in 3.0 in favor of Context
Load = Context.Load  # pylint: disable=invalid-name
Store = Context.Store  # pylint: disable=invalid-name
Del = Context.Del  # pylint: disable=invalid-name
