from __future__ import annotations


class DatabaseMixin:
    """Base contract for database mixins.

    Mixins are stateless domain slices composed by ``DatabaseManager``. They
    may declare the typed collection and cache dependencies they use, expose
    readable public operations, and keep implementation helpers private.
    """

    __slots__ = ()
