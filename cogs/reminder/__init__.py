from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from motor.motor_asyncio import AsyncIOMotorCollection

from dateutil import tz
import arrow
import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.robopages import SimplePages
from utilities.time import FriendlyTimeResult, UserFriendlyTime

log = logging.getLogger("cogs.reminder")

Collection = type[AsyncIOMotorCollection]


class Reminders(Cog):
    """Remind yourself of something after a certain amount of time."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.collection: Collection = bot.timers
        self.lock = asyncio.Lock()

        self.ON_TESTING = False

        self.create_timer = self.bot.create_timer
        self.delete_timer = self.bot.delete_timer

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{STOPWATCH}")

    async def _notify_user(self, *, user: discord.User | discord.Member, message: str) -> None:
        try:
            await user.send(message)
        except discord.Forbidden:
            pass

    async def notify_reminder_msg(self, ctx: Context, *, timestamp: int | float) -> None:
        discord_timestamp = f"<t:{int(timestamp)}:R>"
        msg = (
            f"{ctx.author.mention} you will be mentioned in {ctx.channel.mention} **{discord_timestamp}**\n"
            f"To delete your reminder consider typing `{ctx.clean_prefix}remind delete {ctx.message.id}`\n"
            f"> Syntax: `{ctx.clean_prefix}remind delete <message ID>`"
        )
        try:
            await ctx.author.send(msg, view=ctx.send_view())
            await ctx.reply(f"{ctx.author.mention} check your DM", delete_after=5)
        except discord.Forbidden:
            await ctx.reply(msg, delete_after=5)

    @commands.group(name="remindme", aliases=["remind", "reminder", "remind-me"], invoke_without_command=True)
    @Context.with_type
    async def remindme(
        self,
        ctx: Context[Parrot],
        *,
        when: Annotated[FriendlyTimeResult, UserFriendlyTime(commands.clean_content, default="...")],
    ) -> None:
        """Reminds you of something after a certain amount of time.

        The input can be any direct date (e.g. YYYY-MM-DD) or a human
        readable offset. Examples:

        - "next thursday at 3pm do something funny"
        - "do the dishes tomorrow"
        - "in 3 days do the thing"
        - "2d unmute someone"

        Times are in UTC unless a timezone is specified
        using the "timezone set" command.
        """
        timestamp = await self._get_timestamp(ctx.author.id, when)

        if not ctx.invoked_subcommand:
            await self.notify_reminder_msg(ctx, timestamp=timestamp)

            await self.create_timer(
                expires_at=timestamp,
                created_at=ctx.message.created_at.timestamp(),
                content=when.arg,
                message=ctx.message,
            )
            log.info("Created a reminder for %s. reminder exipres at %s", ctx.author, timestamp)

    @remindme.command(name="list", aliases=["all", "ls", "show"])
    @Context.with_type
    async def _list(self, ctx: Context) -> None:
        """To get all your reminders of first 10 active reminders."""
        ls = []
        log.info("Fetching reminders for %s from database.", ctx.author)

        async for data in self.collection.find({"messageAuthor": ctx.author.id}):
            self.bot.get_guild(data.get("guild", 0))
            ls.append(f"<t:{int(data['expires_at'])}:R> - {data['messageURL']} (`{data['_id']}`)\n" f"> {data['content']}")
            if len(ls) == 10:
                break

        if not ls:
            await ctx.send(f"{ctx.author.mention} you don't have any reminders")
            return
        p = SimplePages(ls, ctx=ctx, per_page=4)
        await p.start()

    @remindme.command(name="del", aliases=["delete", "remove", "rm"])
    @Context.with_type
    async def delremind(self, ctx: Context, message: int) -> None:
        """To delete the reminder."""
        timer = await self.bot.get_timer(_id=message)
        if not timer:
            await ctx.reply(f"{ctx.author.mention} reminder of ID: **{message}** not found")
            return

        if timer["messageAuthor"] != ctx.author.id:
            await ctx.reply(f"{ctx.author.mention} you can't delete other's reminder")
            return

        log.info("Deleting reminder of message id %s", message)
        delete_result = await self.bot.delete_timer(_id=message)
        if delete_result.deleted_count == 0:
            await ctx.reply(f"{ctx.author.mention} failed to delete reminder of ID: **{message}**")
        else:
            await ctx.reply(f"{ctx.author.mention} deleted reminder of ID: **{message}**")

    @remindme.command(name="dm")
    @Context.with_type
    async def remindmedm(
        self,
        ctx: Context,
        *,
        when: Annotated[FriendlyTimeResult, UserFriendlyTime(commands.clean_content, default="...")],
    ) -> None:
        """Same as remindme, but you will be mentioned in DM. Make sure you have DM open for the bot."""
        timestamp = await self._get_timestamp(ctx.author.id, when)
        await self.notify_reminder_msg(ctx, timestamp=timestamp)

        await self.create_timer(
            expires_at=timestamp,
            created_at=ctx.message.created_at.timestamp(),
            content=when.arg,
            message=ctx.message,
            dm_notify=True,
        )
        log.info("Created a reminder for %s. reminder exipres at %s", ctx.author, timestamp)

    @remindme.command(name="loop", aliases=["repeat"])
    @Context.with_type
    async def remindmeloop(
        self,
        ctx: Context,
        *,
        when: Annotated[FriendlyTimeResult, UserFriendlyTime(commands.clean_content, default="...")],
    ):
        """Same as remind me but you will get reminder on every given time.

        `$remind loop 1d To vote the bot`
        This will make a reminder for everyday `To vote the bot`
        """
        timestamp = when.dt.timestamp()
        now = discord.utils.utcnow().timestamp()
        if timestamp - now <= 300:
            return await ctx.reply(f"{ctx.author.mention} You can't set reminder for less than 5 minutes")

        timestamp = await self._get_timestamp(ctx.author.id, when)

        post = {
            "_id": ctx.message.id,
            "expires_at": timestamp,
            "created_at": ctx.message.created_at.timestamp(),
            "content": when.arg,
            "embed": None,
            "messageURL": ctx.message.jump_url,
            "messageAuthor": ctx.message.author.id,
            "messageChannel": ctx.message.channel.id,
            "dm_notify": True,
            "is_todo": False,
            "mod_action": None,
            "cmd_exec_str": None,
            "extra": {"name": "SET_TIMER_LOOP", "main": {"age": str(when)}},
        }
        await self.bot.create_timer(**post)
        log.info(
            "Created a loop reminder for %s. reminder exipres at %s",
            ctx.author,
            timestamp,
        )
        await self.notify_reminder_msg(ctx, timestamp=timestamp)

    @commands.command(name="reminders")
    @Context.with_type
    async def reminders(self, ctx: Context) -> None:
        """To get all your reminders of first 10 active reminders. Alias of `remind list`"""
        return await self._list(ctx)

    async def _get_timestamp(self, user_id: int, when: FriendlyTimeResult) -> float:
        if when.is_relative:
            now = arrow.get(when.dt)
            return now.timestamp()

        try:
            timezone = await self.bot.get_user_timezone(user_id)
            now = arrow.get(when.dt, timezone)
        except Exception:  # noqa
            now = arrow.get(when.dt)

        timestamp = now.datetime.timestamp()
        return timestamp


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Reminders(bot))
