from __future__ import annotations

from collections.abc import Awaitable
from typing import Protocol

import discord

from ..constants import MAX_SELECTION, MENTION_PREVIEW
from ..parsing import format_duration
from ..parsing import parse_duration as parse_time_duration
from . import _CONFIG_TYPES as CONFIG_TYPES
from . import CategoriesConfig, ChannelsConfig, ConditionConfig, ConditionType, DurationConfig, NoConfig, RolesConfig

CONDITION_GROUP = {
    "members": [
        ConditionType.IGNORED_ROLES,
        ConditionType.REQUIRED_ROLES,
        ConditionType.ACCOUNT_AGE_ABOVE,
        ConditionType.ACCOUNT_AGE_BELOW,
        ConditionType.MEMBER_DURATION_ABOVE,
        ConditionType.MEMBER_DURATION_BELOW,
        ConditionType.IGNORE_BOTS,
        ConditionType.ONLY_BOTS,
    ],
    "locations": [
        ConditionType.IGNORED_CHANNELS,
        ConditionType.ACTIVE_CHANNELS,
        ConditionType.IGNORED_CATEGORIES,
        ConditionType.ACTIVE_CATEGORIES,
        ConditionType.ACTIVE_IN_THREADS,
        ConditionType.IGNORE_THREADS,
    ],
    "messages": [
        ConditionType.NEW_MESSAGE,
        ConditionType.EDITED_MESSAGE,
        ConditionType.IGNORE_FORWARDS,
        ConditionType.ONLY_FORWARDS,
    ],
}

CONDITION_GROUP_NAMES = {
    "members": {
        "name": "Members",
        "description": "Conditions based on who sent the message.",
        "emoji": "\N{BUST IN SILHOUETTE}",
    },
    "locations": {
        "name": "Locations",
        "description": "Conditions based on where the message was sent.",
        "emoji": "\N{PUSHPIN}",
    },
    "messages": {
        "name": "Messages",
        "description": "Conditions based on the type of message.",
        "emoji": "\N{SPEECH BALLOON}",
    },
}

CHANNEL_TYPES = [
    discord.ChannelType.text,
    discord.ChannelType.voice,
    discord.ChannelType.news,
    discord.ChannelType.forum,
    discord.ChannelType.media,
    discord.ChannelType.stage_voice,
]

CONFLICT_PAIRS = [
    (ConditionType.IGNORE_BOTS, ConditionType.ONLY_BOTS),
    (ConditionType.NEW_MESSAGE, ConditionType.EDITED_MESSAGE),
    (ConditionType.ACTIVE_IN_THREADS, ConditionType.IGNORE_THREADS),
    (ConditionType.IGNORE_FORWARDS, ConditionType.ONLY_FORWARDS),
]

CONFLICTS: dict[ConditionType, set[ConditionType]] = {a: {b} for a, b in CONFLICT_PAIRS} | {b: {a} for a, b in CONFLICT_PAIRS}


class ConditionsCallback(Protocol):
    async def __call__(
        self,
        interaction: discord.Interaction[discord.Client],
        condition: ConditionType,
        config: ConditionConfig,
    ) -> Awaitable[None]: ...


class ConfigError(Exception):
    pass


def pretty(condition: ConditionType) -> str:
    return condition.value.replace("_", " ").title()


def short_doc(condition: ConditionType) -> str | None:
    LIMIT = 100
    doc = (condition.__doc__ or "").strip()
    if not doc:
        return None
    return doc if len(doc) <= LIMIT else doc[: LIMIT - 1] + "\N{HORIZONTAL ELLIPSIS}"


def labeled(text: str, component: discord.ui.Item, *, description: str | None = None) -> discord.ui.Label:
    return discord.ui.Label(text=text, description=description, component=component)


def parse_duration(text: str) -> int:
    return parse_time_duration(text, error=ConfigError, name="Duration", units="mhdw", minimum=1)


def mentions(ids: tuple[int, ...], template: str) -> str:
    shown = ", ".join(template.format(id_) for id_ in ids[:MENTION_PREVIEW])
    extra = len(ids) - MENTION_PREVIEW
    return f"{shown} +{extra} more" if extra > 0 else shown


