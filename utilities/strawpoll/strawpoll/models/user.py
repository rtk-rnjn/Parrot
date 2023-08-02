from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

try:
    import orjson

    loads = orjson.loads
except ImportError:
    import json

    loads = json.loads


class UserMeta(BaseModel):
    about: str | None = None
    website: str | None = None
    country_code: str | None = None
    monthly_points: int | None = None
    total_points: int | None = None


class UserConfig(BaseModel):
    appearance: str | None = None
    clock_type: str | None = None
    first_day_of_week: int | None = None
    language: str | None = None
    locale: str | None = None
    notification_delay: int | None = None
    notify_deadline: bool | None = None
    notify_meeting_vote: bool | None = None
    notify_poll_vote: bool | None = None
    timezone: str | None = None


class _User(BaseModel):
    id: str | None = None
    username: str | None = None
    displayname: str | None
    avatar_path: str | None
    subscription: Literal["free", "basic", "pro", "business"] | None = "free"
    user_meta: UserMeta | None = None
    created_at: int | None = None


class User(_User):
    user_config: UserConfig | None = None


class PublicUser(_User):
    pass


class UserActivity(BaseModel):
    event: Literal["create_poll", "vote_poll"] | None = None
    payload: str | None = None
    created_at: int | None = None
