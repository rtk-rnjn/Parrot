from __future__ import annotations

import discord

__all__ = ("DeleteMessageButtonView",)


class DeleteMessageButtonView(discord.ui.View):
    message: discord.Message

    def __init__(self, *, author: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.author = author

        button = discord.ui.Button(emoji="\N{WASTEBASKET}", style=discord.ButtonStyle.red)
        button.callback = self.delete_message_callback

        self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.author:
            return True

        await interaction.response.send_message(
            "You cannot interact with this view.",
            ephemeral=True,
        )
        return False

    async def delete_message_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user != self.author:
            await interaction.response.send_message("You cannot delete this message.", ephemeral=True)
            return

        if hasattr(self, "message"):
            await self.message.delete(delay=0)

            # We delete message and its reference,
            # Bot's reply to any command is ctx.reply
            # so message.author == Bot and message's reference is ctx.message
            if self.message.reference and self.message.reference.resolved and isinstance(self.message.reference.resolved, discord.Message):
                await self.message.reference.resolved.delete(delay=0)

            self.stop()
