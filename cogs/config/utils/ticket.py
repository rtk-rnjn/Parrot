from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

import discord

if TYPE_CHECKING:
    from core import Parrot
    from core.utils.database.models import GuildConfiguration

__all__ = ("TicketEditButton",)


class TicketConfigModal(discord.ui.Modal, title="Edit Ticket Configuration"):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__()

        self.channel_id = kwargs["ticket_config"]["channel_id"]

        self._channel_input = discord.ui.ChannelSelect(
            placeholder="Select a channel for tickets...",
            channel_types=[discord.ChannelType.text],
            default_values=([discord.Object(id=self.channel_id)] if self.channel_id is not None else []),
            min_values=0,
            max_values=1,
        )
        self.channel_input = discord.ui.Label(
            text="Ticket Channel",
            component=self._channel_input,
            description="This channel will be used to create new ticket channels.",
        )

        self.add_item(self.channel_input)

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        self.channel_id = self._channel_input.values[0].id if self._channel_input.values else None

        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        await interaction.client.database.edit_ticket_config(guild_id=interaction.guild.id, channel_id=self.channel_id)
        await interaction.response.send_message("Updated ticket configuration.", ephemeral=True)


class TicketEditButton(discord.ui.Button):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__(emoji="\N{PENCIL}", style=discord.ButtonStyle.secondary)
        self.kwargs = kwargs

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        assert self.view is not None

        if interaction.guild is None:
            await interaction.followup.send("This command can only be used in a server (guild).", ephemeral=True)
            return

        self.kwargs: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild.id)  # type: ignore
        modal = TicketConfigModal(**self.kwargs)
        await interaction.response.send_modal(modal)
        await modal.wait()
