from typing import Literal, Optional

from .base_model import BaseModel


class UserMeta(BaseModel):
    # https://strawpoll.com/docs/api/strawpoll-api-v3.html#/schemas/UserMeta

    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def about(self) -> Optional[str]:
        return self._raw.get("about")

    @property
    def website(self) -> Optional[str]:
        return self._raw.get("website")

    @property
    def country_code(self) -> Optional[str]:
        return self._raw.get("country_code")

    @property
    def monthly_points(self) -> Optional[int]:
        return self._raw.get("monthly_points")

    @property
    def total_points(self) -> Optional[int]:
        return self._raw.get("total_points")


class UserConfig(BaseModel):
    # https://strawpoll.com/docs/api/strawpoll-api-v3.html#/schemas/UserConfig

    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def appearance(self) -> Optional[str]:
        return self._raw.get("appearance")

    @property
    def clock_type(self) -> Optional[str]:
        return self._raw.get("clock_type")

    @property
    def first_day_of_week(self) -> Optional[str]:
        """A value of 0 means Sunday, a value of 1 means Monday, etc."""
        return self._raw.get("first_day_of_week")

    @property
    def language(self) -> Optional[str]:
        return self._raw.get("language")

    @property
    def locale(self) -> Optional[str]:
        return self._raw.get("locale")

    @property
    def notification_delay(self) -> Optional[int]:
        """The time in minutes our system waits between sending two email notifications."""
        return self._raw.get("notification_delay")

    @property
    def notify_deadline(self) -> Optional[bool]:
        """Receive an update e-mail notification when a poll is closed. This should be renamed in future versions."""
        return self._raw.get("notify_deadline")

    @property
    def notify_meeting_votes(self) -> Optional[bool]:
        """Receive an update e-mail notification when a participant votes by name. This should be renamed in future versions."""
        return self._raw.get("notify_meeting_votes")

    @property
    def notify_poll_vote(self) -> Optional[bool]:
        """Receive an update e-mail notification when a participant votes anonymously. This should be renamed in future versions."""
        return self._raw.get("notify_poll_vote")

    @property
    def timezone(self) -> Optional[str]:
        return self._raw.get("timezone")


class User(BaseModel):
    # https://strawpoll.com/docs/api/strawpoll-api-v3.html#/schemas/User

    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def username(self) -> Optional[str]:
        return self._raw.get("username")

    @property
    def displayname(self) -> Optional[str]:
        return self._raw.get("displayname")

    @property
    def avatar_path(self) -> Optional[str]:
        return self._raw.get("avatar_path")

    @property
    def user_meta(self) -> Optional[UserMeta]:
        return UserMeta(**self._raw.get("user_meta", {}))

    @property
    def created_at(self) -> Optional[int]:
        return self._raw.get("created_at")

    @property
    def user_config(self) -> Optional[UserConfig]:
        return UserConfig(**self._raw.get("user_config", {}))


class PublicUser(BaseModel):
    def __init__(self, *, displayname: str, avatar_path: str, **kw):
        self._raw = {"displayname": displayname, "avatar_path": avatar_path, **kw}
        super().__init__(**self._raw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def username(self) -> Optional[str]:
        return self._raw.get("username")

    @property
    def displayname(self) -> str:
        return self._raw["displayname"]

    @property
    def avatar_path(self) -> str:
        return self._raw["avatar_path"]

    @property
    def subscription(self) -> Optional[Literal["free", "basic", "pro", "business"]]:
        return self._raw.get("subscription")

    @property
    def created_at(self) -> Optional[int]:
        return self._raw.get("created_at")

    @property
    def user_meta(self) -> Optional[UserMeta]:
        return UserMeta(**self._raw.get("user_meta", {}))


class UserActivity(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def event(self) -> Literal["create_poll", "vote_poll"]:
        return self._raw["event"]
    
    @property
    def payload(self) -> dict:
        return self._raw["payload"]
    
    @property
    def created_at(self) -> int:
        return self._raw["created_at"]