from __future__ import annotations

import datetime

import aiohttp

from .http import HTTPClient
from .paste import File, Paste
from .utils import require_authentication

__all__ = ("Client",)


class Client:
    __slots__ = ("http",)

    def __init__(
        self,
        *,
        token: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.http: HTTPClient = HTTPClient(token=token, session=session)

    async def close(self) -> None:
        """|coro|.

        Closes the internal HTTP session and this client.
        """
        await self.http.close()

    async def create_paste(
        self,
        *,
        filename: str,
        content: str,
        password: str | None = None,
        expires: datetime.datetime | None = None,
    ) -> Paste:
        file = File(filename=filename, content=content)
        data = await self.http.create_paste(file=file, password=password, expires=expires)
        return Paste.from_data(data)

    async def create_multifile_paste(
        self,
        *,
        files: list[File],
        password: str | None = None,
        expires: datetime.datetime | None = None,
    ) -> Paste:
        data = await self.http.create_paste(files=files, password=password, expires=expires)
        return Paste.from_data(data)

    @require_authentication
    async def delete_paste(self, paste_id: str, /) -> None:
        await self.http.delete_pastes(paste_ids=[paste_id])

    @require_authentication
    async def delete_pastes(self, paste_ids: list[str], /) -> None:
        await self.http.delete_pastes(paste_ids=paste_ids)

    async def get_paste(self, paste_id: str, *, password: str | None = None) -> Paste:
        data = await self.http.get_paste(paste_id=paste_id, password=password)
        return Paste.from_data(data)

    @require_authentication
    async def get_user_pastes(self, *, limit: int = 100) -> list[Paste]:
        data = await self.http.get_my_pastes(limit=limit)

        return [Paste.from_data(x) for x in data]
