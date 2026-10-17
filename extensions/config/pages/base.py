from __future__ import annotations

import abc
from collections.abc import Awaitable, Callable, Sequence
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

import discord

from core.utils import CallbackButton, CallbackChannelSelect, CallbackRoleSelect, CallbackStringSelect, truncate

if TYPE_CHECKING:
    from core import Bot
    from core.utils import DatabaseManager
    from core.utils.database import GuildSettingSection
    from core.utils.database.models import GuildConfiguration

    from ..dashboard import ConfigDashboard

__all__ = (
    "DISABLED_TEXT",
    "ENABLED_TEXT",
    "NOT_SET",
    "Button",
    "ChannelSelect",
    "Interaction",
    "NoticeLevel",
    "Page",
    "PageModal",
    "RoleSelect",
    "StringSelect",
    "channel_text",
    "preview",
    "role_text",
    "role_warning",
    "status_text",
)

type Interaction = discord.Interaction[Bot]
type ButtonHandler = Callable[[Interaction], Awaitable[None]]
type ToggleHandler = Callable[[Interaction, bool], Awaitable[None]]
type ChannelHandler = Callable[[Interaction, list[int]], Awaitable[None]]
type RoleHandler = Callable[[Interaction, list[discord.Role]], Awaitable[None]]
type StringHandler = Callable[[Interaction, list[str]], Awaitable[None]]

ENABLED_TEXT = "\N{LARGE GREEN CIRCLE} Enabled"
DISABLED_TEXT = "\N{MEDIUM WHITE CIRCLE} Disabled"
NOT_SET = "*Not set*"
WARNING = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"

PREVIEW_LENGTH = 70
TEXT_CHANNELS: tuple[discord.ChannelType, ...] = (discord.ChannelType.text, discord.ChannelType.news)


class NoticeLevel(Enum):
    """Prefix shown before the dashboard's one-line feedback."""

    OK = "\N{WHITE HEAVY CHECK MARK}"
    INFO = "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}"
    WARNING = WARNING
    ERROR = "\N{CROSS MARK}"


def status_text(enabled: bool) -> str:
    return ENABLED_TEXT if enabled else DISABLED_TEXT


def channel_text(guild: discord.Guild, channel_id: int | None) -> str:
    """Mention a channel, or say clearly that the stored one no longer exists."""
    if channel_id is None:
        return NOT_SET
    channel = guild.get_channel_or_thread(channel_id)
    return channel.mention if channel is not None else f"{WARNING} Deleted channel (`{channel_id}`)"


def role_text(guild: discord.Guild, role_id: int | None) -> str:
    if role_id is None:
        return NOT_SET
    role = guild.get_role(role_id)
    return role.mention if role is not None else f"{WARNING} Deleted role (`{role_id}`)"


def role_warning(guild: discord.Guild, role: discord.Role) -> str | None:
    """Explain why the bot could not hand out ``role``, or ``None`` when it can."""
    if role.is_default():
        return "that is the @everyone role, which cannot be assigned."
    if role.managed:
        return f"{role.mention} is managed by an integration and cannot be assigned."
    me = guild.me
    if me is not None and role >= me.top_role:
        return f"{role.mention} is above the bot's highest role, so Bot cannot assign it. Move the bot's role above it."
    return None


def preview(text: str | None, *, limit: int = PREVIEW_LENGTH) -> str:
    """Show a short, single-line, escaped preview of user-provided text."""
    if not text:
        return NOT_SET
    flat = " ".join(text.split())
    return f"\N{LEFT DOUBLE QUOTATION MARK}{truncate(discord.utils.escape_markdown(flat), limit)}\N{RIGHT DOUBLE QUOTATION MARK}"


def _channel_defaults(guild: discord.Guild, channel_id: int | None) -> list[discord.abc.GuildChannel | discord.Thread]:
    if channel_id is None:
        return []
    channel = guild.get_channel_or_thread(channel_id)
    return [channel] if channel is not None else []


def _role_defaults(guild: discord.Guild, role_ids: Sequence[int]) -> list[discord.Role]:
    roles = (guild.get_role(role_id) for role_id in role_ids)
    return [role for role in roles if role is not None]


Button = CallbackButton
ChannelSelect = CallbackChannelSelect
RoleSelect = CallbackRoleSelect
StringSelect = CallbackStringSelect


class PageModal(discord.ui.Modal):
    """A modal that belongs to a page and reports back through the dashboard.

    ``self.page`` is typed as the base :class:`Page`; constructors take the concrete page so
    they can read page-specific state while building their inputs.
    """

    def __init__(self, page: Page, *, title: str) -> None:
        super().__init__(title=title, timeout=600)
        self.page = page


