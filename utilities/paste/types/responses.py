from __future__ import annotations

from datetime import datetime
from typing import TypedDict

__all__ = (
    "FileResponse",
    "PasteResponse",
)


class FileResponse(TypedDict):
    filename: str
    content: str
    loc: int
    charcount: int


class PasteResponse(TypedDict):
    id: str
    created_at: str
    expires: str | None
    last_edited: str | None
    views: int
    files: list[FileResponse]


class EditPasteResponse(TypedDict):
    id: str
    expires: datetime | None
