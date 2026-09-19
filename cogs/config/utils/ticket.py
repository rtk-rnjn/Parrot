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
        self.category_id = kwargs["ticket_config"]["category_id"]
        self.use_thread = kwargs["ticket_config"]["use_thread"]

        self._channel_input = discord.ui.ChannelSelect(
            placeholder="Select a channel for tickets...",
            channel_types=[discord.ChannelType.text],
            default_values=[discord.Object(id=self.channel_id)] if self.channel_id is not None else [],
            min_values=0,
            max_values=1,
        )
        self.channel_input = discord.ui.Label(
            text="Ticket Channel",
            component=self._channel_input,
            description="This channel will be used to create new ticket channels.",
        )

        self._category_input = discord.ui.ChannelSelect(
            placeholder="Select a category for tickets...",
            channel_types=[discord.ChannelType.category],
            default_values=[discord.Object(id=self.category_id)] if self.category_id is not None else [],
            min_values=0,
            max_values=1,
        )
        self.category_input = discord.ui.Label(
            text="Ticket Category",
            component=self._category_input,
            description="This category will be used to create new ticket channels.",
        )

        self._use_thread_input = discord.ui.Checkbox(
            default=self.use_thread,
        )
        self.use_thread_input = discord.ui.Label(
            text="Use Threads",
            component=self._use_thread_input,
            description="If enabled, tickets will be created as threads instead of channels.",
        )

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        self.channel_id = self._channel_input.values[0].id if self._channel_input.values else None
        self.category_id = self._category_input.values[0].id if self._category_input.values else None
        self.use_thread = self._use_thread_input.value

        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        await interaction.client.database.edit_ticket_config(
            guild_id=interaction.guild.id,
            channel_id=self.channel_id,
            category_id=self.category_id,
            use_thread=self.use_thread,
        )


class TicketEditButton(discord.ui.Button):
    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__(label="Edit Ticket Configuration", style=discord.ButtonStyle.primary)
        self.kwargs = kwargs

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        self.kwargs: GuildConfiguration = await interaction.client.database.get_guild_configuration(interaction.guild.id)  # type: ignore
        modal = TicketConfigModal(**self.kwargs)
        await interaction.response.send_modal(modal)
        await modal.wait()
