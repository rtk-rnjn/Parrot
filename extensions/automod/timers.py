from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core import Bot


class AutomodTimers(commands.Cog):
    """Reverts temporary automod effects when their timers run out."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener("on_automod_unban_timer_complete")
    async def unban(self, metadata: Mapping[str, Any]) -> None:
        guild = self.bot.get_guild(int(metadata["guild_id"]))
        if guild is None:
            return
        try:
            await guild.unban(discord.Object(id=int(metadata["user_id"])), reason="Automod: temporary ban expired")
        except discord.NotFound:
            return
        except discord.HTTPException:
            log.exception("could not unban %s in %s", metadata["user_id"], guild.id)

    @commands.Cog.listener("on_automod_role_timer_complete")
    async def role(self, metadata: Mapping[str, Any]) -> None:
        guild = self.bot.get_guild(int(metadata["guild_id"]))
        if guild is None:
            return
        role = guild.get_role(int(metadata["role_id"]))
        if role is None:
            return

        user_id = int(metadata["user_id"])
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                return

        reason = "Automod: timed role change expired"
        try:
            if metadata["action"] == "remove" and role in member.roles:
                await member.remove_roles(role, reason=reason)
            elif metadata["action"] == "add" and role not in member.roles:
                await member.add_roles(role, reason=reason)
        except discord.HTTPException:
            log.exception("could not finish the timed role change for %s", user_id)

    @commands.Cog.listener("on_automod_slowmode_timer_complete")
    async def slowmode(self, metadata: Mapping[str, Any]) -> None:
        guild = self.bot.get_guild(int(metadata["guild_id"]))
        if guild is None:
            return
        channel = guild.get_channel_or_thread(int(metadata["channel_id"]))
        if channel is None or getattr(channel, "slowmode_delay", None) != metadata["applied"]:
            return

        if not isinstance(channel, discord.abc.Messageable):
            return
        try:
            await channel.edit(slowmode_delay=int(metadata["restore"]), reason="Automod: temporary slowmode ended")
        except discord.HTTPException:
            log.exception("could not restore slowmode in %s", channel.id)
