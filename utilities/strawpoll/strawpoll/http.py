from __future__ import annotations

from typing import Literal

import aiohttp
from pydantic import BaseModel

from .models import Pagination, Poll, PollResults, Replies, User, UserActivity
from .utils import flat_model_to_dict


class HTTPError(Exception):
    pass


class HTTPClient:
    BASE_URL: str = "https://api.strawpoll.com/v3"

    def __init__(self, token: str):
        self.token = token
        self.headers = {"Content-Type": "application/json", "X-API-Key": self.token}
        self.session = None

        self._cached_polls: dict[str, Poll] = {}

    def __repr__(self) -> str:
        return f"<HTTPClient token='...{self.token[:5]}' headers={self.headers!r}>"

    async def init(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    def parse_model(self, model: BaseModel):
        return flat_model_to_dict(model)

    async def request(self, method: str, endpoint: str, **kwargs) -> dict:
        assert self.session is not None

        async with self.session.request(
            method,
            self.BASE_URL + endpoint,
            headers=self.headers,
            **kwargs,
        ) as resp:
            if resp.status >= 400:
                raise HTTPError(await resp.text())

            return await resp.json()

    # Polls

    async def fetch_poll(self, poll_id: str) -> Poll:
        data = await self.request("GET", f"/polls/{poll_id}")
        poll = Poll(**data)
        self._cached_polls[poll_id] = poll
        return poll

    def get_poll(self, poll_id: str) -> Poll | None:
        return self._cached_polls.get(poll_id)

    async def create_poll(self, poll: Poll) -> Poll:
        data = await self.request("POST", "/polls", json=self.parse_model(poll))
        poll = Poll(**data)
        self._cached_polls[poll.id] = poll  # type: ignore  # newly created poll always has an id
        return poll

    async def update_poll(self, poll: Poll) -> Poll:
        data = await self.request(
            "PUT",
            f"/polls/{poll.id}",
            json=self.parse_model(poll),
        )
        poll = Poll(**data)
        self._cached_polls[poll.id] = poll  # type: ignore  # newly created poll always has an id
        return poll

    async def delete_poll(self, poll_id: str) -> None:
        await self.request("DELETE", f"/polls/{poll_id}")

    async def fetch_poll_results(self, poll_id: str) -> PollResults:
        data = await self.request("GET", f"/polls/{poll_id}/results")
        return PollResults(**data)

    async def delete_poll_results(self, poll_id: str) -> None:
        await self.request("DELETE", f"/polls/{poll_id}/results")

    async def fetch_poll_comment(self, poll_id: str) -> Replies:
        data = await self.request("GET", f"/polls/{poll_id}/comments")
        return Replies(**data)

    # Current User

    async def fetch_current_user(self) -> User:
        data = await self.request("GET", "/users/@me")
        return User(**data)

    async def update_current_user(self, user: User) -> User:
        data = await self.request("PATCH", "/users/@me", json=self.parse_model(user))
        return User(**data)

    async def list_current_user_poll(
        self,
        type: Literal["created", "participated"],
    ) -> tuple[list[Poll], Pagination]:
        data = await self.request("GET", "/users/@me/polls", params={"type": type})
        pages = Pagination(**data["pagination"])
        polls = [Poll(**d) for d in data["data"]]
        return polls, pages

    async def list_current_user_activities(
        self,
    ) -> tuple[list[UserActivity], Pagination]:
        data = await self.request("GET", "/users/@me/activities")
        pages = Pagination(**data["pagination"])
        activity = [UserActivity(**d) for d in data["data"]]
        return activity, pages

    # User

    async def fetch_user(self, user_id: str) -> User:
        data = await self.request("GET", f"/users/{user_id}")
        return User(**data)

    async def fetch_user_polls(self, user_id: str) -> tuple[list[Poll], Pagination]:
        data = await self.request("GET", f"/users/{user_id}/polls")
        pages = Pagination(**data["pagination"])
        polls = [Poll(**d) for d in data["data"]]
        return polls, pages

    # Comment

    async def create_comment(self, reply: Replies) -> Replies:
        data = await self.request("POST", "/comments", json=self.parse_model(reply))
        return Replies(**data)

    async def fetch_comment(self, comment_id: str) -> Replies:
        data = await self.request("GET", f"/comments/{comment_id}")
        return Replies(**data)

    async def update_comment(self, comment_id: str) -> Replies:
        data = await self.request("PUT", f"/comments/{comment_id}")
        return Replies(**data)

    async def delete_comment(self, comment_id: str) -> None:
        await self.request("PUT", f"/comments/{comment_id}")
