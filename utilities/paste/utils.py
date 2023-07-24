from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar
from collections.abc import Callable

from .errors import AuthenticationRequired

if TYPE_CHECKING:
    from typing_extensions import ParamSpec
    from typing import Concatenate

    C = TypeVar("C", bound="Any")
    T = TypeVar("T")
    B = ParamSpec("B")

__all__ = ("MISSING", "require_authentication")


class _MissingSentinel:
    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "..."


MISSING: Any = _MissingSentinel()


def require_authentication(func: Callable[Concatenate[C, B], T]) -> Callable[Concatenate[C, B], T]:
    """A decorator to assure the `self` parameter of decorated methods has authentication set."""

    @wraps(func)
    def wrapper(item: C, *args: B.args, **kwargs: B.kwargs) -> T:
        if not item.http._authenticated:
            msg = "This method requires you to be authenticated to the API."
            raise AuthenticationRequired(msg)

        return func(item, *args, **kwargs)

    return wrapper
