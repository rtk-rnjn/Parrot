from __future__ import annotations

from typing import List, Literal, Optional

from .base_model import BaseModel
from .user import User, UserMeta


class Reply(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def reply_to_id(self) -> Optional[str]:
        return self._raw.get("reply_to_id")

    @property
    def reference_id(self) -> Optional[str]:
        return self._raw.get("reference_id")

    @property
    def poll_id(self) -> Optional[str]:
        return self._raw.get("poll_id")

    @property
    def name(self) -> Optional[str]:
        return self._raw.get("name")

    @name.setter
    def name(self, value: str):
        self._raw["name"] = value

    @property
    def user(self) -> Optional[User]:
        return User._from_dict(self._raw.get("user", {}))

    @user.setter
    def user(self, value: User):
        self._raw["user"] = value._to_dict()

    @property
    def text(self) -> Optional[str]:
        return self._raw.get("text")

    @property
    def like_count(self) -> Optional[int]:
        return self._raw.get("like_count")

    @property
    def replies(self) -> Optional[List[Reply]]:
        return [Reply._from_dict(x) for x in self._raw.get("replies", [])]

    @property
    def created_at(self) -> Optional[int]:
        return self._raw.get("created_at")

    @property
    def updated_at(self) -> Optional[int]:
        return self._raw.get("updated_at")


class Comment(Reply):
    pass
