from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from . import Context

__all__ = ("ParrotView", "ParrotButton", "ParrotSelect", "ParrotLinkView")


class ParrotItem(discord.ui.Item):
    ...


class ParrotView(discord.ui.View):
    message: discord.Message
    ctx: Context

    def __init__(self, *, timeout: float = 60, delete_message: bool = False, **kwargs):
        super().__init__(timeout=timeout)
        self.delete_message = delete_message
        if ctx := kwargs.get("ctx"):
            self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not hasattr(self, "ctx"):
            return True

        if interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(f"Only the {self.ctx.author.mention} can use this menu.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        if self.delete_message and hasattr(self, "message") and self.message:
            await self.message.delete(delay=0)

        self.disable_all()

        if hasattr(self, "message") and self.message:
            await self.message.edit(view=self)

        self.stop()

    def disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True

    def disable_all_except(self, *items: discord.ui.Item) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)) and item not in items:
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
        interaction.client.dispatch("error", error, interaction, item)
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class ParrotButton(discord.ui.Button["ParrotView"]):
    def __init__(self, **kwargs):
        self.callback_function = kwargs.pop("callback", None)
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.callback_function:
            await self.callback_function(interaction)
        else:
            await interaction.response.defer()


class ParrotSelect(discord.ui.Select["ParrotView"]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.callback_function = kwargs.get("callback")

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.callback_function:
            await self.callback_function(interaction)
        else:
            await interaction.response.defer()


class ParrotLinkView(discord.ui.View):
    def __init__(self, url: str, label: str = "Click here to view the link"):
        super().__init__()
        self.url = url

        self.add_item(
            ParrotButton(
                label=label,
                url=self.url,
                style=discord.ButtonStyle.link,
            )
        )
