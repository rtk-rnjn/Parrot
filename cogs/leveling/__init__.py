from __future__ import annotations

import logging
import math
import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

from .utils import rank_card

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.leveling")

XP_FLUSH_INTERVAL_SECONDS = 30


class Leveling(commands.Cog):
    """Award message XP with Redis-backed buffering and periodic persistence."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._enabled_guilds: dict[int, bool] = {}
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)
        _log.info("Cog loaded: %s", type(self).__name__)

    async def cog_load(self) -> None:
        self.flush_xp.start()

    async def cog_unload(self) -> None:
        self.flush_xp.cancel()
        await self.bot.database.flush_all_leveling_data()

    def _calculate_xp_for_message(self, message: discord.Message) -> int:
        """Calculate the XP to award for a message."""
        if message.guild is None:
            return 0

        message_length = len(message.content)
        if message_length < 10:
            return random.randint(1, 3)
        elif message_length < 50:
            return random.randint(3, 5)
        elif message_length < 100:
            return random.randint(5, 10)
        else:
            return random.randint(10, 15)

    def _calculate_level_for_xp(self, xp: int) -> int:
        """Calculate the level based on XP."""
        return math.isqrt(xp // 100)

    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate the total XP required for a given level."""
        return level * level * 100

    def _calculate_xp_to_next_level(self, xp: int) -> int:
        """Calculate the XP required to reach the next level."""
        current_level = self._calculate_level_for_xp(xp)
        next_level_xp = self._calculate_xp_for_level(current_level + 1)
        return next_level_xp - xp

    def set_enabled_cache(self, guild_id: int, enabled: bool) -> None:
        self._enabled_guilds[guild_id] = enabled

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        enabled = self._enabled_guilds.get(message.guild.id)
        if enabled is None:
            enabled = await self.bot.database.is_leveling_enabled(message.guild.id)
            self._enabled_guilds[message.guild.id] = enabled

        if not enabled:
            return

        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit() if bucket else None
        if retry_after:
            return

        await self.bot.database.incr_user_xp(
            guild_id=message.guild.id,
            user_id=message.author.id,
            xp=self._calculate_xp_for_message(message),
        )

    @tasks.loop(seconds=XP_FLUSH_INTERVAL_SECONDS)
    async def flush_xp(self) -> None:
        flushed_users = await self.bot.database.flush_all_leveling_data()
        if flushed_users:
            _log.debug("Flushed XP for %s users", flushed_users)

    @flush_xp.before_loop
    async def before_flush_xp(self) -> None:
        await self.bot.wait_until_ready()

    @commands.group(name="leveling", invoke_without_command=True)
    async def leveling(self, ctx: commands.Context[Parrot]) -> None:
        """Manage or view server leveling."""
        if ctx.guild is None:
            return

        enabled = await self.bot.database.is_leveling_enabled(ctx.guild.id)
        await ctx.reply(f"Leveling is currently {'enabled' if enabled else 'disabled'}.")

    @leveling.command(name="enable")
    @commands.has_guild_permissions(manage_guild=True)
    async def enable_leveling(self, ctx: commands.Context[Parrot]) -> None:
        """Enable leveling in this server."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_leveling_config(guild_id=ctx.guild.id, enabled=True)
        if not updated:
            await ctx.reply("Leveling has not been configured for this server yet.")
            return

        self._enabled_guilds[ctx.guild.id] = True
        await ctx.reply("Leveling enabled.")

    @leveling.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    async def disable_leveling(self, ctx: commands.Context[Parrot]) -> None:
        """Disable leveling in this server."""
        if ctx.guild is None:
            return

        updated = await self.bot.database.edit_leveling_config(guild_id=ctx.guild.id, enabled=False)
        if not updated:
            await ctx.reply("Leveling has not been configured for this server yet.")
            return

        self._enabled_guilds[ctx.guild.id] = False
        await ctx.reply("Leveling disabled.")

    @leveling.command(name="role")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_level_role(self, ctx: commands.Context[Parrot], level: commands.Range[int, 1, 100], role: discord.Role) -> None:
        """Assign a role when a member reaches a level."""
        if ctx.guild is None:
            return

        await self.bot.database.set_level_role(guild_id=ctx.guild.id, level=level, role_id=role.id)
        await ctx.reply(f"Level {level} will award {role.mention}.")

    @leveling.command(name="unrole")
    @commands.has_guild_permissions(manage_guild=True)
    async def remove_level_role(self, ctx: commands.Context[Parrot], level: commands.Range[int, 1, 100]) -> None:
        """Remove a role assignment from a level."""
        if ctx.guild is None:
            return

        await self.bot.database.remove_level_role(guild_id=ctx.guild.id, level=level)
        await ctx.reply(f"Removed the role assignment for level {level}.")

    @commands.command(name="rank", aliases=["level"])
    async def rank(self, ctx: commands.Context[Parrot], *, member: discord.Member | None = None) -> None:
        """Show a member's current level and XP."""
        if ctx.guild is None:
            return

        user = member or ctx.author
        xp = await self.bot.database.get_user_xp(guild_id=ctx.guild.id, user_id=user.id)
        xp = xp or 0

        rank = await self.bot.database.predict_user_rank(guild_id=ctx.guild.id, user_id=user.id)
        file = await rank_card(
            level=self._calculate_level_for_xp(xp),
            rank=rank or 1,
            member=user,
            session=self.bot.http_session,
            xp_required_for_next_level=self._calculate_xp_to_next_level(xp),
            current_level_xp=xp,
        )
        await ctx.reply(file=file, mention_author=False)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Leveling(bot))
