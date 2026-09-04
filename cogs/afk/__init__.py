from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.afk")


class AFK(commands.Cog):
    """Cog for handling AFK users."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.command(name="afk")
    async def afk(
        self,
        ctx: commands.Context[Parrot],
        *,
        reason: Annotated[str, commands.clean_content] = commands.parameter(description="Reason for going AFK", default="AFK"),
    ) -> None:
        """Set your AFK status."""
        assert isinstance(ctx.author, discord.Member) and isinstance(ctx.guild, discord.Guild)

        await self.bot.database_manager.set_user_as_afk(guild_id=ctx.guild.id, user_id=ctx.author.id, reason=reason)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        if ctx.guild.me.guild_permissions.manage_nicknames and ctx.guild.me.top_role > ctx.author.top_role:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")

    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message) -> None:
        """Remove AFK status when a user sends a message."""
        if message.author.bot or message.guild is None:
            return

        if not message.mentions:
            return

        for user in message.mentions:
            afk = await self.bot.database_manager.is_user_afk(guild_id=message.guild.id, user_id=user.id)
            if afk:
                continue

            reason = await self.bot.database_manager.get_afk_reason(guild_id=message.guild.id, user_id=user.id)
            await message.reply(f"{user.mention} is currently AFK: {reason}", allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        afk = await self.bot.database_manager.is_user_afk(guild_id=message.guild.id, user_id=message.author.id)
        if not afk:
            return

        await self.bot.database_manager.remove_user_from_afk(guild_id=message.guild.id, user_id=message.author.id)
        await message.reply(f"Welcome back {message.author.mention}")

        assert isinstance(message.author, discord.Member)

        if message.guild.me.guild_permissions.manage_nicknames and message.guild.me.top_role > message.author.top_role:
            if message.author.display_name.startswith("[AFK] "):
                new_nick = message.author.display_name[6:]
                await message.author.edit(nick=new_nick)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(AFK(bot))
