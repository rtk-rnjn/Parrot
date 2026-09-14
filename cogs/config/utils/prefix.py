from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Parrot


class UpdateBotPrefixModal(discord.ui.Modal, title="Update Bot Prefix"):
    def __init__(self, *, bot_prefix: str) -> None:
        super().__init__()

        self.bot_prefix = bot_prefix

        self.prefix_input = discord.ui.TextInput(
            label="New Bot Prefix",
            placeholder="Enter the new bot prefix here...",
            default=self.bot_prefix,
            required=True,
            max_length=16,
            min_length=1,
        )

        self.add_item(self.prefix_input)

    async def on_submit(self, interaction: discord.Interaction[Parrot], /) -> None:
        new_prefix = self.prefix_input.value.strip()
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        await interaction.client.database.set_command_prefix(guild_id=interaction.guild.id, command_prefix=new_prefix)
        await interaction.followup.send(f"Bot prefix updated to `{new_prefix}`.", ephemeral=True)


class ChangeBotPrefixButton(discord.ui.Button):
    def __init__(self, *, bot_prefix: str) -> None:
        super().__init__(label=bot_prefix, style=discord.ButtonStyle.green)
        self.bot_prefix = bot_prefix

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        modal = UpdateBotPrefixModal(bot_prefix=self.bot_prefix)
        await interaction.response.send_modal(modal)

        await modal.wait()
        self.label = modal.prefix_input.value.strip()
        if interaction.message is not None:
            await interaction.message.edit(view=self.view)
