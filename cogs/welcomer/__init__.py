from __future__ import annotations

import logging
from string import Template
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot

_log = logging.getLogger("bot.cogs.welcomer")


class Welcomer(commands.Cog):
    """Send configured messages when members join or leave a guild."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", type(self).__name__)

    @commands.Cog.listener("on_member_join")
    async def member_welcome(self, member: discord.Member) -> None:
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

        await channel.send(
            self._format_message(message, member),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener("on_member_join")
    async def member_join_role(self, member: discord.Member) -> None:
        if not await self.bot.database.is_welcome_enabled(member.guild.id):
            return

        role_id = await self.bot.database.get_welcome_join_role_id(member.guild.id)
        if role_id is None:
            return

        role = member.guild.get_role(role_id)
        if role is None:
            return
        me = member.guild.me
        if me is None or not member.guild.me.guild_permissions.manage_roles:
            return
        if not member.guild.me.top_role > role:
            _log.warning(
                "Cannot assign join role %s to member %s in guild %s: bot's top role is lower than the join role.",
                role.id,
                member.id,
                member.guild.id,
            )
            return

        try:
            await member.add_roles(role, reason="Join role configured in Welcomer cog.")
        except discord.Forbidden:
            _log.warning(
                "Cannot assign join role %s to member %s in guild %s: missing permissions.",
                role.id,
                member.id,
                member.guild.id,
            )

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

        await channel.send(
            self._format_message(message, member),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @staticmethod
    def _format_message(message: str, member: discord.Member) -> str:
        try:
            template = Template(message)
            return template.safe_substitute(
                member_mention=member.mention,
                member_name=member.name,
                member_display_name=member.display_name,
                server_name=member.guild.name,
                count=member.guild.member_count,
            )
        except KeyError, ValueError:
            _log.warning(
                "Invalid welcome message format in guild %s",
                member.guild.id,
                exc_info=True,
            )
            return message


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Welcomer(bot))
