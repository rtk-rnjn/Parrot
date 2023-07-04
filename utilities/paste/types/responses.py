from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TypedDict

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
    expires: Optional[str]
    last_edited: Optional[str]
    views: int
    files: List[FileResponse]


class EditPasteResponse(TypedDict):
    id: str
    expires: Optional[datetime]
