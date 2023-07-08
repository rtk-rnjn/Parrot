from __future__ import annotations

import asyncio

import aiohttp

from .models import Comment, Poll, PollResults, User


class HTTPClient:
    BASE_API = "https://api.strawpoll.com/v3"

    session: aiohttp.ClientSession

    def __init__(self):
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Discord Bot - Parrot @ https://github.com/rtk-rnjn/Parrot"
        }

    @property
    def api_key(self) -> str:
        return self.api_key
    
    @api_key.setter
    def api_key(self, value: str) -> None:
        self.api_key = value
        self.headers["X-API-Key"] = value

    async def init(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        # sourcery skip: raise-specific-error
        async with self.session.request(method, self.BASE_API + endpoint, headers=self.headers, **kwargs) as resp:
            if resp.status >= 400:
                raise Exception(await resp.text())

            return {} if resp.status == 204 else await resp.json()

    async def fetch_poll(self, poll_id: int) -> Poll:
        data = await self._request("GET", f"/polls/{poll_id}")
        return Poll(**data)

    async def create_poll(self, poll: Poll) -> Poll:
        data = await self._request("POST", "/polls", json=poll._to_dict())
        return Poll(**data)

    async def update_poll(self, poll: Poll) -> Poll:
        data = await self._request("PUT", f"/polls/{poll.id}", json=poll._to_dict())
        return Poll(**data)

    async def delete_poll(self, poll_id: int) -> None:
        await self._request("DELETE", f"/polls/{poll_id}")

    async def fetch_poll_results(self, poll_id: int) -> PollResults:
        data = await self._request("GET", f"/polls/{poll_id}/results")
        return PollResults(**data)

    async def delete_poll_results(self, poll_id: int) -> None:
        await self._request("DELETE", f"/polls/{poll_id}/results")

    async def fetch_comment(self, poll_id: int) -> Comment:
        data = await self._request("GET", f"/polls/{poll_id}/comments")
        return Comment(**data)

    async def fetch_current_user(self) -> User:
        data = await self._request("GET", "/users/@me")
        return User(**data)

    async def update_current_user(self, user: User) -> User:
        data = await self._request("PATCH", "/users/@me", json=user._to_dict())
        return User(**data)

    
class StrawPollAPI(HTTPClient):
    def __init__(self, api_key: str):
        self.api_key = api_key