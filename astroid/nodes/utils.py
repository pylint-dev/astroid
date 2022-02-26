from typing import NamedTuple


class Position(NamedTuple):
    """Position with line and column information."""

    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
