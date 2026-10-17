from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

import discord
from discord.utils import MISSING

from ..parsing import ParserSupport
from .checks import evaluate
from .configs import CategoriesConfig, ChannelsConfig, DurationConfig, NoConfig, RolesConfig
from .mapping import _CONFIG_TYPES, ConditionConfig, ConditionType


class ConditionParseError(ValueError):
    """Raised when a condition configuration is invalid."""


parser = ParserSupport(ConditionParseError)


def _parse_no_config(_: Mapping[str, object]) -> ConditionConfig:
    return NoConfig()


def _parse_roles(data: Mapping[str, object]) -> ConditionConfig:
    return RolesConfig(
        roles=parser.require_int_tuple(data, "roles"),
        require_all=parser.optional_bool(data, "require_all", default=False),
    )


def _parse_channels(data: Mapping[str, object]) -> ConditionConfig:
    return ChannelsConfig(channels=parser.require_int_tuple(data, "channels"))


def _parse_categories(data: Mapping[str, object]) -> ConditionConfig:
    return CategoriesConfig(categories=parser.require_int_tuple(data, "categories"))


def _parse_duration(data: Mapping[str, object]) -> ConditionConfig:
    return DurationConfig(minutes=parser.require_int(data, "minutes", minimum=0))


Parser = Callable[[Mapping[str, object]], ConditionConfig]

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
_ROLE_TYPES = {ConditionType.IGNORED_ROLES, ConditionType.REQUIRED_ROLES}
_CHANNEL_TYPES = {ConditionType.IGNORED_CHANNELS, ConditionType.ACTIVE_CHANNELS}
_CATEGORY_TYPES = {ConditionType.IGNORED_CATEGORIES, ConditionType.ACTIVE_CATEGORIES}
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


def _parse_config(condition_type: ConditionType, data: Mapping[str, object]) -> ConditionConfig:
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
        data = parser.require_dict(value, "condition")

        raw_type = data.get("type")
        if not isinstance(raw_type, str):
            msg = "'type' must be a string"
            raise ConditionParseError(msg)

        try:
            condition_type = ConditionType(raw_type)
        except ValueError as exc:
            raise ConditionParseError("unknown condition type: " + repr(raw_type)) from exc

        raw_config = data.get("config", {})
        config_data = parser.require_dict(raw_config, "config")
        config = _parse_config(condition_type, config_data)

        return cls(type=condition_type, config=config)

    async def check(
        self,
        *,
        message: discord.Message = MISSING,
        member: discord.Member = MISSING,
        edited: bool | None = None,
        now: datetime | None = None,
    ) -> bool:
        if message is MISSING and member is MISSING:
            msg = "Either 'message' or 'member' must be provided."
            raise ValueError(msg)

        return evaluate(
            self.type,
            self.config,
            message=None if message is MISSING else message,
            member=None if member is MISSING else member,
            edited=edited,
            now=now,
        )


async def first_failed(
    conditions: Sequence[Condition],
    *,
    message: discord.Message = MISSING,
    member: discord.Member = MISSING,
    edited: bool | None = None,
    now: datetime | None = None,
) -> Condition | None:
    for condition in conditions:
        if not await condition.check(message=message, member=member, edited=edited, now=now):
            return condition
    return None
