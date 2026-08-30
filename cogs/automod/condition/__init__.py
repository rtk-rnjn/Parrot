from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from .configs import (
    CategoriesConfig,
    ChannelsConfig,
    DurationConfig,
    NoConfig,
    RolesConfig,
)
from .mapping import _CONFIG_TYPES, ConditionConfig, ConditionType


class ConditionParseError(ValueError):
    """Raised when a condition configuration is invalid."""


def _require_dict(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConditionParseError(name + " must be an object")
    return value


def _require_int(
    data: Mapping[str, Any],
    key: str,
    *,
    minimum: int = 0,
) -> int:
    value = data.get(key)

    if not isinstance(value, int) or isinstance(value, bool):
        raise ConditionParseError(repr(key) + " must be an integer")

    if value < minimum:
        raise ConditionParseError(repr(key) + " must be >= " + str(minimum))

    return value


def _optional_bool(
    data: Mapping[str, Any],
    key: str,
    default: bool = False,
) -> bool:
    value = data.get(key, default)

    if not isinstance(value, bool):
        raise ConditionParseError(repr(key) + " must be a boolean")

    return value


def _require_int_tuple(
    data: Mapping[str, Any],
    key: str,
) -> tuple[int, ...]:
    value = data.get(key)

    if not isinstance(value, list):
        raise ConditionParseError(repr(key) + " must be an array of integers")

    out: list[int] = []

    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ConditionParseError(repr(key) + " must contain only integers")
        if item < 0:
            raise ConditionParseError(repr(key) + " values must be >= 0")
        out.append(item)

    return tuple(out)


def _parse_no_config(_: Mapping[str, Any]) -> ConditionConfig:
    return NoConfig()


def _parse_roles(data: Mapping[str, Any]) -> ConditionConfig:
    return RolesConfig(
        roles=_require_int_tuple(data, "roles"),
        require_all=_optional_bool(data, "require_all", default=False),
    )


def _parse_channels(data: Mapping[str, Any]) -> ConditionConfig:
    return ChannelsConfig(
        channels=_require_int_tuple(data, "channels"),
    )


def _parse_categories(data: Mapping[str, Any]) -> ConditionConfig:
    return CategoriesConfig(
        categories=_require_int_tuple(data, "categories"),
    )


def _parse_duration(data: Mapping[str, Any]) -> ConditionConfig:
    return DurationConfig(
        minutes=_require_int(data, "minutes", minimum=0),
    )


Parser = Callable[[Mapping[str, Any]], ConditionConfig]

_NO_CONFIG_TYPES = {
    ConditionType.IGNORE_BOTS,
    ConditionType.ONLY_BOTS,
    ConditionType.NEW_MESSAGE,
    ConditionType.EDITED_MESSAGE,
    ConditionType.ACTIVE_IN_THREADS,
    ConditionType.IGNORE_THREADS,
    ConditionType.IGNORE_FORWARDS,
    ConditionType.ONLY_FORWARDS,
}
_ROLE_TYPES = {
    ConditionType.IGNORED_ROLES,
    ConditionType.REQUIRED_ROLES,
}
_CHANNEL_TYPES = {
    ConditionType.IGNORED_CHANNELS,
    ConditionType.ACTIVE_CHANNELS,
}
_CATEGORY_TYPES = {
    ConditionType.IGNORED_CATEGORIES,
    ConditionType.ACTIVE_CATEGORIES,
}
_DURATION_TYPES = {
    ConditionType.ACCOUNT_AGE_ABOVE,
    ConditionType.ACCOUNT_AGE_BELOW,
    ConditionType.MEMBER_DURATION_ABOVE,
    ConditionType.MEMBER_DURATION_BELOW,
}

_PARSERS: dict[ConditionType, Parser] = {}

for t in _NO_CONFIG_TYPES:
    _PARSERS[t] = _parse_no_config
for t in _ROLE_TYPES:
    _PARSERS[t] = _parse_roles
for t in _CHANNEL_TYPES:
    _PARSERS[t] = _parse_channels
for t in _CATEGORY_TYPES:
    _PARSERS[t] = _parse_categories
for t in _DURATION_TYPES:
    _PARSERS[t] = _parse_duration


def _parse_config(
    condition_type: ConditionType,
    data: Mapping[str, Any],
) -> ConditionConfig:
    parser = _PARSERS.get(condition_type)

    if parser is None:
        raise ConditionParseError("No parser registered for condition type " + repr(condition_type.value))

    return parser(data)


@dataclass(frozen=True, slots=True)
class Condition:
    type: ConditionType
    config: ConditionConfig

    def __post_init__(self) -> None:
        expected = _CONFIG_TYPES[self.type]

        if not isinstance(self.config, expected):
            raise TypeError(repr(self.type.value) + " requires " + expected.__name__ + ", got " + type(self.config).__name__)

    @classmethod
    def parse(cls, value: object) -> Condition:
        data = _require_dict(value, "condition")

        raw_type = data.get("type")
        if not isinstance(raw_type, str):
            raise ConditionParseError("'type' must be a string")

        try:
            condition_type = ConditionType(raw_type)
        except ValueError as exc:
            raise ConditionParseError("unknown condition type: " + repr(raw_type)) from exc

        raw_config = data.get("config", {})
        config_data = _require_dict(raw_config, "config")
        config = _parse_config(condition_type, config_data)

        return cls(type=condition_type, config=config)