class Page(abc.ABC):
    """One category of the settings dashboard.

    A page renders the current values from the dashboard's cached guild document and
    exposes controls whose handlers write through the database and then ask the
    dashboard to reload and re-render in place. ``section`` names the settings section a
    reset restores; leaving it ``None`` hides the reset button.
    """

    key: ClassVar[str]
    label: ClassVar[str]
    emoji: ClassVar[str]
    description: ClassVar[str]
    section: ClassVar[GuildSettingSection | None] = None

    def __init__(self, dashboard: ConfigDashboard) -> None:
        self.dashboard = dashboard

    @property
    def bot(self) -> Bot:
        return self.dashboard.bot

    @property
    def guild(self) -> discord.Guild:
        return self.dashboard.guild

    @property
    def config(self) -> GuildConfiguration:
        return self.dashboard.config

    @property
    def db(self) -> DatabaseManager:
        return self.dashboard.bot.database

    async def prepare(self) -> None:  # noqa: B027
        """Fetch anything the page needs beyond the guild document. Runs before every render."""

    @abc.abstractmethod
    def summary(self) -> str:
        """One short line for the overview page."""

    def accent(self) -> discord.Colour | None:
        """Container colour; ``None`` uses the dashboard default."""
        return None

    @abc.abstractmethod
    def build(self) -> list[discord.ui.Item]:
        """The page body, rendered below the header."""

    def reset_summary(self) -> str:
        """What a reset clears, shown in the confirmation prompt."""
        return f"every {self.label} setting"

    async def reset(self) -> None:
        """Restore this page's section to its defaults."""
        if self.section is not None:
            await self.db.reset_guild_setting(guild_id=self.guild.id, section=self.section)

    async def commit(self, interaction: Interaction, notice: str | None = None, *, level: NoticeLevel = NoticeLevel.OK) -> None:
        await self.dashboard.commit(interaction, notice, level=level)

    @staticmethod
    def text(content: str) -> discord.ui.TextDisplay:
        return discord.ui.TextDisplay(content)

    @staticmethod
    def row(*items: discord.ui.Item) -> discord.ui.ActionRow:
        return discord.ui.ActionRow(*items)

    @staticmethod
    def status(pairs: Sequence[tuple[str, str]]) -> discord.ui.TextDisplay:
        """A compact ``**Label**: value`` card."""
        return discord.ui.TextDisplay("\n".join(f"**{label}**: {value}" for label, value in pairs))

    def button(
        self,
        label: str | None,
        handler: ButtonHandler,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        emoji: str | None = None,
        disabled: bool = False,
    ) -> Button:
        return Button(handler, label=label, style=style, emoji=emoji, disabled=disabled)

    def toggle(self, enabled: bool, handler: ToggleHandler) -> Button:
        """An Enable/Disable button that reports the *new* state to ``handler``."""

        async def flip(interaction: Interaction) -> None:
            await handler(interaction, not enabled)

        if enabled:
            return Button(flip, label="Disable", style=discord.ButtonStyle.secondary, emoji="\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}")
        return Button(flip, label="Enable", style=discord.ButtonStyle.success, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}")

    def reset_button(self) -> Button:
        return Button(
            self.dashboard.request_reset,
            label="Reset",
            style=discord.ButtonStyle.danger,
            emoji="\N{LEFTWARDS ARROW WITH HOOK}\N{VARIATION SELECTOR-16}",
        )

    def channel_select(
        self,
        placeholder: str,
        handler: ChannelHandler,
        *,
        current: int | None = None,
        channel_types: Sequence[discord.ChannelType] = TEXT_CHANNELS,
    ) -> ChannelSelect:
        return ChannelSelect(
            handler,
            placeholder=placeholder,
            channel_types=list(channel_types),
            min_values=0,
            max_values=1,
            default_values=_channel_defaults(self.guild, current),
        )

    def role_select(
        self,
        placeholder: str,
        handler: RoleHandler,
        *,
        current: Sequence[int] = (),
        max_values: int = 1,
    ) -> RoleSelect:
        return RoleSelect(
            handler,
            placeholder=placeholder,
            min_values=0,
            max_values=max_values,
            default_values=_role_defaults(self.guild, current),
        )

    def string_select(
        self,
        placeholder: str,
        options: Sequence[discord.SelectOption],
        handler: StringHandler,
        *,
        max_values: int = 1,
        disabled: bool = False,
    ) -> StringSelect:
        return StringSelect(
            handler,
            placeholder=placeholder,
            options=list(options),
            min_values=1,
            max_values=max(1, max_values),
            disabled=disabled,
        )
