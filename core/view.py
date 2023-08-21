from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from discord.enums import ButtonStyle
from discord.interactions import Interaction

import discord

if TYPE_CHECKING:
    from . import Context
    from . import Parrot

__all__ = ("ParrotView", "ParrotButton", "ParrotSelect", "ParrotLinkView", "ParrotModal")


class ParrotItem(discord.ui.Item):
    ...


class ParrotModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        title: str = discord.utils.MISSING,
        timeout: float = None,
        custom_id: str = discord.utils.MISSING,
    ) -> None:
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)

    async def on_error(self, interaction: Interaction, error: Exception):
        interaction.client.dispatch("error", error, interaction, self)
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class ParrotView(discord.ui.View):
    if TYPE_CHECKING:
        message: discord.Message
        ctx: Context
        bot: Parrot

    def __init__(self, *, timeout: float | None = 60, delete_message: bool = False, **kwargs) -> None:
        super().__init__(timeout=timeout)
        self.delete_message = delete_message
        if ctx := kwargs.get("ctx"):
            self.ctx: Context = ctx
            self.bot = self.ctx.bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        author = self.ctx.author if hasattr(self, "ctx") else None
        if author and interaction.user.id != author.id:
            await interaction.response.send_message(f"Only the {self.ctx.author.mention} can use this menu.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        if self.delete_message and hasattr(self, "message") and self.message:
            await self.message.delete(delay=0)

        self.disable_all()

        if hasattr(self, "message") and self.message:
            await self.message.edit(view=self)

        self.stop()

    def disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button | discord.ui.Select):
                item.disabled = True

    def disable_all_except(self, *items: discord.ui.Item) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button | discord.ui.Select) and item not in items:
                item.disabled = True

    def disable_all_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    def disable_all_selects(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.disabled = True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        interaction.client.dispatch("error", error, interaction, item, self)
        err = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        await interaction.response.send_message(f"An error occurred: {err}", ephemeral=True)


class ParrotButton(discord.ui.Button["ParrotView"]):
    def __init__(
        self,
        *,
        style: ButtonStyle = ButtonStyle.secondary,
        label: str = None,
        disabled: bool = False,
        custom_id: str = None,
        url: str = None,
        emoji: str | discord.Emoji | discord.PartialEmoji = None,
        row: int = None,
        **kwargs,
    ) -> None:
        super().__init__(style=style, label=label, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji, row=row)

        self.callback_function = kwargs.pop("callback", None)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.callback_function:
            await self.callback_function(interaction)
        else:
            await interaction.response.defer()

    def set_callback(self, callback) -> ParrotButton:
        self.callback_function = callback
        return self


class ParrotSelect(discord.ui.Select):
    def __init__(
        self,
        *,
        custom_id: str = discord.utils.MISSING,
        placeholder: str = None,
        min_values: int = 1,
        max_values: int = 1,
        options: list[discord.SelectOption] = discord.utils.MISSING,
        row: int = None,
        **kwargs,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            row=row,
        )
        self.callback_function = kwargs.get("callback")

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.callback_function:
            await self.callback_function(interaction)
        else:
            await interaction.response.defer()

    def set_callback(self, callback) -> ParrotSelect:
        self.callback_function = callback
        return self


class ParrotLinkView(discord.ui.View):
    def __init__(self, url: str, label: str = "Click here to view the link") -> None:
        super().__init__()
        self.url = url

        self.add_item(
            ParrotButton(
                label=label,
                url=self.url,
                style=discord.ButtonStyle.link,
            ),
        )
