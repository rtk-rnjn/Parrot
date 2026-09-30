from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord

from .views import BaseLayoutView

if TYPE_CHECKING:
    from core import Parrot


class ConfirmationLayout(BaseLayoutView):
    def __init__(
        self,
        author: discord.User | discord.Member,
        prompt: str,
        result: asyncio.Future[bool],
    ) -> None:
        super().__init__(author=author)
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
            )
        )

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
