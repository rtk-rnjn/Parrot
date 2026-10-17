from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import discord
import re2 as re

from .configs import AllCapsConfig, CountConfig, LengthConfig, ListConfig, NoConfig, RegexConfig, TimeWindowConfig, ViolationConfig
from .mapping import _CONFIG_TYPES as CONFIG_TYPES
from .trigger import TriggerConfig, TriggerType

TRIGGER_GROUP = {
    "message_content": [
        TriggerType.ALL_CAPS,
        TriggerType.MESSAGE_MENTIONS,
        TriggerType.ANY_LINK,
        TriggerType.WORD_DENYLIST,
        TriggerType.WORD_ALLOWLIST,
        TriggerType.WEBSITE_DENYLIST,
        TriggerType.WEBSITE_ALLOWLIST,
        TriggerType.SERVER_INVITES,
        TriggerType.MESSAGE_REGEX,
        TriggerType.MESSAGE_NOT_REGEX,
        TriggerType.MESSAGE_WITHOUT_ATTACHMENTS,
        TriggerType.MESSAGE_WITH_ATTACHMENTS,
        TriggerType.FLAGGED_SCAM_LINKS,
        TriggerType.MESSAGE_LENGTH_GT,
        TriggerType.MESSAGE_LENGTH_LT,
        TriggerType.DISCORD_AUTOMOD,
    ],
    "user_rate_limits": [
        TriggerType.VIOLATIONS,
        TriggerType.X_CONSECUTIVE_IDENTICAL_MESSAGES,
        TriggerType.X_USER_ATTACHMENTS_IN_Y_MINUTES,
        TriggerType.X_USER_LINKS_IN_Y_MINUTES,
        TriggerType.X_USER_MESSAGE_IN_Y_MINUTES,
        TriggerType.X_VIOLATION_IN_Y_MINUTES,
        TriggerType.X_USER_MESSAGE_MENTIONS_IN_Y_MINUTES,
    ],
    "channel_rate_limits": [
        TriggerType.X_CHANNEL_ATTACHMENTS_IN_Y_MINUTES,
        TriggerType.X_CHANNEL_LINKS_IN_Y_MINUTES,
        TriggerType.X_CHANNEL_MESSAGE_IN_Y_MINUTES,
        TriggerType.X_CHANNEL_MESSAGE_MENTIONS_IN_Y_MINUTES,
    ],
    "nickname": [
        TriggerType.NICKNAME_REGEX,
        TriggerType.NICKNAME_NOT_REGEX,
        TriggerType.NICKNAME_WORD_ALLOWLIST,
        TriggerType.NICKNAME_WORD_DENYLIST,
    ],
    "join_username": [
        TriggerType.JOIN_USERNAME_WORD_ALLOWLIST,
        TriggerType.JOIN_USERNAME_WORD_DENYLIST,
        TriggerType.JOIN_USERNAME_REGEX,
        TriggerType.JOIN_USERNAME_NOT_REGEX,
        TriggerType.JOIN_USERNAME_INVITE,
        TriggerType.NEW_MEMBER,
    ],
}


TRIGGER_GROUP_NAMES = {
    "message_content": {
        "name": "Message Content",
        "description": "Triggers that fire based on the content of a message.",
        "emoji": "\N{SPEECH BALLOON}",
    },
    "user_rate_limits": {
        "name": "User Rate Limits",
        "description": "Triggers that fire based on the rate of user activity.",
        "emoji": "\N{STOPWATCH}",
    },
    "channel_rate_limits": {
        "name": "Channel Rate Limits",
        "description": "Triggers that fire based on the rate of channel activity.",
        "emoji": "\N{STOPWATCH}",
    },
    "nickname": {"name": "Nickname", "description": "Triggers that fire based on a user's nickname.", "emoji": "\N{MEMO}"},
    "join_username": {
        "name": "Join Username",
        "description": "Triggers that fire based on a user's username when they join.",
        "emoji": "\N{BUST IN SILHOUETTE}",
    },
}


