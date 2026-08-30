from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoConfig:
    pass


@dataclass(frozen=True, slots=True)
class ViolationConfig:
    name: str | None = None


@dataclass(frozen=True, slots=True)
class MessageConfig:
    message: str | None = None


@dataclass(frozen=True, slots=True)
class BanConfig:
    duration_minutes: int = 0
    message: str | None = None
    delete_days: int = 0


@dataclass(frozen=True, slots=True)
class MuteConfig:
    duration_minutes: int = 0
    message: str | None = None


@dataclass(frozen=True, slots=True)
class TimeoutConfig:
    duration_minutes: int = 0
    message: str | None = None


@dataclass(frozen=True, slots=True)
class NicknameConfig:
    nickname: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteMessagesConfig:
    count: int = 3
    max_age_seconds: int = 15


@dataclass(frozen=True, slots=True)
class RoleConfig:
    role_id: int | None = None
    duration_seconds: int = 0


@dataclass(frozen=True, slots=True)
class SlowmodeConfig:
    duration_seconds: int = 0
    ratelimit_seconds: int = 0


@dataclass(frozen=True, slots=True)
class SendMessageConfig:
    message: str = ""
    delete_after_seconds: int = 0
    ping_user: bool = False
    channel_id: int | None = None


@dataclass(frozen=True, slots=True)
class AlertConfig:
    message: str = ""
    channel_id: int | None = None
