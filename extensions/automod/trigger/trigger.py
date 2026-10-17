from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping
from dataclasses import dataclass

import discord
from discord.utils import MISSING

from ..constants import MAX_PERCENTAGE
from ..parsing import ParserSupport
from .checks import HANDLERS, TriggerEnv, TriggerEvent, evaluate
from .configs import AllCapsConfig, CountConfig, LengthConfig, ListConfig, NoConfig, RegexConfig, TimeWindowConfig, ViolationConfig
from .mapping import _CONFIG_TYPES, TriggerConfig, TriggerType


class TriggerParseError(ValueError):
    """Raised when a trigger configuration is invalid."""


parser = ParserSupport(TriggerParseError)


def _parse_no_config(_: Mapping[str, object]) -> TriggerConfig:
    return NoConfig()


def _parse_all_caps(data: Mapping[str, object]) -> TriggerConfig:
    percentage = parser.require_int(data, "percentage", minimum=0)
    if percentage > MAX_PERCENTAGE:
        msg = "'percentage' must be <= 100"
        raise TriggerParseError(msg)

    return AllCapsConfig(min_count=parser.require_int(data, "min_count"), percentage=percentage)


def _parse_message_mentions(data: Mapping[str, object]) -> TriggerConfig:
    return CountConfig(count=parser.require_int(data, "count", minimum=1))


def _parse_list(data: Mapping[str, object]) -> TriggerConfig:
    return ListConfig(list_name=parser.optional_string(data, "list"))


def _parse_regex(data: Mapping[str, object]) -> TriggerConfig:
    regex = data.get("regex")
    if not isinstance(regex, str):
        msg = "'regex' must be a string"
        raise TriggerParseError(msg)

    return RegexConfig(regex=regex)


def _parse_time_window(data: Mapping[str, object]) -> TriggerConfig:
    return TimeWindowConfig(
        count=parser.require_int(data, "count", minimum=1),
        within_minutes=parser.require_int(data, "within_minutes", minimum=1),
    )


def _parse_violations(data: Mapping[str, object]) -> TriggerConfig:
    violation_name = data.get("violation_name")
    if not isinstance(violation_name, str):
        msg = "'violation_name' must be a string"
        raise TriggerParseError(msg)

    return ViolationConfig(
        violation_name=violation_name,
        number_of_violations=parser.require_int(data, "number_of_violations", minimum=1),
        within_minutes=parser.require_int(data, "within_minutes", minimum=1),
    )


def _parse_length(data: Mapping[str, object]) -> TriggerConfig:
    return LengthConfig(length=parser.require_int(data, "length", minimum=0))


Parser = Callable[[Mapping[str, object]], TriggerConfig]

_NO_CONFIG_TYPES = {
    TriggerType.ANY_LINK,
    TriggerType.SERVER_INVITES,
    TriggerType.JOIN_USERNAME_INVITE,
    TriggerType.NEW_MEMBER,
    TriggerType.MESSAGE_WITHOUT_ATTACHMENTS,
    TriggerType.MESSAGE_WITH_ATTACHMENTS,
    TriggerType.FLAGGED_SCAM_LINKS,
}
_LIST_TYPES = {
    TriggerType.WORD_DENYLIST,
    TriggerType.WORD_ALLOWLIST,
    TriggerType.WEBSITE_DENYLIST,
    TriggerType.WEBSITE_ALLOWLIST,
    TriggerType.NICKNAME_WORD_ALLOWLIST,
    TriggerType.NICKNAME_WORD_DENYLIST,
    TriggerType.JOIN_USERNAME_WORD_ALLOWLIST,
    TriggerType.JOIN_USERNAME_WORD_DENYLIST,
}
_REGEX_TYPES = {
    TriggerType.MESSAGE_REGEX,
    TriggerType.MESSAGE_NOT_REGEX,
    TriggerType.NICKNAME_REGEX,
    TriggerType.NICKNAME_NOT_REGEX,
    TriggerType.JOIN_USERNAME_REGEX,
    TriggerType.JOIN_USERNAME_NOT_REGEX,
}
_TIME_WINDOW_TYPES = {
    TriggerType.X_CONSECUTIVE_IDENTICAL_MESSAGES,
    TriggerType.X_USER_LINKS_IN_Y_MINUTES,
    TriggerType.X_CHANNEL_LINKS_IN_Y_MINUTES,
    TriggerType.X_VIOLATION_IN_Y_MINUTES,
    TriggerType.X_USER_MESSAGE_IN_Y_MINUTES,
    TriggerType.X_CHANNEL_MESSAGE_IN_Y_MINUTES,
    TriggerType.X_USER_MESSAGE_MENTIONS_IN_Y_MINUTES,
    TriggerType.X_CHANNEL_MESSAGE_MENTIONS_IN_Y_MINUTES,
}

_PARSERS: dict[TriggerType, Parser] = {
    TriggerType.ALL_CAPS: _parse_all_caps,
    TriggerType.MESSAGE_MENTIONS: _parse_message_mentions,
    TriggerType.X_USER_ATTACHMENTS_IN_Y_MINUTES: _parse_time_window,
    TriggerType.X_CHANNEL_ATTACHMENTS_IN_Y_MINUTES: _parse_time_window,
    TriggerType.VIOLATIONS: _parse_violations,
    TriggerType.MESSAGE_LENGTH_GT: _parse_length,
    TriggerType.MESSAGE_LENGTH_LT: _parse_length,
}

for t in _NO_CONFIG_TYPES:
    _PARSERS[t] = _parse_no_config
for t in _LIST_TYPES:
    _PARSERS[t] = _parse_list
for t in _REGEX_TYPES:
    _PARSERS[t] = _parse_regex
for t in _TIME_WINDOW_TYPES:
    _PARSERS[t] = _parse_time_window


def _parse_config(trigger_type: TriggerType, data: Mapping[str, object]) -> TriggerConfig:
    parser = _PARSERS.get(trigger_type)
    if parser is None:
        raise TriggerParseError("No parser registered for trigger type " + repr(trigger_type.value))
    return parser(data)


@dataclass(frozen=True, slots=True)
class Trigger:
    type: TriggerType
    config: TriggerConfig

    def __post_init__(self) -> None:
        expected = _CONFIG_TYPES[self.type]
        if not isinstance(self.config, expected):
            error_message = f"{self.type.value!r} requires {expected.__name__!r}, got {type(self.config).__name__!r}"
            raise TypeError(error_message)

    @classmethod
    def parse(cls, value: object) -> Trigger:
        data = parser.require_dict(value, "trigger")
        raw_type = data.get("type")

        if not isinstance(raw_type, str):
            msg = "'type' must be a string"
            raise TriggerParseError(msg)

        try:
            trigger_type = TriggerType(raw_type)
        except ValueError as exc:
            raise TriggerParseError("unknown trigger type: " + repr(raw_type)) from exc

        raw_config = data.get("config", {})
        config_data = parser.require_dict(raw_config, "config")
        config = _parse_config(trigger_type, config_data)

        return cls(type=trigger_type, config=config)

    @property
    def event(self) -> TriggerEvent:
        return HANDLERS[self.type].event

    async def check(
        self,
        *,
        message: discord.Message = MISSING,
        member: discord.Member = MISSING,
        env: TriggerEnv | None = None,
        key: Hashable | None = None,
    ) -> bool:
        if message is MISSING and member is MISSING:
            msg = "Either 'message' or 'member' must be provided."
            raise ValueError(msg)

        return await evaluate(
            self.type,
            self.config,
            message=None if message is MISSING else message,
            member=None if member is MISSING else member,
            env=env,
            key=key,
        )
