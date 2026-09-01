from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
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


@dataclass(slots=True)
class ErrorResponse:
    title: str
    description: str
    reset_cooldown: bool = False
    delete_after: float | None = None
    should_raise: bool = False


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

    def _title(self, text: str) -> str:
        return f"{QUESTION_MARK} {text} {QUESTION_MARK}"

    def _format_permissions(self, permissions: list[str]) -> str:
        missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in permissions]
        return human_join(missing, delim="`, `", final="and")

    def _get_object_by_fuzzy[T: _Named](self, *, argument: str, objects: Sequence[T]) -> tuple[T, str, int] | None:
        """Get an object from a list of objects by fuzzy matching."""
        if not argument:
            return None

        cut_off = 90
        names = [o.name for o in objects]
        if data := process.extractOne(argument, names, scorer=fuzz.WRatio, score_cutoff=cut_off):
            result, score, position = data
            return objects[position], result, int(score)
        return None

    def _should_ignore(self, ctx: commands.Context[Parrot], error: commands.CommandError) -> bool:
        if ctx.guild is None or ctx.author.bot or ctx.command is None:
            return True

        if hasattr(ctx.command, "on_error"):
            return True

        ignore = (
            commands.CommandNotFound,
            discord.NotFound,
            discord.Forbidden,
            commands.PrivateMessageOnly,
            commands.NotOwner,
        )
        return isinstance(error, ignore)

    async def _build_error_response(  # noqa: C901, PLR0911, PLR0912
        self,
        ctx: commands.Context[Parrot],
        error: commands.CommandError,
    ) -> ErrorResponse:
        if isinstance(error, commands.BotMissingPermissions):
            fmt = self._format_permissions(error.missing_permissions)
            return ErrorResponse(
                title=self._title("Bot Missing Permissions"),
                description=f"Please provide the following permission(s) to the bot.\nPermission(s) missing: {fmt}",
                reset_cooldown=True,
            )

        if isinstance(error, commands.CommandOnCooldown):
            now = arrow.utcnow().shift(seconds=error.retry_after).datetime
            discord_time = discord.utils.format_dt(now, "R")
            return ErrorResponse(
                title=self._title("Command On Cooldown"),
                description=f"You are on command cooldown, please retry **{discord_time}**",
                delete_after=error.retry_after,
            )

        if isinstance(error, commands.MissingPermissions):
            if await self.bot.is_owner(ctx.author):
                await ctx.reinvoke()
                return ErrorResponse(title="", description="")  # sentinel: no message needed
            fmt = self._format_permissions(error.missing_permissions)
            return ErrorResponse(
                title=self._title("Missing permissions"),
                description=f"You need the following permission(s) to run the command.\nPermission(s) missing: {fmt}",
                reset_cooldown=True,
            )

        if isinstance(error, commands.MissingRole):
            return ErrorResponse(
                title=self._title("Missing Role"),
                description=f"You need the role `{error.missing_role}` to run this command.",
                reset_cooldown=True,
            )

        if isinstance(error, commands.MissingAnyRole):
            fmt = human_join(list(error.missing_roles), delim="`, `", final="or")
            return ErrorResponse(
                title=self._title("Missing Role"),
                description=f"You need any of the following role(s) to use the command.\nRole(s) missing: {fmt}",
                reset_cooldown=True,
            )

        if isinstance(error, commands.NSFWChannelRequired):
            return ErrorResponse(
                title=self._title("NSFW Channel Required"),
                description="This command will only run in an NSFW-marked channel. [View example](https://i.imgur.com/oe4iK5i.gif)",
                reset_cooldown=True,
            )

        if isinstance(error, commands.BadArgument):
            return self._handle_bad_argument(ctx, error)

        if isinstance(error, (commands.MissingRequiredArgument, commands.BadUnionArgument, commands.TooManyArguments)):
            command = ctx.command
            aliases = f"|{'|'.join(command.aliases)}" if command.aliases else ""  # pyright: ignore[reportOptionalMemberAccess]
            usage = f"{ctx.clean_prefix}{command.qualified_name}{aliases} {command.signature}"  # pyright: ignore[reportOptionalMemberAccess]
            return ErrorResponse(
                title=self._title("Invalid Syntax"),
                description=f"Please use proper syntax.\n`{usage}`",
                reset_cooldown=True,
            )

        if isinstance(error, commands.BadLiteralArgument):
            literals = "`, `".join(str(i) for i in error.literals)
            return ErrorResponse(
                title=self._title("Invalid Literal(s)"),
                description=f"Please use proper Literals. Literal should be any one of the following: `{literals}`",
            )

        if isinstance(error, commands.MaxConcurrencyReached):
            return ErrorResponse(
                title=self._title("Max Concurrency Reached"),
                description="This command is already running in this server/channel by you. You have to wait for it to finish",
            )

        if isinstance(error, commands.CheckAnyFailure):
            desc = " or\n".join([e.__str__().format(ctx=ctx) for e in error.errors])
            return ErrorResponse(
                title=self._title("Unexpected Error"),
                description=desc,
                reset_cooldown=True,
            )

        if isinstance(error, commands.CheckFailure):
            return ErrorResponse(
                title=self._title("Unexpected Error"),
                description="You don't have the required permissions to use this command.",
                reset_cooldown=True,
            )

        if isinstance(error, asyncio.TimeoutError):
            return ErrorResponse(
                title=self._title("Timeout Error"),
                description="Command took too long to respond",
            )

        if isinstance(error, commands.InvalidEndOfQuotedStringError):
            return ErrorResponse(
                title=self._title("Invalid End Of Quoted String Error"),
                description="Invalid end of quoted string. Expected space after closing quotation mark. Did you forget to close the quotation mark?",
            )

        if isinstance(error, commands.UnexpectedQuoteError):
            return ErrorResponse(
                title=self._title("Unexpected Quote Error"),
                description="Unexpected quote mark. Did you forget to close the quotation mark?",
            )

        if isinstance(error, commands.DisabledCommand):
            return ErrorResponse(
                title=self._title("Disabled Command"),
                description="This command is disabled in this server, ask your server admin to enable it.",
            )

        return ErrorResponse(
            title=self._title("Well this is embarrassing!"),
            description=f"For some reason **{ctx.command.qualified_name}** is not working. If possible report this error.",  # pyright: ignore[reportOptionalMemberAccess]
            should_raise=True,
        )

    def _handle_bad_argument(self, ctx: commands.Context[Parrot], error: commands.BadArgument) -> ErrorResponse:  # noqa: C901, PLR0911, PLR0912
        description = str(error)
        title = self._title("Bad Argument")
        objects: Sequence[_Named] = []

        if isinstance(error, commands.MessageNotFound):
            description = "Message ID/Link you provided is either invalid or deleted"
            title = self._title("Message Not Found")
        elif isinstance(error, commands.MemberNotFound):
            description = "Member ID/Mention/Name you provided is invalid or bot can not see that Member"
            title = self._title("Member Not Found")
            objects = ctx.guild.members if ctx.guild else []
        elif isinstance(error, commands.UserNotFound):
            description = "User ID/Mention/Name you provided is invalid or bot can not see that User"
            title = self._title("User Not Found")
        elif isinstance(error, commands.ChannelNotFound):
            description = "Channel ID/Mention/Name you provided is invalid or bot can not see that Channel"
            title = self._title("Channel Not Found")
            if ctx.guild:
                objects = [*ctx.guild.text_channels, *ctx.guild.voice_channels]
        elif isinstance(error, commands.RoleNotFound):
            description = "Role ID/Mention/Name you provided is invalid or bot can not see that Role"
            title = self._title("Role Not Found")
            objects = ctx.guild.roles if ctx.guild else []
        elif isinstance(error, commands.EmojiNotFound):
            description = "Emoji ID/Name you provided is invalid or bot can not see that Emoji"
            title = self._title("Emoji Not Found")
            objects = ctx.guild.emojis if ctx.guild else []
        elif isinstance(error, commands.RangeError):
            description = f"Value you provided is out of range. Expected a value between {error.minimum} and {error.maximum}"
            title = self._title("Value Out Of Range")

        # optional fuzzy hint
        arg = getattr(error, "argument", None)
        if objects and isinstance(arg, str):
            obj = self._get_object_by_fuzzy(argument=arg, objects=objects)
            if obj:
                _, result, score = obj
                description += f"\nDid you mean: `{result}`?"
                description += f"\n-# Confidence: {score}%"

        return ErrorResponse(
            title=title,
            description=description,
            reset_cooldown=True,
        )

    async def _send_error_reply(self, ctx: commands.Context[Parrot], response: ErrorResponse) -> discord.Message | None:
        # sentinel path when owner reinvoke happens
        if not response.title and not response.description:
            return None
        return await ctx.reply(content=f"**{response.title}**\n{response.description}")

    async def _handle_message_cleanup(
        self,
        ctx: commands.Context[Parrot],
        msg: discord.Message | None,
        delete_after: float | None,
    ) -> None:
        if msg is None:
            return

        try:
            await self.bot.wait_for("message_delete", timeout=10, check=lambda m: m.id == ctx.message.id)
            await msg.delete(delay=0)
        except TimeoutError:
            if delete_after:
                await msg.delete(delay=max(delete_after - 10, 0))

    def _log_and_raise(self, ctx: commands.Context[Parrot], error: Exception) -> None:
        _log.exception(
            "Error in command `%s` invoked by `%s (ID: %s)` in guild `%s (ID: %s)`",
            ctx.command.qualified_name,  # pyright: ignore[reportOptionalMemberAccess]
            ctx.author,
            ctx.author.id,
            ctx.guild,
            ctx.guild.id,  # pyright: ignore[reportOptionalMemberAccess]
            exc_info=error,
        )
        raise error

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context[Parrot], error: commands.CommandError):
        await self.bot.wait_until_ready()

        original = getattr(error, "original", error)
        if self._should_ignore(ctx, original):
            return

        response = await self._build_error_response(ctx, original)

        # reinvoke sentinel: no outbound message
        if not response.title and not response.description:
            return

        if response.reset_cooldown and ctx.command:
            ctx.command.reset_cooldown(ctx)

        msg = await self._send_error_reply(ctx, response)
        await self._handle_message_cleanup(ctx, msg, response.delete_after)

        if response.should_raise:
            self._log_and_raise(ctx, original)
