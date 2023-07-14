from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from . import Context

__all__ = ("ParrotView", "ParrotButton", "ParrotSelect", "ParrotLinkView")


class ParrotView(discord.ui.View):
    message: discord.Message
    ctx: Context

    def __init__(self, *, timeout: float = 60, delete_message: bool = False):
        super().__init__(timeout=timeout)
        self.delete_message = delete_message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
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
    
    def disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        interaction.client.dispatch("error", error, interaction, item)


class ParrotButton(discord.ui.Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.callback_function = kwargs.get("callback")

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.callback_function:
            await self.callback_function(interaction)
        else:
            await interaction.response.defer()


class ParrotSelect(discord.ui.Select):
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
