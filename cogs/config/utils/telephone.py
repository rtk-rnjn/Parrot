from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Parrot


class TelephoneChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, hub_channel_id: int | None) -> None:
        super().__init__(
            placeholder="Select a Telephone channel...",
            min_values=0,
            max_values=1,
            channel_types=[discord.ChannelType.text],
            default_values=[discord.Object(id=hub_channel_id)] if hub_channel_id is not None else [],
        )
        self.hub_channel_id = hub_channel_id

    async def callback(self, interaction: discord.Interaction[Parrot], /) -> None:
        assert self.view is not None
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        selected_channel = self.values[0] if self.values else None

        if selected_channel is not None:
            new_hub_channel_id = selected_channel.id

            await interaction.client.database.edit_telephone_config(guild_id=interaction.guild.id, enabled=True, channel_id=new_hub_channel_id)
            await interaction.followup.send(f"Telephone channel updated to {selected_channel.mention}.", ephemeral=True)

        else:
            await interaction.client.database.edit_telephone_config(guild_id=interaction.guild.id, enabled=False, channel_id=None)
            await interaction.followup.send("Telephone channel has been removed.", ephemeral=True)