def describe(config: ConditionConfig) -> str:
    match config:
        case RolesConfig(roles=roles, require_all=require_all):
            return mentions(roles, "<@&{}>") + (" (all required)" if require_all else "")
        case ChannelsConfig(channels=channels):
            return mentions(channels, "<#{}>")
        case CategoriesConfig(categories=categories):
            return mentions(categories, "<#{}>")
        case DurationConfig(minutes=minutes):
            return format_duration(minutes)
        case _:
            return ""


class ConfigModal(discord.ui.Modal):
    def __init__(self, condition: ConditionType, callback: ConditionsCallback) -> None:
        super().__init__(title=pretty(condition)[:45])
        self.condition = condition
        self.config_callback = callback

    def build_config(self) -> ConditionConfig:
        raise NotImplementedError

    async def on_submit(self, interaction: discord.Interaction[discord.Client]) -> None:
        try:
            config = self.build_config()
        except ConfigError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await self.config_callback(interaction, self.condition, config)

    async def on_error(self, interaction: discord.Interaction[discord.Client], error: Exception) -> None:
        message = "Something went wrong saving that config."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        raise error


class RolesModal(ConfigModal):
    def __init__(self, condition: ConditionType, callback: ConditionsCallback) -> None:
        super().__init__(condition, callback)
        self.roles = discord.ui.RoleSelect(placeholder="Select roles...", min_values=1, max_values=MAX_SELECTION)
        self.add_item(labeled("Roles", self.roles, description=short_doc(condition)))

        self.require_all: discord.ui.Checkbox | None = None
        if condition is ConditionType.REQUIRED_ROLES:
            self.require_all = discord.ui.Checkbox()
            self.add_item(labeled("Require all roles", self.require_all, description="Off means any one of them is enough."))

    def build_config(self) -> RolesConfig:
        return RolesConfig(
            roles=tuple(role.id for role in self.roles.values),
            require_all=bool(self.require_all and self.require_all.value),
        )


class ChannelsModal(ConfigModal):
    def __init__(self, condition: ConditionType, callback: ConditionsCallback) -> None:
        super().__init__(condition, callback)
        self.channels = discord.ui.ChannelSelect(
            placeholder="Select channels...",
            channel_types=CHANNEL_TYPES,
            min_values=1,
            max_values=MAX_SELECTION,
        )
        self.add_item(labeled("Channels", self.channels, description=short_doc(condition)))

    def build_config(self) -> ChannelsConfig:
        return ChannelsConfig(channels=tuple(channel.id for channel in self.channels.values))


class CategoriesModal(ConfigModal):
    def __init__(self, condition: ConditionType, callback: ConditionsCallback) -> None:
        super().__init__(condition, callback)
        self.categories = discord.ui.ChannelSelect(
            placeholder="Select categories...",
            channel_types=[discord.ChannelType.category],
            min_values=1,
            max_values=MAX_SELECTION,
        )
        self.add_item(labeled("Categories", self.categories, description=short_doc(condition)))

    def build_config(self) -> CategoriesConfig:
        return CategoriesConfig(categories=tuple(category.id for category in self.categories.values))


class DurationModal(ConfigModal):
    def __init__(self, condition: ConditionType, callback: ConditionsCallback) -> None:
        super().__init__(condition, callback)
        self.duration = discord.ui.TextInput(placeholder="e.g. 30m, 12h, 7d, 2w, 1d 12h", max_length=30)
        self.add_item(labeled("Duration", self.duration, description=short_doc(condition)))

    def build_config(self) -> DurationConfig:
        return DurationConfig(minutes=parse_duration(self.duration.value))


MODAL_FOR_CONFIG: dict[type[ConditionConfig], type[ConfigModal]] = {
    RolesConfig: RolesModal,
    ChannelsConfig: ChannelsModal,
    CategoriesConfig: CategoriesModal,
    DurationConfig: DurationModal,
}


def get_condition_modal(condition: ConditionType, callback: ConditionsCallback) -> ConfigModal | None:
    config_type = CONFIG_TYPES[condition]
    if config_type is NoConfig:
        return None
    return MODAL_FOR_CONFIG[config_type](condition, callback)
