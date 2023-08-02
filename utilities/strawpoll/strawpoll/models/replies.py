from __future__ import annotations

from pydantic import BaseModel

from .user import User


class Replies(BaseModel):
    id: str | None = None
    reply_to_id: str | None = None
    reference_id: str | None = None
    poll_id: str | None = None
    name: str | None = None
    user: User | None = None
    text: str | None = None
    like_count: int | None = None
    replies: list[Replies] = []
    created_at: int | None = None
    updated_at: int | None = None