class TriggerCallback(Protocol):
    async def __call__(self, interaction: discord.Interaction[discord.Client], trigger: TriggerType, config: TriggerConfig) -> None: ...


class ConfigError(Exception):
    """Raised when modal input is invalid. The message is shown to the user."""


def parse_int(field: discord.ui.TextInput, name: str, *, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        value = int(field.value.strip())
    except ValueError:
        msg = f"**{name}** must be a whole number."
        raise ConfigError(msg) from None

    if value < minimum or (maximum is not None and value > maximum):
        bounds = f"at least {minimum}" if maximum is None else f"between {minimum} and {maximum}"
        msg = f"**{name}** must be {bounds}."
        raise ConfigError(msg)
    return value


class ConfigModal(discord.ui.Modal):
    """Base modal: subclasses add inputs and implement `build_config`."""

    def __init__(self, *, title: str, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title=title)  # Discord limits titles to 45 chars
        self.trigger = trigger
        self.config_callback = callback

    def build_config(self) -> TriggerConfig:
        raise NotImplementedError

    async def on_submit(self, interaction: discord.Interaction[discord.Client]) -> None:
        try:
            config = self.build_config()
        except ConfigError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await self.config_callback(interaction, self.trigger, config)

    async def on_error(self, interaction: discord.Interaction[discord.Client], error: Exception) -> None:
        if interaction.response.is_done():
            await interaction.followup.send("Something went wrong saving that config.", ephemeral=True)
        else:
            await interaction.response.send_message("Something went wrong saving that config.", ephemeral=True)
        raise error


class AllCapsModal(ConfigModal):
    def __init__(self, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title="All Caps Configuration", trigger=trigger, callback=callback)
        defaults = AllCapsConfig()  # NOT AllCapsConfig.min_count, see note below

        self.min_count = discord.ui.TextInput(
            label="Minimum Characters",
            placeholder="Minimum number of letters before the check applies.",
            default=str(defaults.min_count),
            max_length=4,
        )
        self.percentage = discord.ui.TextInput(
            label="Percentage (1-100)",
            placeholder="Percentage of letters that must be uppercase.",
            default=str(defaults.percentage),
            max_length=3,
        )
        self.add_item(self.min_count)
        self.add_item(self.percentage)

    def build_config(self) -> AllCapsConfig:
        return AllCapsConfig(
            min_count=parse_int(self.min_count, "Minimum Characters"),
            percentage=parse_int(self.percentage, "Percentage", maximum=100),
        )


class CountModal(ConfigModal):
    def __init__(self, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title="Count Configuration", trigger=trigger, callback=callback)
        self.count = discord.ui.TextInput(
            label="Count",
            placeholder="How many are needed to trigger.",
            max_length=5,
        )
        self.add_item(self.count)

    def build_config(self) -> CountConfig:
        return CountConfig(count=parse_int(self.count, "Count"))


class TimeWindowModal(ConfigModal):
    def __init__(self, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title="Time Window Configuration", trigger=trigger, callback=callback)
        self.count = discord.ui.TextInput(
            label="Count",
            placeholder="How many are needed to trigger.",
            max_length=5,
        )
        self.within_minutes = discord.ui.TextInput(
            label="Within (minutes)",
            placeholder="Length of the time window in minutes.",
            max_length=5,
        )
        self.add_item(self.count)
        self.add_item(self.within_minutes)

    def build_config(self) -> TimeWindowConfig:
        return TimeWindowConfig(
            count=parse_int(self.count, "Count"),
            within_minutes=parse_int(self.within_minutes, "Within (minutes)"),
        )


class ListModal(ConfigModal):
    def __init__(self, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title="List Configuration", trigger=trigger, callback=callback)
        self.list_name = discord.ui.TextInput(
            label="List Name (optional)",
            placeholder="Name of an existing list. Leave empty to choose later.",
            required=False,
            max_length=100,
        )
        self.add_item(self.list_name)

    def build_config(self) -> ListConfig:
        return ListConfig(list_name=self.list_name.value.strip() or None)


class RegexModal(ConfigModal):
    def __init__(self, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title="Regex Configuration", trigger=trigger, callback=callback)
        self.regex = discord.ui.TextInput(
            label="Regex Pattern",
            placeholder=r"e.g. (?i)free\s+nitro",
            style=discord.TextStyle.paragraph,
            max_length=500,
        )
        self.add_item(self.regex)

    def build_config(self) -> RegexConfig:
        pattern = self.regex.value.strip()
        try:
            re.compile(pattern)
        except re.error as error:
            msg = f"Invalid regex: `{error}`"
            raise ConfigError(msg) from None
        return RegexConfig(regex=pattern)


class LengthModal(ConfigModal):
    def __init__(self, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title="Length Configuration", trigger=trigger, callback=callback)
        self.length = discord.ui.TextInput(
            label="Length (characters)",
            placeholder="Message length threshold.",
            max_length=5,
        )
        self.add_item(self.length)

    def build_config(self) -> LengthConfig:
        return LengthConfig(length=parse_int(self.length, "Length"))


class ViolationModal(ConfigModal):
    def __init__(self, trigger: TriggerType, callback: TriggerCallback) -> None:
        super().__init__(title="Violation Configuration", trigger=trigger, callback=callback)
        self.violation_name = discord.ui.TextInput(
            label="Violation Name",
            placeholder="Name of the rule whose violations are counted.",
            max_length=100,
        )
        self.number_of_violations = discord.ui.TextInput(
            label="Number of Violations",
            placeholder="How many violations are needed to trigger.",
            max_length=5,
        )
        self.within_minutes = discord.ui.TextInput(
            label="Within (minutes)",
            placeholder="Length of the time window in minutes.",
            max_length=5,
        )
        self.add_item(self.violation_name)
        self.add_item(self.number_of_violations)
        self.add_item(self.within_minutes)

    def build_config(self) -> ViolationConfig:
        return ViolationConfig(
            violation_name=self.violation_name.value.strip(),
            number_of_violations=parse_int(self.number_of_violations, "Number of Violations"),
            within_minutes=parse_int(self.within_minutes, "Within (minutes)"),
        )


MODAL_FOR_CONFIG: dict[type[TriggerConfig], Callable[[TriggerType, TriggerCallback], ConfigModal]] = {
    AllCapsConfig: AllCapsModal,
    CountConfig: CountModal,
    TimeWindowConfig: TimeWindowModal,
    ListConfig: ListModal,
    RegexConfig: RegexModal,
    LengthConfig: LengthModal,
    ViolationConfig: ViolationModal,
}


def get_config_modal(trigger: TriggerType, callback: TriggerCallback) -> ConfigModal | None:
    """Return the modal for a trigger, or None if the trigger needs no config."""
    config_type = CONFIG_TYPES[trigger]
    if config_type is NoConfig:
        return None

    config_modal = MODAL_FOR_CONFIG[config_type]
    return config_modal(trigger, callback)


def describe(config: TriggerConfig) -> str:  # noqa: PLR0911
    REGEX_LIMIMT = 40
    match config:
        case AllCapsConfig(min_count=minimum, percentage=percentage):
            return f"{percentage}% caps, at least {minimum} letters"
        case CountConfig(count=count):
            return f"{count} or more"
        case TimeWindowConfig(count=count, within_minutes=minutes):
            return f"{count} within {minutes} min"
        case ListConfig(list_name=name):
            return f"list `{name}`" if name else "no list chosen yet"
        case RegexConfig(regex=regex):
            flat = regex.replace("`", "'")
            return f"`{flat if len(flat) <= REGEX_LIMIMT else flat[:39] + '\N{HORIZONTAL ELLIPSIS}'}`"
        case LengthConfig(length=length):
            return f"{length} characters"
        case ViolationConfig(violation_name=name, number_of_violations=count, within_minutes=minutes):
            return f"{count}\N{MULTIPLICATION SIGN} `{name}` within {minutes} min"
        case _:
            return ""
