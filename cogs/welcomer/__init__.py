from __future__ import annotations

import logging
from string import Template
from typing import TYPE_CHECKING, Annotated

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.welcomer")


class Welcomer(commands.Cog):
    """Send configured messages when members join or leave a guild."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", type(self).__name__)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if not await self.bot.database.is_welcome_enabled(member.guild.id):
            return

        channel_id = await self.bot.database.get_welcome_join_channel_id(member.guild.id)
        message = await self.bot.database.get_welcome_join_message(member.guild.id)
        if channel_id is None or message is None:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        me = member.guild.me
        if me is None or not channel.permissions_for(me).send_messages:
            return

        await channel.send(self._format_message(message, member), allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if not await self.bot.database.is_welcome_enabled(member.guild.id):
            return

        channel_id = await self.bot.database.get_welcome_leave_channel_id(member.guild.id)
        message = await self.bot.database.get_welcome_leave_message(member.guild.id)
        if channel_id is None or message is None:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        me = member.guild.me
        if me is None or not channel.permissions_for(me).send_messages:
            return

        await channel.send(self._format_message(message, member), allowed_mentions=discord.AllowedMentions.none())

    @staticmethod
    def _format_message(message: str, member: discord.Member) -> str:
        try:
            template = Template(message)
            return template.safe_substitute(
                member=member.mention,
                user=member.name,
                username=member.name,
                display_name=member.display_name,
                server=member.guild.name,
                server_name=member.guild.name,
                count=member.guild.member_count,
            )
        except KeyError, ValueError:
            _log.warning("Invalid welcome message format in guild %s", member.guild.id, exc_info=True)
            return message

    @commands.group(name="welcome", invoke_without_command=True)
    async def welcome(self, ctx: commands.Context[Parrot]) -> None:
        """Manage welcome and leave messages."""
        if ctx.guild is None:
            return

        enabled = await self.bot.database.is_welcome_enabled(ctx.guild.id)
        await ctx.reply(f"Welcome messages are currently {'enabled' if enabled else 'disabled'}.")

    @welcome.command(name="enable")
    @commands.has_guild_permissions(manage_guild=True)
    async def enable_welcome(self, ctx: commands.Context[Parrot]) -> None:
        """Enable welcome messages."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_welcome_config(guild_id=ctx.guild.id, enabled=True)
        await ctx.reply("Welcome messages enabled." if updated else "Welcome messages have not been configured yet.")

    @welcome.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    async def disable_welcome(self, ctx: commands.Context[Parrot]) -> None:
        """Disable welcome messages."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_welcome_config(guild_id=ctx.guild.id, enabled=False)
        await ctx.reply("Welcome messages disabled." if updated else "Welcome messages have not been configured yet.")

    @welcome.command(name="join-message", aliases=["welcome-message", "join_message", "welcome_message"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_join_message(
        self,
        ctx: commands.Context[Parrot],
        *,
        message: Annotated[str, commands.clean_content],
    ) -> None:
        """Set the member join message."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_welcome_config(guild_id=ctx.guild.id, on_member_join_message=message)
        await ctx.reply("Join message updated." if updated else "Welcome messages have not been configured yet.")

    @welcome.command(name="leave-message", aliases=["goodbye-message", "leave_message", "goodbye_message"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_leave_message(
        self,
        ctx: commands.Context[Parrot],
        *,
        message: Annotated[str, commands.clean_content],
    ) -> None:
        """Set the member leave message."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_welcome_config(guild_id=ctx.guild.id, on_member_leave_message=message)
        await ctx.reply("Leave message updated." if updated else "Welcome messages have not been configured yet.")

    @welcome.command(name="join-channel", aliases=["welcome-channel", "join_channel", "welcome_channel"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_join_channel(self, ctx: commands.Context[Parrot], channel: discord.TextChannel) -> None:
        """Set the channel used for member join messages."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_welcome_config(guild_id=ctx.guild.id, on_member_join_channel_id=channel.id)
        await ctx.reply("Join channel updated." if updated else "Welcome messages have not been configured yet.")

    @welcome.command(name="leave-channel", aliases=["goodbye-channel", "leave_channel", "goodbye_channel"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_leave_channel(self, ctx: commands.Context[Parrot], channel: discord.TextChannel) -> None:
        """Set the channel used for member leave messages."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_welcome_config(guild_id=ctx.guild.id, on_member_leave_channel_id=channel.id)
        await ctx.reply("Leave channel updated." if updated else "Welcome messages have not been configured yet.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Welcomer(bot))
