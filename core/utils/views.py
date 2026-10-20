# core/utils/views.py

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Self

import discord
from discord.ext import commands

from .formats import truncate

if TYPE_CHECKING:
    from core import Bot

__all__ = (
    "BaseLayoutView",
    "BaseView",
    "DeleteMessageButtonView",
    "DisabledButtonView",
    "DisambiguatorView",
    "NoticeLayout",
)

type Author = discord.Member | discord.User

_DISABLEABLE_ITEMS = (
    discord.ui.Button,
    discord.ui.Select,
    discord.ui.UserSelect,
    discord.ui.RoleSelect,
    discord.ui.MentionableSelect,
    discord.ui.ChannelSelect,
)

MAX_TEXT_LENGTH = 4000
MAX_FOOTER_LENGTH = MAX_TEXT_LENGTH // 4


async def _authorise(
    interaction: discord.Interaction,
    *,
    author: Author,
    required_permission: discord.Permissions | None,
) -> bool:
    """Allow the owner, or a member holding ``required_permission``; tell anyone else why they were refused."""
    if interaction.user.id == author.id:
        return True

    if required_permission is not None and isinstance(interaction.user, discord.Member):
        if interaction.user.guild_permissions >= required_permission:
            return True
        reason = "You do not have the required permissions to interact with this view."
    else:
        reason = "You cannot interact with this view."

    await interaction.response.send_message(reason, ephemeral=True)
    return False


def _disable_items(view: discord.ui.View | discord.ui.LayoutView) -> None:
    for item in view.walk_children():
        if isinstance(item, _DISABLEABLE_ITEMS):
            item.disabled = True


async def _push_to_message(view: discord.ui.View | discord.ui.LayoutView, message: discord.Message | None) -> None:
    """Edit ``message`` to show the view's current state, ignoring messages that are gone or no longer editable."""
    if message is None:
        return

    with contextlib.suppress(discord.HTTPException):
        await message.edit(view=view)


class BaseView(discord.ui.View):
    """A view owned by one user. It disables its items and updates its message when it times out."""

    message: discord.Message | None = None

    def __init__(
        self,
        author: Author,
        *,
        timeout: float | None = None,
        required_permission: discord.Permissions | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.author = author
        self.required_permission = required_permission

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _authorise(interaction, author=self.author, required_permission=self.required_permission)

    def disable_all_items(self) -> None:
        _disable_items(self)

    async def update_message(self) -> None:
        """Push the current state of the view to its message, if one has been attached."""
        await _push_to_message(self, self.message)

    async def on_timeout(self) -> None:
        self.disable_all_items()
        await self.update_message()


class BaseLayoutView(discord.ui.LayoutView):
    """A components v2 view owned by one user. It disables its items and updates its message when it times out."""

    message: discord.Message | None = None

    def __init__(
        self,
        author: Author,
        *,
        timeout: float | None = None,
        required_permission: discord.Permissions | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.author = author
        self.required_permission = required_permission

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await _authorise(interaction, author=self.author, required_permission=self.required_permission)

    def disable_all_items(self) -> None:
        _disable_items(self)

    async def update_message(self) -> None:
        """Push the current state of the view to its message, if one has been attached."""
        await _push_to_message(self, self.message)

    async def on_timeout(self) -> None:
        self.disable_all_items()
        await self.update_message()


class DeleteMessageButtonView(BaseView):
    """A single wastebasket button that deletes the bot's reply and, when it can, the message it replied to."""

    def __init__(self, *, author: Author) -> None:
        super().__init__(author, timeout=None)

        button = discord.ui.Button[DeleteMessageButtonView](emoji="\N{WASTEBASKET}", style=discord.ButtonStyle.red)
        button.callback = self.delete_message_callback
        self.add_item(button)

    async def delete_message_callback(self, interaction: discord.Interaction) -> None:
        self.stop()
        await interaction.response.defer()

        message = self.message or interaction.message
        if message is None:
            return

        await message.delete(delay=0)

        # The bot replies with ctx.reply, so the reference resolves to the invoking message.
        reference = message.reference.resolved if message.reference is not None else None
        if isinstance(reference, discord.Message):
            await reference.delete(delay=0)


class DisabledButtonView(BaseView):
    """A single disabled button used as a label, for example to show which server a message came from."""

    def __init__(
        self,
        *,
        author: Author,
        display_text: str,
        button_style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    ) -> None:
        super().__init__(author, timeout=None)

        button = discord.ui.Button[DisabledButtonView](label=display_text, style=button_style, disabled=True)
        self.add_item(button)


class NoticeLayout(discord.ui.LayoutView):
    """A one-container components v2 message for short status, success, warning and error replies.

    It has no interactive items, so it never times out and needs no owner check. Prefer the
    ``info``, ``success``, ``warning`` and ``error`` constructors so accent colours stay consistent.
    """

    def __init__(
        self,
        body: str,
        *,
        title: str | None = None,
        colour: discord.Colour | None = None,
        footer: str | None = None,
        thumbnail: str | None = None,
    ) -> None:
        super().__init__(timeout=None)

        footer_text = truncate(f"-# {footer}", MAX_FOOTER_LENGTH) if footer else None
        budget = MAX_TEXT_LENGTH - (len(footer_text) if footer_text else 0)
        text = truncate(f"### {title}\n{body}" if title else body, budget)

        content: discord.ui.Item = discord.ui.TextDisplay(text)
        if thumbnail:
            content = discord.ui.Section(content, accessory=discord.ui.Thumbnail(thumbnail))

        self.container = discord.ui.Container(content, accent_colour=colour)
        if footer_text:
            self.container.add_item(discord.ui.Separator())
            self.container.add_item(discord.ui.TextDisplay(footer_text))

        self.add_item(self.container)

    @classmethod
    def info(cls, body: str, *, title: str | None = None, footer: str | None = None, thumbnail: str | None = None) -> Self:
        return cls(body, title=title, colour=discord.Colour.blurple(), footer=footer, thumbnail=thumbnail)

    @classmethod
    def success(cls, body: str, *, title: str | None = None, footer: str | None = None, thumbnail: str | None = None) -> Self:
        return cls(body, title=title, colour=discord.Colour.green(), footer=footer, thumbnail=thumbnail)

    @classmethod
    def warning(cls, body: str, *, title: str | None = None, footer: str | None = None, thumbnail: str | None = None) -> Self:
        return cls(body, title=title, colour=discord.Colour.orange(), footer=footer, thumbnail=thumbnail)

    @classmethod
    def error(cls, body: str, *, title: str | None = None, footer: str | None = None, thumbnail: str | None = None) -> Self:
        return cls(body, title=title, colour=discord.Colour.red(), footer=footer, thumbnail=thumbnail)


class DisambiguatorView[T](BaseView):
    message: discord.Message
    selected: T

    def __init__(
        self,
        ctx: commands.Context[Bot],
        data: list[T],
        entry: Callable[[T], str] = str,
    ):
        super().__init__(author=ctx.author)
        self.ctx = ctx
        self.data: list[T] = data

        options = []
        for i, x in enumerate(data):
            option = entry(x)
            if not isinstance(option, discord.SelectOption):
                option = discord.SelectOption(label=str(option))
            option.value = str(i)
            options.append(option)

        select = discord.ui.Select(options=options)

        select.callback = self.on_select_submit
        self.select = select
        self.add_item(select)

    async def on_select_submit(self, interaction: discord.Interaction):
        index = int(self.select.values[0])
        self.selected = self.data[index]
        await interaction.response.defer()

        if not self.message.flags.ephemeral:
            await self.message.delete(delay=0)

        self.stop()
