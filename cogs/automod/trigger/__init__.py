from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .configs import (
    AllCapsConfig,
    CountConfig,
    LengthConfig,
    ListConfig,
    NoConfig,
    RegexConfig,
    TimeWindowConfig,
    ViolationConfig,
)
from .mapping import _CONFIG_TYPES, TriggerConfig, TriggerType


class TriggerParseError(ValueError):
    """Raised when a trigger configuration is invalid."""


def _require_dict(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TriggerParseError(name + " must be an object")
    return value


def _require_int(
    data: Mapping[str, Any],
    key: str,
    *,
    minimum: int = 0,
) -> int:
    value = data.get(key)

    if not isinstance(value, int) or isinstance(value, bool):
        raise TriggerParseError(repr(key) + " must be an integer")

    if value < minimum:
        raise TriggerParseError(repr(key) + " must be >= " + str(minimum))

    return value


def _optional_bool(
    data: Mapping[str, Any],
    key: str,
    default: bool = False,
) -> bool:
    value = data.get(key, default)

    if not isinstance(value, bool):
        raise TriggerParseError(repr(key) + " must be a boolean")

    return value


def _optional_string(
    data: Mapping[str, Any],
    key: str,
) -> str | None:
    value = data.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise TriggerParseError(repr(key) + " must be a string")

    return value


def _parse_no_config(_: Mapping[str, Any]) -> TriggerConfig:
    return NoConfig()


def _parse_all_caps(data: Mapping[str, Any]) -> TriggerConfig:
    percentage = _require_int(data, "percentage", minimum=0)
    if percentage > 100:
        raise TriggerParseError("'percentage' must be <= 100")

    return AllCapsConfig(
        min_count=_require_int(data, "min_count"),
        percentage=percentage,
    )


def _parse_message_mentions(data: Mapping[str, Any]) -> TriggerConfig:
    return CountConfig(count=_require_int(data, "count", minimum=1))


def _parse_list(data: Mapping[str, Any]) -> TriggerConfig:
    return ListConfig(
        list_name=_optional_string(data, "list"),
    )


def _parse_regex(data: Mapping[str, Any]) -> TriggerConfig:
    regex = data.get("regex")
    if not isinstance(regex, str):
        raise TriggerParseError("'regex' must be a string")

    return RegexConfig(
        regex=regex,
    )


def _parse_time_window(data: Mapping[str, Any]) -> TriggerConfig:
    return TimeWindowConfig(
        count=_require_int(data, "count", minimum=1),
        within_minutes=_require_int(data, "within_minutes", minimum=1),
    )



def _parse_violations(data: Mapping[str, Any]) -> TriggerConfig:
    violation_name = data.get("violation_name")
    if not isinstance(violation_name, str):
        raise TriggerParseError("'violation_name' must be a string")

    return ViolationConfig(
        violation_name=violation_name,
        number_of_violations=_require_int(data, "number_of_violations", minimum=1),
        within_minutes=_require_int(data, "within_minutes", minimum=1),
    )


def _parse_length(data: Mapping[str, Any]) -> TriggerConfig:
    return LengthConfig(length=_require_int(data, "length", minimum=0))



Parser = Callable[[Mapping[str, Any]], TriggerConfig]

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
    TriggerType.X_VOILATION_IN_Y_MINUTES,
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


def _parse_config(
    trigger_type: TriggerType,
    data: Mapping[str, Any],
) -> TriggerConfig:
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
            error_message = repr(self.type.value) + " requires " + expected.__name__ + ", got " + type(self.config).__name__
            raise TypeError(error_message)

    @classmethod
    def parse(cls, value: object) -> Trigger:
        data = _require_dict(value, "trigger")
        raw_type = data.get("type")

        if not isinstance(raw_type, str):
            raise TriggerParseError("'type' must be a string")

        try:
            trigger_type = TriggerType(raw_type)
        except ValueError as exc:
            raise TriggerParseError("unknown trigger type: " + repr(raw_type)) from exc

        raw_config = data.get("config", {})
        config_data = _require_dict(raw_config, "config")
        config = _parse_config(trigger_type, config_data)

        return cls(type=trigger_type, config=config)
