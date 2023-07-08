from __future__ import annotations

from io import BytesIO
from typing import Literal

from .base_model import BaseModel


class Upload(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def file(self) -> BytesIO:
        return self._raw["file"]

    @file.setter
    def file(self, value: BytesIO):
        self._raw["file"] = value

    @property
    def type(self) -> Literal["user_avatar", "poll_cover", "poll_option", "poll_option"]:
        return self._raw["type"]

    @type.setter
    def type(self, value: str):
        self._raw["type"] = value
