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

        self.add_item(self.channel_input)
        self.add_item(self.category_input)
        self.add_item(self.use_thread_input)

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
        await interaction.response.send_message("Updated ticket configuration.", ephemeral=True)


class TicketCreateView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket_button")
    async def create_ticket_button(self, interaction: discord.Interaction[Parrot], button: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        await interaction.response.defer()
        category_id = await interaction.client.database.get_ticket_config_category_id(interaction.guild.id)
        use_thread = await interaction.client.database.is_ticket_config_use_thread(interaction.guild.id)

        if use_thread and isinstance(interaction.channel, discord.TextChannel):
            thread = await interaction.channel.create_thread(
                name=f"ticket-{interaction.user.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60,
                reason="Ticket created by user.",
            )
            await thread.add_user(interaction.user)
            await thread.send(f"{interaction.user.mention} Your ticket has been created. A staff member will assist you shortly.")
            await interaction.followup.send(f"Your ticket has been created: {thread.mention}", ephemeral=True)
            return

        elif category_id is not None:
            category = interaction.guild.get_channel(category_id)
            user = interaction.user
            if category is not None and isinstance(category, discord.CategoryChannel) and isinstance(user, discord.Member):
                ticket_channel = await interaction.guild.create_text_channel(
                    name=f"ticket-{interaction.user.name}",
                    category=category,
                    reason="Ticket created by user.",
                    overwrites={
                        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    },
                )
                await ticket_channel.set_permissions(user, read_messages=True, send_messages=True)
                await ticket_channel.send(f"{interaction.user.mention} Your ticket has been created. A staff member will assist you shortly.")
                await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
                return

        else:
            await interaction.followup.send("Ticket creation is not configured properly. Please contact a server administrator.", ephemeral=True)


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

        channel_id = await interaction.client.database.get_ticket_config_channel_id(interaction.guild.id)
        embed = discord.Embed(
            title=f"{interaction.guild.name} Ticket System",
            description="Click on the button below to create a new ticket. A staff member will assist you shortly. Please don't create multiple tickets for the same issue.",
        )
        channel = interaction.guild.get_channel(channel_id) if channel_id is not None else None
        if channel is None:
            return

        if TYPE_CHECKING:
            assert isinstance(channel, discord.TextChannel), "The ticket channel must be a text channel."

        message = await channel.send(embed=embed, view=TicketCreateView())

        await interaction.client.database.edit_ticket_config(
            guild_id=interaction.guild.id,
            bot_message_id=message.id,
            bot_channel_channel_id=channel.id,
        )
