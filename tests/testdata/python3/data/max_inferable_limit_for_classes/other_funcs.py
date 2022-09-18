from operator import attrgetter

from .nodes import roles


class HasCacheKey:
    ...


class HasMemoized:
    ...


class MemoizedHasCacheKey(HasCacheKey, HasMemoized):
    ...


class ClauseElement(MemoizedHasCacheKey):
    ...


class ReturnsRows(roles.ReturnsRowsRole, ClauseElement):
    ...


class Selectable(ReturnsRows):
    ...


class FromClause(roles.AnonymizedFromClauseRole, Selectable):
    c = property(attrgetter("columns"))
