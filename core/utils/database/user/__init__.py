from __future__ import annotations

from typing import TYPE_CHECKING

from ..mixin import DatabaseMixin
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
    DatabaseMixin,
):
    def create_user_configuration(self, user_id: int) -> UserConfiguration:
        return {
            "_id": user_id,
            "birthday": "",
            "timezone": "",
            "todo_items": [],
            "highlights": [],
            "highlight_ignored_users": [],
        }

    def empty_user_config(self, user_id: int) -> UserConfiguration:
        """Compatibility alias for :meth:`create_user_configuration`."""
        return self.create_user_configuration(user_id)
