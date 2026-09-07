from __future__ import annotations

import logging
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from PIL import Image

from .card import birthday_card_file

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.birthday")
DATE_FORMAT = "%m-%d"


def parse_birthday(value: str) -> str:
    return datetime.strptime(value.strip(), DATE_FORMAT).strftime(DATE_FORMAT)


class Birthday(commands.Cog):
    """Store member birthdays and announce them in a configured channel."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._announced: set[tuple[int, str, int]] = set()
        _log.info("Cog loaded: %s", type(self).__name__)

    async def cog_load(self) -> None:
        self.check_birthdays.start()

    async def cog_unload(self) -> None:
        self.check_birthdays.cancel()

    @commands.group(name="birthday", invoke_without_command=True)
    async def birthday(self, ctx: commands.Context[Parrot]) -> None:
        """View birthday status or manage your birthday."""
        if ctx.guild is None:
            return

        birthday = await self.bot.database_manager.get_user_birthday(ctx.author.id)
        config = await self.bot.database_manager.get_birthday_config(ctx.guild.id)
        channel_id = config.get("channel_id") if config else None
        status = "enabled" if config and config["enabled"] else "disabled"
        saved = birthday or "not set"
        channel = f" in <#{channel_id}>" if channel_id else ""
        await ctx.reply(f"Your birthday: **{saved}**. Server wishes are **{status}**{channel}.")

    @birthday.command(name="set")
    async def set_birthday(self, ctx: commands.Context[Parrot], date: str) -> None:
        """Set your birthday in MM-DD format."""
        try:
            birthday = parse_birthday(date)
        except ValueError:
            await ctx.reply("Use a valid birthday in `MM-DD` format, for example `04-23`.")
            return

        await self.bot.database_manager.set_user_birthday(user_id=ctx.author.id, birthday=birthday)
        await ctx.reply(f"Your birthday is set to **{birthday}**.")

    @birthday.command(name="clear")
    async def clear_birthday(self, ctx: commands.Context[Parrot]) -> None:
        """Remove your saved birthday."""
        await self.bot.database_manager.clear_user_birthday(ctx.author.id)
        await ctx.reply("Your birthday has been cleared.")

    @birthday.command(name="set-channel")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_channel(self, ctx: commands.Context[Parrot], channel: discord.TextChannel) -> None:
        """Choose where birthday wishes are sent."""
        await self.bot.database_manager.edit_birthday_config(guild_id=ctx.guild.id, channel_id=channel.id)
        await ctx.reply(f"Birthday wishes will be sent in {channel.mention}.")

    @birthday.command(name="enable")
    @commands.has_guild_permissions(manage_guild=True)
    async def enable(self, ctx: commands.Context[Parrot]) -> None:
        """Enable birthday wishes for this server."""
        config = await self.bot.database_manager.get_birthday_config(ctx.guild.id)
        if not config or config["channel_id"] is None:
            await ctx.reply("Set a birthday channel first with `birthday set-channel #channel`.")
            return
        await self.bot.database_manager.edit_birthday_config(guild_id=ctx.guild.id, enabled=True)
        await ctx.reply("Birthday wishes enabled.")

    @birthday.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    async def disable(self, ctx: commands.Context[Parrot]) -> None:
        """Disable birthday wishes for this server."""
        await self.bot.database_manager.edit_birthday_config(guild_id=ctx.guild.id, enabled=False)
        await ctx.reply("Birthday wishes disabled.")

    @tasks.loop(minutes=30)
    async def check_birthdays(self) -> None:
        today = datetime.now(UTC).strftime(DATE_FORMAT)
        users = await self.bot.database_manager.get_users_with_birthdays()
        birthday_users = {user["_id"]: user for user in users if user.get("birthday") == today}

        for guild in self.bot.guilds:
            config = await self.bot.database_manager.get_birthday_config(guild.id)
            if not config or not config["enabled"] or config["channel_id"] is None:
                continue

            channel = guild.get_channel(config["channel_id"])
            if not isinstance(channel, discord.TextChannel):
                continue

            for member in guild.members:
                announcement_key = (guild.id, today, member.id)
                if member.bot or member.id not in birthday_users or announcement_key in self._announced:
                    continue
                await self._send_wish(channel, member, today)
                self._announced.add(announcement_key)

    @check_birthdays.before_loop
    async def before_check_birthdays(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_wish(self, channel: discord.TextChannel, member: discord.Member, birthday: str) -> None:
        avatar = None
        try:
            avatar = Image.open(BytesIO(await member.display_avatar.read()))
        except discord.HTTPException, OSError:
            _log.debug("Could not download avatar for %s", member.id, exc_info=True)

        try:
            await channel.send(content=f"Happy birthday, {member.mention}!", file=birthday_card_file(member.display_name, birthday, avatar))
        except discord.HTTPException:
            _log.exception("Could not send birthday wish for %s in guild %s", member.id, channel.guild.id)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Birthday(bot))
