from __future__ import annotations

from typing import TYPE_CHECKING

from ..mixin import DatabaseMixin
from .birthday import _UserBirthdayMixin
from .chess import _UserChessMixin
from .highlights import _UserHighlightsMixin
from .supercell import _UserSupercellMixin
from .timezone import _UserTimezoneMixin
from .todo import _UserTodoMixin
from .weather import _UserWeatherMixin

if TYPE_CHECKING:
    from ..models import UserConfiguration

__all__ = ("_UserMixin",)


class _UserMixin(
    _UserTimezoneMixin,
    _UserChessMixin,
    _UserHighlightsMixin,
    _UserTodoMixin,
    _UserBirthdayMixin,
    _UserSupercellMixin,
    _UserWeatherMixin,
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
            "supercell": {
                "clash_royale": None,
                "clash_of_clans": None,
            },
            "chess_com": None,
            "weather": {
                "location": {},
                "lang": "en",
                "units": "metric",
            },
        }

    def empty_user_config(self, user_id: int) -> UserConfiguration:
        """Compatibility alias for :meth:`create_user_configuration`."""
        return self.create_user_configuration(user_id)
