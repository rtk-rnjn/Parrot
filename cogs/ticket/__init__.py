from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot


class TicketCreateView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="create_ticket_button",
    )
    async def create_ticket_button(self, interaction: discord.Interaction[Parrot], button: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server (guild).", ephemeral=True)
            return

        await interaction.response.defer()

        if isinstance(interaction.channel, discord.TextChannel):
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

        await interaction.followup.send(
            "Ticket creation is not configured properly. Please contact a server administrator.",
            ephemeral=True,
        )


class Ticket(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        async for message_id in self.bot.database.get_all_ticket_config_message_id():
            self.bot.add_view(TicketCreateView(), message_id=message_id)

    @commands.group(name="ticket", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def ticket(self, ctx: commands.Context[Parrot]) -> None:
        """Manage ticket settings.

        You must have the "Administrator" permission to use this command.

        This command has no cooldown.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @ticket.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx: commands.Context[Parrot], *, message: str) -> None:
        """Set up the ticket system in a channel.

        You must have the "Administrator" permission to use this command.

        This command has no cooldown.
        """
        assert ctx.guild is not None

        channel_id = await self.bot.database.get_ticket_config_channel_id(ctx.guild.id)
        embed = discord.Embed(
            title=f"{ctx.guild.name} Ticket System",
            description="Click on the button below to create a new ticket. A staff member will assist you shortly. Please don't create multiple tickets for the same issue.",
        )
        channel = ctx.guild.get_channel(channel_id) if channel_id is not None else None
        if channel is None:
            channel = ctx.channel

        if TYPE_CHECKING:
            assert isinstance(channel, discord.TextChannel), "The ticket channel must be a text channel."

        msg = await channel.send(embed=embed, view=TicketCreateView())

        await self.bot.database.edit_ticket_config(
            guild_id=ctx.guild.id,
            bot_message_id=msg.id,
            bot_channel_channel_id=channel.id,
            channel_id=channel.id,
        )

    @ticket.command(name="open", aliases=["create"])
    @commands.bot_has_guild_permissions(create_private_threads=True)
    async def ticket_open(self, ctx: commands.Context[Parrot]) -> None:
        """Open a new ticket; without using the buttons

        No special user permissions are required.
        The bot must have the "Create Private Threads" permission to run this command successfully.

        This command has no cooldown.
        """
        assert ctx.guild is not None
        assert isinstance(ctx.author, discord.Member)

        channel_id = await self.bot.database.get_ticket_config_channel_id(ctx.guild.id)

        if channel_id is None:
            await ctx.reply("Ticket system is not set up. Please contact a server administrator.")
            return

        channel = ctx.guild.get_channel(channel_id)
        if channel is None:
            await ctx.reply("Ticket system is not set up properly. Please contact a server administrator.")
            return

        if isinstance(channel, discord.TextChannel):
            thread = await channel.create_thread(
                name=f"ticket-{ctx.author.name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60,
                reason="Ticket created by user.",
            )
            await thread.add_user(ctx.author)
            await thread.send(f"{ctx.author.mention} Your ticket has been created. A staff member will assist you shortly.")
            await ctx.reply(f"Your ticket has been created: {thread.mention}", ephemeral=True)
            return

    @ticket.command(name="delete")
    @commands.has_permissions(manage_threads=True)
    @commands.bot_has_permissions(manage_threads=True)
    async def ticket_delete(self, ctx: commands.Context[Parrot]) -> None:
        """Close the ticket in the current channel.

        You must have the "Manage Threads" permission to use this command.
        The bot must have the "Manage Threads" permission to run this command successfully.

        This command has no cooldown.
        """
        if ctx.guild is None:
            await ctx.reply("This command can only be used in a server (guild).")
            return

        if not isinstance(ctx.channel, discord.Thread):
            await ctx.reply("This command can only be used in a ticket thread.")
            return

        if not ctx.channel.name.startswith("ticket-"):
            await ctx.reply("This command can only be used in a ticket thread.")
            return

        await ctx.channel.delete()

    @ticket.command(name="resolved", aliases=["close", "archive"])
    async def ticket_resolved(self, ctx: commands.Context[Parrot]) -> None:
        """Mark the ticket in the current channel as resolved.

        This command has no cooldown.
        """
        if ctx.guild is None:
            await ctx.reply("This command can only be used in a server (guild).")
            return

        if not isinstance(ctx.channel, discord.Thread):
            await ctx.reply("This command can only be used in a ticket thread.")
            return

        ticket_name = ctx.channel.name
        if not ticket_name.startswith("ticket-"):
            await ctx.reply("This command can only be used in a ticket thread.")
            return

        await ctx.channel.edit(archived=True, locked=True)
        await ctx.reply("This ticket has been marked as resolved and archived.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Ticket(bot))
