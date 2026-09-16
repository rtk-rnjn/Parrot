from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from core import Parrot


class GlobalChatChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, global_chat_channel_id: int | None) -> None:
        super().__init__(
            placeholder="Select a global chat channel...",
            min_values=0,
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
            channel = interaction.guild.get_channel(new_global_chat_channel_id)
            assert isinstance(channel, discord.TextChannel), "Selected channel must be a text channel."

            webhook = await channel.create_webhook(
                name="Global Chat Webhook",
                reason="Global chat webhook created.",
            )

            await interaction.client.database.edit_global_chat_config(
                guild_id=interaction.guild.id,
                enabled=True,
                webhook_uri=webhook.url,
                channel_id=new_global_chat_channel_id,
            )
            await interaction.followup.send(f"Global chat channel updated to {selected_channel.mention}.", ephemeral=True)
