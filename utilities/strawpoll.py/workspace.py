from __future__ import annotations

from typing import Optional

from .base_model import BaseModel


class Workspace(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def name(self) -> Optional[str]:
        return self._raw.get("name")

    @property
    def member_count(self) -> Optional[int]:
        return self._raw.get("member_count")

    @property
    def created_at(self) -> Optional[int]:
        return self._raw.get("created_at")

    @property
    def updated_at(self) -> Optional[int]:
        return self._raw.get("updated_at")
