from __future__ import annotations
from typing import TYPE_CHECKING
from .birthday import _UserBirthdayMixin  # noqa
from .highlights import _UserHighlightsMixin  # noqa
from .timezone import _UserTimezoneMixin  # noqa
from .todo import _UserTodoMixin  # noqa

if TYPE_CHECKING:
    from ..models import UserConfiguration

__all__ = ("_UserMixin",)


class _UserMixin(
    _UserTimezoneMixin,
    _UserHighlightsMixin,
    _UserTodoMixin,
    _UserBirthdayMixin,
):
    def empty_user_config(self, user_id: int) -> UserConfiguration:
        return {
            "_id": user_id,
            "birthday": "",
            "timezone": "",
            "todo_items": [],
            "highlights": [],
            "highlight_ignored_users": [],
        }
