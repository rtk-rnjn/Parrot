from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.afk")

DEFAULT_REASON = "AFK"


class AFK(commands.Cog):
    """Handle AFK users."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", type(self).__name__)

    @commands.command(name="afk")
    async def afk(
        self,
        ctx: commands.Context[Parrot],
        *,
        reason: Annotated[str, commands.clean_content] = commands.parameter(description="Reason for going AFK", default=DEFAULT_REASON),
    ) -> None:
        """Set your AFK status."""

        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return

        reason = reason.strip() or DEFAULT_REASON

        await self.bot.database.set_user_as_afk(guild_id=ctx.guild.id, user_id=ctx.author.id, reason=reason)

        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        me = ctx.guild.me

        if me is not None and me.guild_permissions.manage_nicknames and me.top_role > ctx.author.top_role:
            nickname = f"[AFK] {ctx.author.display_name}"[:32]

            try:
                await ctx.author.edit(nick=nickname, reason="User marked themselves as AFK")
            except discord.HTTPException:
                _log.warning("Failed to update AFK nickname for %s (%s)", ctx.author, ctx.author.id, exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle AFK notifications and automatically remove AFK status."""

        if message.guild is None or message.author.bot:
            return

        afk_reason = await self.bot.database.get_afk_reason(guild_id=message.guild.id, user_id=message.author.id)

        mentioned_ids = {member.id for member in message.mentions if not member.bot}

        if mentioned_ids:
            afk_users = await self.bot.database.get_afk_users(guild_id=message.guild.id)

            for user_id, afk_reason in afk_users.items():
                member = message.guild.get_member(user_id)

                if member is None:
                    continue

                await message.reply(f"{member.mention} is currently AFK: {afk_reason}", allowed_mentions=discord.AllowedMentions.none())

        if afk_reason is None:
            return

        await self.bot.database.remove_user_from_afk(guild_id=message.guild.id, user_id=message.author.id)
        await message.reply(f"Welcome back, {message.author.mention}.", allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: Parrot) -> None:
    await bot.add_cog(AFK(bot))
