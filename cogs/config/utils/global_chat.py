from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Parrot


class GlobalChatToggleButton(discord.ui.Button):
    def __init__(self, *, enabled: bool) -> None:
        super().__init__(
            label="On" if enabled else "Off",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        new_enabled_state = not self.enabled

        if new_enabled_state:
            await interaction.client.database.enable_global_chat(guild_id=interaction.guild.id)
            await interaction.followup.send("Global chat has been enabled.", ephemeral=True)
        else:
            await interaction.client.database.disable_global_chat(guild_id=interaction.guild.id)
            await interaction.followup.send("Global chat has been disabled.", ephemeral=True)

        self.enabled = new_enabled_state
        self.label = "On" if self.enabled else "Off"


class GlobalChatChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, global_chat_channel_id: int | None) -> None:
        super().__init__(
            placeholder="Select a global chat channel...",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            default_values=[discord.Object(id=global_chat_channel_id)] if global_chat_channel_id is not None else [],
        )
        self.global_chat_channel_id = global_chat_channel_id

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        selected_channel = self.values[0] if self.values else None

        if selected_channel is not None:
            new_global_chat_channel_id = selected_channel.id

            await interaction.client.database.set_global_chat_channel_id(guild_id=interaction.guild.id, channel_id=new_global_chat_channel_id)
            await interaction.followup.send(f"Global chat channel updated to {selected_channel.mention}.", ephemeral=True)
