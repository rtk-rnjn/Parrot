from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

import arrow
import discord
from discord.ext import commands
from rapidfuzz import fuzz, process

from core.utils import human_join

if TYPE_CHECKING:
    from core.bot import Parrot

QUESTION_MARK = "\N{BLACK QUESTION MARK ORNAMENT}"

_log = logging.getLogger("bot.cogs.events.error")


class _Named(Protocol):
    name: str


class _Command(commands.Cog, command_attrs={"hidden": True}):
    """This category is of no use for you, ignore it."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context[Parrot]):
        if ctx.author.bot or ctx.guild is None:
            return

        payload = {
            "command": ctx.command.qualified_name if ctx.command else None,
            "author_id": ctx.author.id,
            "message_id": ctx.message.id,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "message_conent": ctx.message.content,
            "is_command_failed": ctx.command_failed if ctx.command else None,
        }
        _log.debug("Command invoked: %s", payload)

    def _get_object_by_fuzzy[T: _Named](self, *, argument: str, objects: Sequence[T]) -> tuple[T, str, int] | None:
        """Get an object from a list of objects by fuzzy matching."""
        if not argument:
            return None
        CUT_OFF = 90
        names = [o.name for o in objects]
        if data := process.extractOne(argument, names, scorer=fuzz.WRatio, score_cutoff=CUT_OFF):
            result, score, position = data
            return objects[position], result, int(score)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context[Parrot], error: commands.CommandError):  # noqa: PLR0912, PLR0915, C901
        await self.bot.wait_until_ready()
        # elif command has local error handler, return
        if hasattr(ctx.command, "on_error"):
            return

        # get the original exception
        error = getattr(error, "original", error)
        TO_RAISE_ERROR, DELETE_AFTER, RESET_COOLDOWN = False, None, False
        ignore = (
            commands.CommandNotFound,
            discord.NotFound,
            discord.Forbidden,
            commands.PrivateMessageOnly,
            commands.NotOwner,
        )

        if isinstance(error, ignore) or ctx.guild is None or ctx.author.bot or ctx.command is None:
            return

        error_title = f"{QUESTION_MARK} Unexpected Error {QUESTION_MARK}"
        error_description = ""
        if isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
            fmt = human_join(missing, delim="`, `", final="and")
            error_description = f"Please provide the following permission(s) to the bot.\nPermission(s) missing: {fmt}"
            error_title = f"{QUESTION_MARK} Bot Missing Permissions {QUESTION_MARK}"
            RESET_COOLDOWN = True

        elif isinstance(error, commands.CommandOnCooldown):
            now = arrow.utcnow().shift(seconds=error.retry_after).datetime
            DELETE_AFTER = error.retry_after
            discord_time = discord.utils.format_dt(now, "R")
            error_description = f"You are on command cooldown, please retry **{discord_time}**"
            error_title = f"{QUESTION_MARK} Command On Cooldown {QUESTION_MARK}"

        elif isinstance(error, commands.MissingPermissions):
            if await self.bot.is_owner(ctx.author):
                await ctx.reinvoke()
                return

            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
            fmt = human_join(missing, delim="`, `", final="and")

            error_description = f"You need the following permission(s) to run the command.\nPermission(s) missing: {fmt}"
            error_title = f"{QUESTION_MARK} Missing permissions {QUESTION_MARK}"
            RESET_COOLDOWN = True

        elif isinstance(error, commands.MissingRole):
            error_description = f"You need the role `{error.missing_role}` to run this command."
            error_title = f"{QUESTION_MARK} Missing Role {QUESTION_MARK}"
            RESET_COOLDOWN = True

        elif isinstance(error, commands.MissingAnyRole):
            missing = list(error.missing_roles)
            fmt = human_join(missing, delim="`, `", final="or")
            error_description = f"You need any of the following role(s) to use the command.\nRole(s) missing: {fmt}"
            error_title = f"{QUESTION_MARK} Missing Role {QUESTION_MARK}"
            RESET_COOLDOWN = True

        elif isinstance(error, commands.NSFWChannelRequired):
            error_description = "This command will only run in an NSFW-marked channel. [View example](https://i.imgur.com/oe4iK5i.gif)"
            error_title = f"{QUESTION_MARK} NSFW Channel Required {QUESTION_MARK}"

            RESET_COOLDOWN = True

        elif isinstance(error, commands.BadArgument):
            RESET_COOLDOWN = True
            objects = []
            if isinstance(error, commands.MessageNotFound):
                error_description = "Message ID/Link you provided is either invalid or deleted"
                error_title = f"{QUESTION_MARK} Message Not Found {QUESTION_MARK}"

            elif isinstance(error, commands.MemberNotFound):
                error_description = "Member ID/Mention/Name you provided is invalid or bot can not see that Member"
                error_title = f"{QUESTION_MARK} Member Not Found {QUESTION_MARK}"
                objects = ctx.guild.members

            elif isinstance(error, commands.UserNotFound):
                error_description = "User ID/Mention/Name you provided is invalid or bot can not see that User"
                error_title = f"{QUESTION_MARK} User Not Found {QUESTION_MARK}"

            elif isinstance(error, commands.ChannelNotFound):
                error_description = "Channel ID/Mention/Name you provided is invalid or bot can not see that Channel"
                error_title = f"{QUESTION_MARK} Channel Not Found {QUESTION_MARK}"
                objects = ctx.guild.text_channels + ctx.guild.voice_channels

            elif isinstance(error, commands.RoleNotFound):
                error_description = "Role ID/Mention/Name you provided is invalid or bot can not see that Role"
                error_title = f"{QUESTION_MARK} Role Not Found {QUESTION_MARK}"
                objects = ctx.guild.roles

            elif isinstance(error, commands.EmojiNotFound):
                error_description = "Emoji ID/Name you provided is invalid or bot can not see that Emoji"
                error_title = f"{QUESTION_MARK} Emoji Not Found {QUESTION_MARK}"
                objects = ctx.guild.emojis
            elif isinstance(error, commands.RangeError):
                error_description = f"Value you provided is out of range. Expected a value between {error.minimum} and {error.maximum}"
                error_title = f"{QUESTION_MARK} Value Out Of Range {QUESTION_MARK}"
            else:
                error_description = f"{error}"
                error_title = f"{QUESTION_MARK} Bad Argument {QUESTION_MARK}"

            if objects:
                obj = self._get_object_by_fuzzy(argument=error.argument, objects=objects)
                if obj:
                    _, result, score = obj
                    error_description += f"\nDid you mean: `{result}`?"
                    error_description += f"\n-# Confidence: {score}%"

        elif isinstance(
            error,
            commands.MissingRequiredArgument | commands.BadUnionArgument | commands.TooManyArguments,
        ):
            command = ctx.command
            RESET_COOLDOWN = True
            error_description = f"Please use proper syntax.\n`{ctx.clean_prefix}{command.qualified_name}{'|' if command.aliases else ''}{'|'.join(command.aliases or '')} {command.signature}`"

            error_title = f"{QUESTION_MARK} Invalid Syntax {QUESTION_MARK}"

        elif isinstance(error, commands.BadLiteralArgument):
            error_description = (
                f"Please use proper Literals. Literal should be any one of the following: `{'`, `'.join(str(i) for i in error.literals)}`"
            )
            error_title = f"{QUESTION_MARK} Invalid Literal(s) {QUESTION_MARK}"

        elif isinstance(error, commands.MaxConcurrencyReached):
            error_description = "This command is already running in this server/channel by you. You have to wait for it to finish"
            error_title = f"{QUESTION_MARK} Max Concurrency Reached {QUESTION_MARK}"

        elif isinstance(error, commands.CheckAnyFailure):
            RESET_COOLDOWN = True
            error_description = " or\n".join([error.__str__().format(ctx=ctx) for error in error.errors])
            error_title = f"{QUESTION_MARK} Unexpected Error {QUESTION_MARK}"

        elif isinstance(error, commands.CheckFailure):
            RESET_COOLDOWN = True
            error_title = f"{QUESTION_MARK} Unexpected Error {QUESTION_MARK}"
            error_description = "You don't have the required permissions to use this command."

        elif isinstance(error, asyncio.TimeoutError):
            error_description = "Command took too long to respond"
            error_title = f"{QUESTION_MARK} Timeout Error {QUESTION_MARK}"

        elif isinstance(error, commands.InvalidEndOfQuotedStringError):
            error_description = (
                "Invalid end of quoted string. Expected space after closing quotation mark. Did you forget to close the quotation mark?"
            )
            error_title = f"{QUESTION_MARK} Invalid End Of Quoted String Error {QUESTION_MARK}"

        elif isinstance(error, commands.UnexpectedQuoteError):
            error_description = "Unexpected quote mark. Did you forget to close the quotation mark?"
            error_title = f"{QUESTION_MARK} Unexpected Quote Error {QUESTION_MARK}"

        elif isinstance(error, commands.DisabledCommand):
            error_description = "This command is disabled in this server, ask your server admin to enable it."
            error_title = f"{QUESTION_MARK} Disabled Command {QUESTION_MARK}"

        else:
            error_description = f"For some reason **{ctx.command.qualified_name}** is not working. If possible report this error."
            error_title = f"{QUESTION_MARK} Well this is embarrassing! {QUESTION_MARK}"
            TO_RAISE_ERROR = True

        if RESET_COOLDOWN:
            ctx.command.reset_cooldown(ctx)

        msg: discord.Message = await ctx.reply(content=f"**{error_title}**\n{error_description}")

        try:
            if msg:
                await self.bot.wait_for("message_delete", timeout=10, check=lambda m: m.id == ctx.message.id)
                await msg.delete(delay=0)
        except TimeoutError:
            if DELETE_AFTER:
                await msg.delete(delay=max(DELETE_AFTER - 10, 0))

        if TO_RAISE_ERROR:
            _log.exception(
                "Error in command `%s` invoked by `%s (ID: %s)` in guild `%s (ID: %s)`",
                ctx.command.qualified_name,
                ctx.author,
                ctx.author.id,
                ctx.guild,
                ctx.guild.id,
                exc_info=error,
            )
            raise error
