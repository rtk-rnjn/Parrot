from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Parrot


class ConfirmationLayout(discord.ui.LayoutView):
    def __init__(self, author: discord.User | discord.Member, prompt: str, result: asyncio.Future[bool]) -> None:
        super().__init__(timeout=None)
        self.author = author
        self.result = result
        self.message: discord.Message

        confirm_button = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.success)
        confirm_button.callback = self.confirm_callback
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        cancel_button.callback = self.cancel_callback

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(prompt),
                discord.ui.Separator(),
                discord.ui.ActionRow(confirm_button, cancel_button),
            ),
        )

    async def interaction_check(self, interaction: discord.Interaction[Parrot]) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
            return False
        return True

    async def confirm_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not self.result.done():
            self.result.set_result(True)
        await interaction.response.edit_message(content="Confirmed.", view=None)
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not self.result.done():
            self.result.set_result(False)
        await interaction.response.edit_message(content="Cancelled.", view=None)
        self.stop()
