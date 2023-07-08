from __future__ import annotations

from typing import List, Literal, Optional

from .base_model import BaseModel


class Media(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")
    
    @id.setter
    def id(self, value: str):
        self._raw["id"] = value

    @property
    def type(self) -> Literal["image"]:
        return self._raw["type"]
    
    @type.setter
    def type(self, value: Literal["image"]):
        self._raw["type"] = value

    @property
    def source(self) -> Optional[str]:
        return self._raw.get("source")
    
    @source.setter
    def source(self, value: str):
        self._raw["source"] = value

    @property
    def url(self) -> Optional[str]:
        return self._raw.get("url")
    
    @url.setter
    def url(self, value: str):
        self._raw["url"] = value

    @property
    def width(self) -> Optional[int]:
        return self._raw.get("width")
    
    @width.setter
    def width(self, value: int):
        self._raw["width"] = value

    @property
    def height(self) -> Optional[int]:
        return self._raw.get("height")
    
    @height.setter
    def height(self, value: int):
        self._raw["height"] = value

    @property
    def created_at(self) -> Optional[int]:
        return self._raw.get("created_at")

    @property
    def updated_at(self) -> Optional[int]:
        return self._raw.get("updated_at")
