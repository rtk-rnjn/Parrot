from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Optional


if TYPE_CHECKING:
    from typing_extensions import Self

    from .types.responses import FileResponse, PasteResponse

__all__ = (
    "File",
    "Paste",
)


class File:
    _lines_of_code: int
    _character_count: int

    __slots__ = (
        "filename",
        "content",
        "_lines_of_code",
        "_character_count",
    )

    def __init__(
        self,
        *,
        filename: str,
        content: str,
    ) -> None:
        self.filename: str = filename
        self.content: str = content

    @property
    def lines_of_code(self) -> int:
        return self._lines_of_code

    @property
    def character_count(self) -> int:
        return self._character_count

    @classmethod
    def from_data(cls, payload: FileResponse, /) -> Self:
        self = cls(
            content=payload["content"],
            filename=payload["filename"],
        )
        self._lines_of_code = payload["loc"]
        self._character_count = payload["charcount"]

        return self

    def to_dict(self) -> dict[str, Any]:
        ret: dict[str, Any] = {"content": self.content, "filename": self.filename}

        return ret


class Paste:
    _last_edited: Optional[datetime.datetime]
    _expires: Optional[datetime.datetime]
    _views: Optional[int]

    __slots__ = (
        "id",
        "author_id",
        "created_at",
        "files",
        "notice",
        "_expires",
        "_views",
        "_last_edited",
    )

    def __init__(
        self,
        *,
        id: str,
        created_at: str,
        files: list[File],
    ) -> None:
        self.id: str = id
        self.created_at: datetime.datetime = datetime.datetime.fromisoformat(created_at)
        self.files: list[File] = files

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
        return f"<Paste id={self.id!r} files={len(self.files)}>"

    @property
    def url(self) -> str:
        return f"https://mystb.in/{self.id}"

    @property
    def last_edited(self) -> Optional[datetime.datetime]:
        return self._last_edited

    @property
    def expires(self) -> Optional[datetime.datetime]:
        return self._expires

    @property
    def views(self) -> Optional[int]:
        return self._views

    @classmethod
    def from_data(cls, payload: PasteResponse, /) -> Self:
        files = [File.from_data(data) for data in payload["files"]]
        self = cls(
            id=payload["id"],
            created_at=payload["created_at"],
            files=files,
        )
        self._views = payload.get("views")
        if last_edited := payload.get("last_edited"):
            self._last_edited = datetime.datetime.fromisoformat(last_edited)
        else:
            self._last_edited = None

        if expires := payload.get("expires"):
            self._expires = datetime.datetime.fromisoformat(expires)
        else:
            self._expires = None

        return self