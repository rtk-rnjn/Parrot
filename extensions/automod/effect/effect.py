from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..parsing import ParserSupport
from .configs import (
    AlertConfig,
    BanConfig,
    DeleteMessagesConfig,
    MessageConfig,
    MuteConfig,
    NicknameConfig,
    NoConfig,
    RoleConfig,
    SendMessageConfig,
    SlowmodeConfig,
    TimeoutConfig,
    ViolationConfig,
)
from .enum import EffectType
from .mapping import _EFFECT_CONFIG_TYPES, EffectConfig
from .runner import EffectContext, EffectOutcome, run_one


class EffectParseError(ValueError):
    """Raised when an effect configuration is invalid."""


parser = ParserSupport(EffectParseError)


def _parse_no_config(_: Mapping[str, object]) -> EffectConfig:
    return NoConfig()


def _parse_violation(data: Mapping[str, object]) -> EffectConfig:
    return ViolationConfig(name=parser.optional_string(data, "name"))


def _parse_message(data: Mapping[str, object]) -> EffectConfig:
    return MessageConfig(message=parser.optional_string(data, "message"))


def _parse_ban(data: Mapping[str, object]) -> EffectConfig:
    return BanConfig(
        duration_minutes=parser.require_int(data, "duration_minutes", minimum=0),
        message=parser.optional_string(data, "message"),
        delete_days=parser.require_int(data, "delete_days", minimum=0),
    )


def _parse_mute(data: Mapping[str, object]) -> EffectConfig:
    return MuteConfig(
        duration_minutes=parser.require_int(data, "duration_minutes", minimum=0),
        message=parser.optional_string(data, "message"),
    )


def _parse_timeout(data: Mapping[str, object]) -> EffectConfig:
    return TimeoutConfig(
        duration_minutes=parser.require_int(data, "duration_minutes", minimum=0),
        message=parser.optional_string(data, "message"),
    )


def _parse_nickname(data: Mapping[str, object]) -> EffectConfig:
    return NicknameConfig(nickname=parser.optional_string(data, "nickname"))


def _parse_delete_messages(data: Mapping[str, object]) -> EffectConfig:
    return DeleteMessagesConfig(
        count=parser.require_int(data, "count", minimum=1),
        max_age_seconds=parser.require_int(data, "max_age_seconds", minimum=0),
    )


def _parse_role(data: Mapping[str, object]) -> EffectConfig:
    return RoleConfig(
        role_id=parser.optional_int_or_none(data, "role_id", minimum=0),
        duration_seconds=parser.require_int(data, "duration_seconds", minimum=0),
    )


def _parse_slowmode(data: Mapping[str, object]) -> EffectConfig:
    return SlowmodeConfig(
        duration_seconds=parser.require_int(data, "duration_seconds", minimum=0),
        ratelimit_seconds=parser.require_int(data, "ratelimit_seconds", minimum=0),
    )


def _parse_send_message(data: Mapping[str, object]) -> EffectConfig:
    message = data.get("message")
    if not isinstance(message, str):
        msg = "'message' must be a string"
        raise EffectParseError(msg)

    return SendMessageConfig(
        message=message,
        delete_after_seconds=parser.require_int(data, "delete_after_seconds", minimum=0),
        ping_user=parser.optional_bool(data, "ping_user", default=False),
        channel_id=parser.optional_int_or_none(data, "channel_id", minimum=0),
    )


def _parse_alert(data: Mapping[str, object]) -> EffectConfig:
    message = data.get("message")
    if not isinstance(message, str):
        msg = "'message' must be a string"
        raise EffectParseError(msg)

    return AlertConfig(message=message, channel_id=parser.optional_int_or_none(data, "channel_id", minimum=0))


Parser = Callable[[Mapping[str, object]], EffectConfig]

_PARSERS: dict[EffectType, Parser] = {
    EffectType.DELETE_MESSAGE: _parse_no_config,
    EffectType.ADD_VIOLATION: _parse_violation,
    EffectType.KICK_USER: _parse_message,
    EffectType.BAN_USER: _parse_ban,
    EffectType.MUTE_USER: _parse_mute,
    EffectType.WARN_USER: _parse_message,
    EffectType.SET_NICKNAME: _parse_nickname,
    EffectType.RESET_VIOLATIONS: _parse_violation,
    EffectType.DELETE_MULTIPLE_MESSAGES: _parse_delete_messages,
    EffectType.GIVE_ROLE: _parse_role,
    EffectType.ENABLE_SLOWMODE: _parse_slowmode,
    EffectType.REMOVE_ROLE: _parse_role,
    EffectType.SEND_MESSAGE: _parse_send_message,
    EffectType.TIMEOUT_USER: _parse_timeout,
    EffectType.SEND_ALERT: _parse_alert,
}


def _parse_config(effect_type: EffectType, data: Mapping[str, object]) -> EffectConfig:
    parser = _PARSERS.get(effect_type)

    if parser is None:
        raise EffectParseError("No parser registered for effect type " + repr(effect_type.value))

    return parser(data)


@dataclass(frozen=True, slots=True)
class Effect:
    type: EffectType
    config: EffectConfig

    def __post_init__(self) -> None:
        expected = _EFFECT_CONFIG_TYPES[self.type]

        if not isinstance(self.config, expected):
            raise TypeError(repr(self.type.value) + " requires " + expected.__name__ + ", got " + type(self.config).__name__)

    @classmethod
    def parse(cls, value: object) -> Effect:
        data = parser.require_dict(value, "effect")

        raw_type = data.get("type")
        if not isinstance(raw_type, str):
            msg = "'type' must be a string"
            raise EffectParseError(msg)

        try:
            effect_type = EffectType(raw_type)
        except ValueError as exc:
            raise EffectParseError("unknown effect type: " + repr(raw_type)) from exc

        raw_config = data.get("config", {})
        config_data = parser.require_dict(raw_config, "config")
        config = _parse_config(effect_type, config_data)

        return cls(type=effect_type, config=config)

    async def execute(self, ctx: EffectContext) -> EffectOutcome:
        return await run_one(self.type, self.config, ctx)
