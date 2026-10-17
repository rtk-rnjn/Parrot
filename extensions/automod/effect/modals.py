from __future__ import annotations

from typing import Protocol

import discord

from ..constants import MAX_SLOWMODE_SECONDS, MAX_TIMEOUT_SECONDS, MENTION_PREVIEW
from ..parsing import format_duration
from ..parsing import parse_duration as parse_time_duration
from .effect import (
    AlertConfig,
    BanConfig,
    DeleteMessagesConfig,
    EffectConfig,
    EffectType,
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
from .mapping import _EFFECT_CONFIG_TYPES as CONFIG_TYPES

EFFECT_GROUP = {
    "messages": [
        EffectType.DELETE_MESSAGE,
        EffectType.DELETE_MULTIPLE_MESSAGES,
        EffectType.SEND_MESSAGE,
        EffectType.SEND_ALERT,
        EffectType.ENABLE_SLOWMODE,
    ],
    "punishments": [
        EffectType.WARN_USER,
        EffectType.TIMEOUT_USER,
        EffectType.MUTE_USER,
        EffectType.KICK_USER,
        EffectType.BAN_USER,
    ],
    "violations": [
        EffectType.ADD_VIOLATION,
        EffectType.RESET_VIOLATIONS,
    ],
    "members": [
        EffectType.SET_NICKNAME,
        EffectType.GIVE_ROLE,
        EffectType.REMOVE_ROLE,
    ],
}

EFFECT_GROUP_NAMES = {
    "messages": {
        "name": "Messages",
        "description": "Effects that delete or send messages.",
        "emoji": "\N{ENVELOPE}",
    },
    "punishments": {
        "name": "Punishments",
        "description": "Effects that warn or punish the user.",
        "emoji": "\N{HAMMER}",
    },
    "violations": {
        "name": "Violations",
        "description": "Effects that change the user's violation record.",
        "emoji": "\N{WARNING SIGN}",
    },
    "members": {
        "name": "Members",
        "description": "Effects that change the user's nickname or roles.",
        "emoji": "\N{BUST IN SILHOUETTE}",
    },
}

REPEATABLE = {
    EffectType.ADD_VIOLATION,
    EffectType.RESET_VIOLATIONS,
    EffectType.GIVE_ROLE,
    EffectType.REMOVE_ROLE,
    EffectType.SEND_MESSAGE,
    EffectType.SEND_ALERT,
}

CONFLICTS = {
    EffectType.KICK_USER: {EffectType.BAN_USER},
    EffectType.BAN_USER: {EffectType.KICK_USER},
    EffectType.MUTE_USER: {EffectType.TIMEOUT_USER},
    EffectType.TIMEOUT_USER: {EffectType.MUTE_USER},
}

CHANNEL_TYPES = [
    discord.ChannelType.text,
    discord.ChannelType.news,
    discord.ChannelType.voice,
]


class EffectCallback(Protocol):
    async def __call__(self, interaction: discord.Interaction[discord.Client], effect: EffectType, config: EffectConfig) -> None: ...


class ConfigError(Exception):
    pass


def pretty(effect: EffectType) -> str:
    return effect.value.replace("_", " ").title()


def short_doc(effect: EffectType) -> str | None:
    LIMIT = 100
    doc = (effect.__doc__ or "").strip()
    if not doc:
        return None
    return doc if len(doc) <= LIMIT else doc[: LIMIT - 1] + "\N{HORIZONTAL ELLIPSIS}"


def labeled(text: str, component: discord.ui.Item, *, description: str | None = None) -> discord.ui.Label:
    return discord.ui.Label(text=text, description=description, component=component)


def optional(text: str) -> str | None:
    return text.strip() or None


def clip(text: str, limit: int = 40) -> str:
    flat = " ".join(text.split())
    return f"\N{LEFT DOUBLE QUOTATION MARK}{flat if len(flat) <= limit else flat[: limit - 1] + '\N{HORIZONTAL ELLIPSIS}'}\N{RIGHT DOUBLE QUOTATION MARK}"


def duration_text(seconds: int) -> str:
    return format_duration(seconds) if seconds else "permanent"


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


def parse_duration(
    text: str,
    *,
    name: str,
    default_unit: str = "m",
    units: str = "smhdw",
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    return parse_time_duration(
        text,
        error=ConfigError,
        name=name,
        default_unit=default_unit,
        units=units,
        minimum=minimum,
        maximum=maximum,
    )


def message_input(*, required: bool) -> discord.ui.TextInput:
    return discord.ui.TextInput(
        placeholder="Message text...",
        style=discord.TextStyle.paragraph,
        required=required,
        max_length=1000,
    )


def duration_input(placeholder: str, *, required: bool = False, default: str | None = None) -> discord.ui.TextInput:
    return discord.ui.TextInput(placeholder=placeholder, required=required, max_length=30, default=default)


def channel_select() -> discord.ui.ChannelSelect:
    return discord.ui.ChannelSelect(
        placeholder="Same channel as the rule",
        channel_types=CHANNEL_TYPES,
        min_values=0,
        max_values=1,
        required=False,
    )


def mentions(ids: tuple[int, ...], template: str) -> str:
    shown = ", ".join(template.format(id_) for id_ in ids[:MENTION_PREVIEW])
    extra = len(ids) - MENTION_PREVIEW
    return f"{shown} +{extra} more" if extra > 0 else shown


def describe(config: EffectConfig) -> str:  # noqa: PLR0911, PLR0912
    match config:
        case ViolationConfig(name=name):
            return f"`{name}`" if name else ""
        case MessageConfig(message=message):
            return clip(message) if message else ""
        case BanConfig(duration_minutes=minutes, message=message, delete_days=days):
            parts = [duration_text(minutes * 60)]
            if days:
                parts.append(f"deletes {days}d of messages")
            if message:
                parts.append(clip(message))
            return ", ".join(parts)
        case MuteConfig(duration_minutes=minutes, message=message) | TimeoutConfig(duration_minutes=minutes, message=message):
            return ", ".join([duration_text(minutes * 60), *([clip(message)] if message else [])])
        case NicknameConfig(nickname=nickname):
            return clip(nickname) if nickname else "cleared"
        case DeleteMessagesConfig(count=count, max_age_seconds=age):
            return f"last {count} within {format_duration(age)}"
        case RoleConfig(role_id=role_id, duration_seconds=seconds):
            return (f"<@&{role_id}>" if role_id else "") + (f" for {format_duration(seconds)}" if seconds else "")
        case SlowmodeConfig(duration_seconds=seconds, ratelimit_seconds=rate):
            return f"{format_duration(rate)} per message, {duration_text(seconds)}"
        case SendMessageConfig(message=message, delete_after_seconds=delete_after, ping_user=ping, channel_id=channel):
            parts = [f"<#{channel}>" if channel else "same channel", clip(message)]
            if delete_after:
                parts.append(f"deleted after {format_duration(delete_after)}")
            if ping:
                parts.append("pings user")
            return ", ".join(parts)
        case AlertConfig(message=message, channel_id=channel):
            return ", ".join([f"<#{channel}>" if channel else "same channel", clip(message)])
        case _:
            return ""


class ConfigModal(discord.ui.Modal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(title=pretty(effect)[:45])
        self.effect = effect
        self.config_callback = callback

    def build_config(self) -> EffectConfig:
        raise NotImplementedError

    async def on_submit(self, interaction: discord.Interaction[discord.Client]) -> None:
        try:
            config = self.build_config()
        except ConfigError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await self.config_callback(interaction, self.effect, config)

    async def on_error(self, interaction: discord.Interaction[discord.Client], error: Exception) -> None:
        message = "Something went wrong saving that config."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        raise error


class ViolationModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.name = discord.ui.TextInput(placeholder="Violation name", required=False, max_length=100)
        self.add_item(labeled("Violation Name", self.name, description="Leave empty for the default violation."))

    def build_config(self) -> ViolationConfig:
        return ViolationConfig(name=optional(self.name.value))


class MessageModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.message = message_input(required=False)
        self.add_item(labeled("Message", self.message, description="Sent to the user. Leave empty for none."))

    def build_config(self) -> MessageConfig:
        return MessageConfig(message=optional(self.message.value))


class BanModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.duration = duration_input("e.g. 7d, 12h")
        self.message = message_input(required=False)
        self.delete_days = discord.ui.Select(
            options=[discord.SelectOption(label="Don't delete any", value="0", default=True)]
            + [discord.SelectOption(label=f"{n} day{'s' if n > 1 else ''}", value=str(n)) for n in range(1, 8)]
        )
        self.add_item(labeled("Duration", self.duration, description="Leave empty for a permanent ban."))
        self.add_item(labeled("Message", self.message, description="Sent to the user. Leave empty for none."))
        self.add_item(labeled("Delete Message History", self.delete_days))

    def build_config(self) -> BanConfig:
        seconds = parse_duration(self.duration.value, name="Duration", units="mhdw")
        return BanConfig(
            duration_minutes=seconds // 60,
            message=optional(self.message.value),
            delete_days=int(self.delete_days.values[0]),
        )


class DurationMessageModal(ConfigModal):
    config_type: type[MuteConfig] | type[TimeoutConfig]
    minimum = 0
    maximum: int | None = None
    hint = "Leave empty for permanent."

    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.duration = duration_input("e.g. 30m, 12h, 7d", required=self.minimum > 0)
        self.message = message_input(required=False)
        self.add_item(labeled("Duration", self.duration, description=self.hint))
        self.add_item(labeled("Message", self.message, description="Sent to the user. Leave empty for none."))

    def build_config(self) -> MuteConfig | TimeoutConfig:
        seconds = parse_duration(
            self.duration.value,
            name="Duration",
            units="mhdw",
            minimum=self.minimum,
            maximum=self.maximum,
        )
        return self.config_type(duration_minutes=seconds // 60, message=optional(self.message.value))


class MuteModal(DurationMessageModal):
    config_type = MuteConfig


class TimeoutModal(DurationMessageModal):
    config_type = TimeoutConfig
    minimum = 60
    maximum = MAX_TIMEOUT_SECONDS
    hint = "Between 1 minute and 28 days."


class NicknameModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.nickname = discord.ui.TextInput(placeholder="New nickname", required=False, max_length=32)
        self.add_item(labeled("Nickname", self.nickname, description="Leave empty to clear the nickname."))

    def build_config(self) -> NicknameConfig:
        return NicknameConfig(nickname=optional(self.nickname.value))


class DeleteMessagesModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        defaults = DeleteMessagesConfig()
        self.count = discord.ui.TextInput(placeholder="1-100", default=str(defaults.count), max_length=3)
        self.max_age = duration_input("e.g. 15s, 2m", required=True, default=format_duration(defaults.max_age_seconds))
        self.add_item(labeled("Message Count", self.count, description="How many recent messages to remove."))
        self.add_item(labeled("Max Age", self.max_age, description="Only messages newer than this. Bare number = seconds."))

    def build_config(self) -> DeleteMessagesConfig:
        return DeleteMessagesConfig(
            count=parse_int(self.count, "Message Count", maximum=100),
            max_age_seconds=parse_duration(
                self.max_age.value,
                name="Max Age",
                default_unit="s",
                units="smh",
                minimum=1,
            ),
        )


class RoleModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.role = discord.ui.RoleSelect(placeholder="Select a role...", min_values=1, max_values=1)
        self.duration = duration_input("e.g. 30m, 12h, 7d")
        self.add_item(labeled("Role", self.role))
        self.add_item(labeled("Duration", self.duration, description="Leave empty to make it permanent."))

    def build_config(self) -> RoleConfig:
        return RoleConfig(
            role_id=self.role.values[0].id,
            duration_seconds=parse_duration(self.duration.value, name="Duration", units="mhdw"),
        )


class SlowmodeModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.ratelimit = duration_input("e.g. 10s, 1m", required=True)
        self.duration = duration_input("e.g. 5m, 1h")
        self.add_item(labeled("Slowmode Delay", self.ratelimit, description="Time between messages. Max 6h."))
        self.add_item(labeled("Duration", self.duration, description="How long slowmode stays on. Empty = until removed."))

    def build_config(self) -> SlowmodeConfig:
        return SlowmodeConfig(
            ratelimit_seconds=parse_duration(
                self.ratelimit.value,
                name="Slowmode Delay",
                default_unit="s",
                units="smh",
                minimum=1,
                maximum=MAX_SLOWMODE_SECONDS,
            ),
            duration_seconds=parse_duration(self.duration.value, name="Duration", units="smhdw"),
        )


class SendMessageModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.message = message_input(required=True)
        self.channel = channel_select()
        self.delete_after = duration_input("e.g. 10s, 1m", default=None)
        self.ping_user = discord.ui.Checkbox()
        self.add_item(labeled("Message", self.message))
        self.add_item(labeled("Channel", self.channel, description="Where to send it."))
        self.add_item(labeled("Delete After", self.delete_after, description="Leave empty to keep the message."))
        self.add_item(labeled("Ping the user", self.ping_user))

    def build_config(self) -> SendMessageConfig:
        return SendMessageConfig(
            message=self.message.value.strip(),
            delete_after_seconds=parse_duration(
                self.delete_after.value,
                name="Delete After",
                default_unit="s",
                units="smhd",
            ),
            ping_user=bool(self.ping_user.value),
            channel_id=self.channel.values[0].id if self.channel.values else None,
        )


class AlertModal(ConfigModal):
    def __init__(self, effect: EffectType, callback: EffectCallback) -> None:
        super().__init__(effect, callback)
        self.message = message_input(required=True)
        self.channel = channel_select()
        self.add_item(labeled("Alert Message", self.message))
        self.add_item(labeled("Channel", self.channel, description="Where to send the alert."))

    def build_config(self) -> AlertConfig:
        return AlertConfig(
            message=self.message.value.strip(),
            channel_id=self.channel.values[0].id if self.channel.values else None,
        )


MODAL_FOR_CONFIG: dict[type[EffectConfig], type[ConfigModal]] = {
    ViolationConfig: ViolationModal,
    MessageConfig: MessageModal,
    BanConfig: BanModal,
    MuteConfig: MuteModal,
    TimeoutConfig: TimeoutModal,
    NicknameConfig: NicknameModal,
    DeleteMessagesConfig: DeleteMessagesModal,
    RoleConfig: RoleModal,
    SlowmodeConfig: SlowmodeModal,
    SendMessageConfig: SendMessageModal,
    AlertConfig: AlertModal,
}


def get_effect_modal(effect: EffectType, callback: EffectCallback) -> ConfigModal | None:
    config_type = CONFIG_TYPES[effect]
    if config_type is NoConfig:
        return None

    return MODAL_FOR_CONFIG[config_type](effect, callback)
