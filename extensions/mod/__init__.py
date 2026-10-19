from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import re
import textwrap
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict

import discord
from discord.ext import commands

from core import FutureTime
from core.utils import PaginationView

if TYPE_CHECKING:
    from core import Bot
    from core.utils.database.models import ModAction

_log = logging.getLogger(__name__)

REASON_LIMIT = 512
DISCORD_MESSAGE_LIMIT = 1900
DISCORD_HARD_LIMIT = 2000
MAX_DISPLAY_TARGETS = 5
MAX_BULK_BAN = 200
MAX_TIMEOUT = datetime.timedelta(days=28)  # Discord's hard limit for native timeouts
CASES_PER_PAGE = 8
MAX_CASES_SHOWN = 100

WARN_VIOLATION = "warn"
WARN_EXPIRY: datetime.timedelta | None = datetime.timedelta(days=60)

ModActionType = Literal[
    "kick",
    "ban",
    "softban",
    "unban",
    "mute",
    "unmute",
    "timeout",
    "untimeout",
    "warn",
    "unwarn",
    "clearwarns",
    "purge",
]


_ACTION_META: dict[str, tuple[str, str, discord.Colour]] = {
    "kick": ("\N{WOMANS BOOTS}", "Member Kicked", discord.Colour.orange()),
    "ban": ("\N{HAMMER}", "Member Banned", discord.Colour.red()),
    "softban": ("\N{HAMMER AND WRENCH}", "Member Softbanned", discord.Colour.dark_red()),
    "unban": ("\N{DOVE OF PEACE}", "Member Unbanned", discord.Colour.green()),
    "mute": ("\N{SPEAKER WITH CANCELLATION STROKE}", "Member Muted", discord.Colour.dark_orange()),
    "unmute": ("\N{SPEAKER WITH THREE SOUND WAVES}", "Member Unmuted", discord.Colour.green()),
    "timeout": ("\N{HOURGLASS WITH FLOWING SAND}", "Member Timed Out", discord.Colour.gold()),
    "untimeout": ("\N{ALARM CLOCK}", "Timeout Removed", discord.Colour.green()),
    "warn": ("\N{WARNING SIGN}", "Member Warned", discord.Colour.yellow()),
    "unwarn": ("\N{WHITE HEAVY CHECK MARK}", "Warning Removed", discord.Colour.green()),
    "clearwarns": ("\N{BROOM}", "Warnings Cleared", discord.Colour.green()),
    "purge": ("\N{WASTEBASKET}", "Messages Purged", discord.Colour.blurple()),
}


def _truncate(text: str, width: int) -> str:
    return textwrap.shorten(text, width=width, placeholder="\N{HORIZONTAL ELLIPSIS}")


def _case_note(*entries: ModAction) -> str:
    ids = [f"#{entry.case_id}" for entry in entries if entry.case_id]
    return f"\n-# Case {', '.join(ids)}" if ids else ""


def _http_error(exc: discord.HTTPException) -> str:
    if isinstance(exc, discord.Forbidden):
        return "Bot lacks permission to do that. Check the bot's role position and permissions."
    return f"Discord rejected the request: {exc.text}"


@dataclass(slots=True)
class ModAction:
    """A single moderation action.

    This is both what gets stored in the ``mod_actions`` collection and the payload of the
    ``mod_action`` event, so any cog can ``@commands.Cog.listener() async def on_mod_action(self, entry)``.
    """

    guild_id: int
    action: ModActionType
    moderator_id: int | None  # None = unknown / system
    target_ids: list[int]
    reason: str | None
    created_at: datetime.datetime
    case_id: int | None = None  # None if persisting the case failed
    expires_at: datetime.datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_document(cls, doc: ModAction) -> ModAction:
        return cls(
            guild_id=doc["guild_id"],
            action=doc["action"],  # pyright: ignore[reportArgumentType]
            moderator_id=doc.get("moderator_id"),
            target_ids=list(doc.get("target_ids", [])),
            reason=doc.get("reason"),
            created_at=doc["created_at"],
            case_id=doc.get("case_id"),
            expires_at=doc.get("expires_at"),
            metadata=dict(doc.get("metadata", {})),
        )


@dataclass(slots=True)
class WarnResult:
    entry: ModAction
    active_count: int
    dm_sent: bool


class Snowflake:
    @classmethod
    async def convert(cls, ctx: commands.Context[Bot], argument: str) -> int:
        try:
            return int(argument)
        except ValueError:
            param = ctx.current_parameter
            if param:
                error_message = f"{param.name} argument expected a Discord ID not {argument!r}"
                raise commands.BadArgument(error_message) from None

            error_message = f"expected a Discord ID not {argument!r}"
            raise commands.BadArgument(error_message) from None


class PurgeFlags(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    user: discord.User | None = commands.flag(description="Remove messages from this user", default=None)
    contains: str | None = commands.flag(
        description="Remove messages that contains this string (case sensitive)",
        default=None,
    )
    prefix: str | None = commands.flag(
        description="Remove messages that start with this string (case sensitive)",
        default=None,
    )
    suffix: str | None = commands.flag(
        description="Remove messages that end with this string (case sensitive)",
        default=None,
    )
    after: Annotated[int | None, Snowflake] = commands.flag(description="Search for messages that come after this message ID", default=None)
    before: Annotated[int | None, Snowflake] = commands.flag(description="Search for messages that come before this message ID", default=None)
    bot: bool = commands.flag(description="Remove messages from bots (not webhooks!)", default=False)
    webhooks: bool = commands.flag(description="Remove messages from webhooks", default=False)
    embeds: bool = commands.flag(description="Remove messages that have embeds", default=False)
    files: bool = commands.flag(description="Remove messages that have attachments", default=False)
    emoji: bool = commands.flag(description="Remove messages that have custom emoji", default=False)
    reactions: bool = commands.flag(description="Remove messages that have reactions", default=False)
    require: Literal["any", "all"] = commands.flag(
        description='Whether any or all of the flags should be met before deleting messages. Defaults to "all"',
        default="all",
    )


def _is_owner(ctx: commands.Context[Bot], user: discord.abc.User) -> bool:
    """Guild owner or bot owner."""
    if TYPE_CHECKING:
        assert ctx.guild is not None

    return ctx.guild.owner_id == user.id or user.id in (ctx.bot.owner_ids or []) or user.id == ctx.bot.owner_id


def can_execute_action(ctx: commands.Context[Bot], user: discord.Member, target: discord.Member) -> bool:
    """Return whether ``user`` has sufficient authority to act on ``target``.

    A user may act on another member when they are either the guild owner, the bot owner,
    or higher than the target in Discord's role hierarchy. Discord's own permission and
    role-hierarchy checks still apply when the bot performs the action.
    """
    return _is_owner(ctx, user) or user.top_role > target.top_role


def audit_reason(ctx: commands.Context[Bot], reason: str | None) -> str:
    """Build the audit-log reason (always attributed to the invoking moderator)."""
    prefix = f"{ctx.author} (ID: {ctx.author.id})"
    return f"{prefix}: {reason}" if reason else prefix


class ActionReason(commands.Converter):
    """Validate a reason so that ``audit_reason`` fits in Discord's 512 character limit.

    The raw reason is returned (it is what gets stored in the mod log and shown to users);
    the moderator prefix is only added for the audit log via :func:`audit_reason`.
    """

    async def convert(self, ctx: commands.Context[Bot], argument: str) -> str:
        full = audit_reason(ctx, argument)

        if len(full) > REASON_LIMIT:
            reason_max = REASON_LIMIT - (len(full) - len(argument))
            error_message = f"Reason is too long ({len(argument)}/{reason_max})"
            raise commands.BadArgument(error_message)

        return argument


class MemberID(commands.Converter):
    """Resolve a command argument to a guild member, or to an ID-only object.

    Normal Discord member conversion is attempted first. If that fails the argument is
    treated as a raw ID. A user that cannot be found as a member is represented by a
    :class:`discord.Object`, which is enough for hackbans.
    """

    async def convert(self, ctx: commands.Context[Bot], argument: str) -> discord.Member | discord.Object:
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        try:
            member = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                raise commands.MemberNotFound(argument) from None

            member = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
            if member is None:
                return discord.Object(id=member_id)

        if not can_execute_action(ctx, ctx.author, member):
            error_message = f"{ctx.author} does not have sufficient authority to act on {member}."
            raise commands.BadArgument(error_message)

        return member


class BannedMember(commands.Converter):
    """Resolve a command argument to an existing guild ban."""

    async def convert(self, ctx: commands.Context[Bot], argument: str) -> discord.BanEntry:
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if argument.isdigit():
            member_id = int(argument, base=10)

            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                error_message = f"User ID {member_id} has not been banned before."
                raise commands.BadArgument(error_message) from None

        entity = await discord.utils.find(lambda u: str(u.user) == argument, ctx.guild.bans(limit=None))

        if entity is None:
            error_message = f"{argument} has not been banned before."
            raise commands.BadArgument(error_message)

        return entity


class MuteMetadata(TypedDict):
    guild_id: int
    member_id: int
    moderator_id: int
    reason: str | None


class Mod(commands.Cog, name="Moderation"):
    """Commands for moderators and administrators."""

    help_emoji = "\N{SHIELD}\N{VARIATION SELECTOR-16}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._mutes_synced = False
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def log_action(
        self,
        *,
        guild: discord.Guild,
        action: ModActionType,
        moderator: discord.abc.Snowflake | None,
        targets: list[discord.abc.Snowflake] | tuple[discord.abc.Snowflake, ...] = (),
        reason: str | None = None,
        expires_at: datetime.datetime | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ModAction:
        """Record a moderation action and dispatch ``mod_action``.

        1. The action is stored in the capped per-guild history (this assigns the case number).
        2. ``bot.dispatch("mod_action", entry)`` is fired. This cog listens to it to post in the
           mod-log channel; other cogs (automod, dashboards, ...) can listen to it as well.

        Persisting never raises: if the database is down the action still happened, so the
        command must still be able to reply. The entry then simply has no ``case_id``.
        """
        entry = ModAction(
            guild_id=guild.id,
            action=action,
            moderator_id=moderator.id if moderator else None,
            target_ids=[target.id for target in targets],
            reason=reason,
            created_at=discord.utils.utcnow(),
            expires_at=expires_at,
            metadata=dict(metadata or {}),
        )

        try:
            document = await self.bot.database.add_mod_action(
                guild_id=entry.guild_id,
                action=entry.action,
                moderator_id=entry.moderator_id,
                target_ids=entry.target_ids,
                reason=entry.reason,
                created_at=entry.created_at,
                expires_at=entry.expires_at,
                metadata=entry.metadata,
            )
        except Exception:
            _log.exception("Failed to persist mod action %s in guild %s", action, guild.id)
        else:
            entry.case_id = document["case_id"]

        self.bot.dispatch("mod_action", entry)
        return entry

    @commands.Cog.listener()
    async def on_mod_action(self, entry: ModAction) -> None:
        """Post a mod action in the guild's moderation log channel."""
        guild = self.bot.get_guild(entry.guild_id)
        if guild is None:
            return

        channel_id = await self.bot.database.get_moderator_logs_channel_id(guild_id=guild.id)
        if channel_id is None:
            _log.debug("Moderation log channel not set for guild: %s", guild.id)
            return

        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            _log.warning("Moderation log channel not found or is not a text channel for guild: %s", guild.id)
            return

        view = await self.build_case_view(guild, entry)
        try:
            await channel.send(view=view, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            _log.warning("Could not send mod log message in guild %s", guild.id, exc_info=True)

    async def _resolve_user(self, guild: discord.Guild, user_id: int) -> discord.Member | discord.User | None:
        user = guild.get_member(user_id) or self.bot.get_user(user_id)
        if user is None:
            with contextlib.suppress(discord.HTTPException):
                user = await self.bot.fetch_user(user_id)
        return user

    @staticmethod
    def _format_user(user_id: int, user: discord.Member | discord.User | None) -> str:
        if user is None:
            return f"<@{user_id}>\nID: `{user_id}`"
        return f"{user.mention} \N{BULLET} `{user}`\nID: `{user.id}`"

    async def build_case_view(self, guild: discord.Guild, entry: ModAction) -> discord.ui.LayoutView:
        """Render a case as a components-v2 layout (used by the mod log and ``case``)."""
        emoji, title, colour = _ACTION_META.get(
            entry.action,
            ("\N{SHIELD}", entry.action.replace("_", " ").title(), discord.Colour.default()),
        )

        shown_ids = entry.target_ids[:MAX_DISPLAY_TARGETS]
        moderator, *targets = await asyncio.gather(
            self._resolve_user(guild, entry.moderator_id) if entry.moderator_id else asyncio.sleep(0),
            *(self._resolve_user(guild, target_id) for target_id in shown_ids),
        )
        moderator = moderator if isinstance(moderator, (discord.Member, discord.User)) else None

        heading = f"### {emoji} {title}" + (f" \N{BULLET} Case #{entry.case_id}" if entry.case_id else "")
        if moderator is not None:
            moderator_text = self._format_user(moderator.id, moderator)
        elif entry.moderator_id:
            moderator_text = self._format_user(entry.moderator_id, None)
        else:
            moderator_text = "*AutoMod / System*"

        container = discord.ui.Container(accent_colour=colour)

        header = discord.ui.TextDisplay(f"{heading}\n**Moderator**:\n{moderator_text}")
        if moderator is not None:
            container.add_item(discord.ui.Section(header, accessory=discord.ui.Thumbnail(media=moderator.display_avatar.url)))
        else:
            container.add_item(header)

        if entry.target_ids:
            container.add_item(discord.ui.Separator())
            target_lines = [self._format_user(target_id, user) for target_id, user in zip(shown_ids, targets, strict=True)]
            hidden = len(entry.target_ids) - len(shown_ids)
            if hidden > 0:
                target_lines.append(f"...and {hidden} more.")

            if len(entry.target_ids) == 1 and targets[0] is not None:
                container.add_item(
                    discord.ui.Section(
                        discord.ui.TextDisplay(f"**Target**:\n{target_lines[0]}"),
                        accessory=discord.ui.Thumbnail(media=targets[0].display_avatar.url),
                    )
                )
            else:
                label = "Targets" if len(entry.target_ids) > 1 else "Target"
                container.add_item(discord.ui.TextDisplay(f"**{label}**:\n" + "\n".join(target_lines)))

        if entry.expires_at is not None:
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay(f"**Expiration**\n{discord.utils.format_dt(entry.expires_at, 'R')}"))

        if entry.metadata:
            container.add_item(discord.ui.Separator())
            details = "\n".join(f"**{key.replace('_', ' ').capitalize()}**: {value}" for key, value in entry.metadata.items())
            container.add_item(discord.ui.TextDisplay(details))

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(f"**Reason**\n{entry.reason or '*No reason provided.*'}"))

        container.add_item(discord.ui.Separator())
        container.add_item(
            discord.ui.TextDisplay(f"-# Happened {discord.utils.format_dt(entry.created_at, 'R')} - {discord.utils.format_dt(entry.created_at, 'F')}")
        )

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        return view

    @staticmethod
    def _case_line(entry: ModAction) -> str:
        emoji, title, _ = _ACTION_META.get(entry.action, ("\N{SHIELD}", entry.action.title(), discord.Colour.default()))
        moderator = f"<@{entry.moderator_id}>" if entry.moderator_id else "System"
        targets = ", ".join(f"<@{target_id}>" for target_id in entry.target_ids[:3])
        if len(entry.target_ids) > 3:
            targets += f" +{len(entry.target_ids) - 3}"
        reason = _truncate(entry.reason or "No reason provided", 60)
        details = " \N{BULLET} ".join(part for part in (targets, f"by {moderator}", reason) if part)
        return f"`#{entry.case_id}` {emoji} **{title}** {discord.utils.format_dt(entry.created_at, 'R')}\n-# {details}"

    @staticmethod
    async def _paginate_lines(
        ctx: commands.Context[Bot],
        lines: list[str],
        *,
        title: str,
        per_page: int,
        colour: discord.Colour | None = None,
    ) -> discord.Message:
        embeds = [
            discord.Embed(title=title, description="\n".join(chunk), colour=colour or discord.Colour.blurple())
            for chunk in discord.utils.as_chunks(lines, per_page)
        ]
        return await PaginationView(author=ctx.author, items=embeds).start(ctx)

    @commands.command(name="case")
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def case(
        self,
        ctx: commands.Context[Bot],
        case_id: commands.Range[int, 1] = commands.parameter(description="The case number to look up."),  # noqa: B008
    ) -> discord.Message:
        """Show a single moderation case.

        Only the most recent cases are kept (see the history limit of the bot), older ones are pruned.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        document = await ctx.bot.database.get_mod_action(guild_id=ctx.guild.id, case_id=case_id)
        if document is None:
            return await ctx.reply(f"Case #{case_id} was not found. It may have been pruned from the history.")

        view = await self.build_case_view(ctx.guild, ModAction.from_document(document))
        return await ctx.reply(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name="cases", aliases=["modlogs"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def cases(
        self,
        ctx: commands.Context[Bot],
        user: discord.User | None = commands.parameter(description="Only show cases targeting this user.", default=None),  # noqa: B008
    ) -> discord.Message:
        """Browse the recent moderation history of the server, optionally for one user."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        documents = await ctx.bot.database.get_mod_actions(
            guild_id=ctx.guild.id,
            target_id=user.id if user else None,
            limit=MAX_CASES_SHOWN,
        )
        if not documents:
            return await ctx.reply("No moderation cases found.")

        lines = [self._case_line(ModAction.from_document(document)) for document in documents]
        title = f"Moderation cases for {user}" if user else "Recent moderation cases"
        return await self._paginate_lines(ctx, lines, title=title, per_page=CASES_PER_PAGE)

    def _target_problem(
        self,
        ctx: commands.Context[Bot],
        target: discord.Member | discord.Object,
        verb: str,
        *,
        check_bot_hierarchy: bool = True,
    ) -> str | None:
        """Return a user-facing reason why ``target`` cannot be acted on, or ``None``."""
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        guild = ctx.guild
        if target.id == guild.me.id:
            return f"Cannot {verb} the bot itself."
        if target.id == ctx.author.id:
            return f"You cannot {verb} yourself."
        if target.id == guild.owner_id:
            return f"Cannot {verb} the server owner."

        if isinstance(target, discord.Member):
            if check_bot_hierarchy and target.top_role >= guild.me.top_role:
                return f"Cannot {verb} {target}. The bot's role is not high enough."
            if not can_execute_action(ctx, ctx.author, target):
                return f"You cannot {verb} {target}. Their top role is equal to or higher than yours."

        return None

    async def _dm_user(
        self,
        user: discord.Member | discord.User | discord.Object,
        guild: discord.Guild,
        title: str,
        reason: str | None,
        *,
        note: str | None = None,
    ) -> bool:
        """Best-effort DM. Returns whether it was delivered."""
        if not isinstance(user, (discord.Member, discord.User)):
            return False

        embed = discord.Embed(title=title, description=note, colour=discord.Colour.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Reason", value=reason or "No reason provided.", inline=False)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url if guild.icon else None)

        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            return False
        return True

    @commands.command(name="kick")
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    async def kick_member(
        self,
        ctx: commands.Context[Bot],
        member: Annotated[discord.Member | discord.Object, MemberID] = commands.parameter(description="The member to kick from the server."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for kicking the member(s).", default=None),
    ) -> discord.Message:
        """Kick member from the server.

        Kicking a member removes them from the server, but does not prevent them from rejoining.
        This is useful for temporarily removing a member or for enforcing server rules without permanently banning them.

        This command will log the action in the moderation log channel if it is configured for the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if not isinstance(member, discord.Member):
            return await ctx.reply("That user is not in this server.")

        problem = self._target_problem(ctx, member, "kick")
        if problem is not None:
            return await ctx.reply(problem)

        await self._dm_user(member, ctx.guild, f"You have been kicked from {ctx.guild.name}", reason)

        try:
            await ctx.guild.kick(member, reason=audit_reason(ctx, reason))
        except discord.HTTPException as exc:
            return await ctx.reply(_http_error(exc))

        entry = await self.log_action(guild=ctx.guild, action="kick", moderator=ctx.author, targets=[member], reason=reason)
        return await ctx.reply(f"**{member}** (ID: {member.id}) has been kicked from the server.{_case_note(entry)}")

    @commands.command(name="ban", aliases=["hackban"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def ban_member(
        self,
        ctx: commands.Context[Bot],
        member: Annotated[discord.Member | discord.Object, MemberID] = commands.parameter(description="The member(s) to ban from the server."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for banning the member(s).", default=None),
    ) -> discord.Message:
        """Ban member from the server.

        A member that is not currently in the server can still be banned by providing their Discord ID.
        This is known as a "hackban" and is useful for banning users who have already left the server or who have been banned from the server previously.

        This command will log the action in the moderation log channel if it is configured for the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        problem = self._target_problem(ctx, member, "ban")
        if problem is not None:
            return await ctx.reply(problem)

        await self._dm_user(member, ctx.guild, f"You have been banned from {ctx.guild.name}", reason)

        try:
            await ctx.guild.ban(member, reason=audit_reason(ctx, reason))
        except discord.HTTPException as exc:
            return await ctx.reply(_http_error(exc))

        entry = await self.log_action(guild=ctx.guild, action="ban", moderator=ctx.author, targets=[member], reason=reason)

        if isinstance(member, discord.Object):
            return await ctx.reply(f"ID: {member.id} has been banned from the server.{_case_note(entry)}")
        return await ctx.reply(f"**{member}** (ID: {member.id}) has been banned from the server.{_case_note(entry)}")

    @commands.command(name="massban", aliases=["mass-ban", "multiban", "multi-ban"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True, manage_guild=True)  # bulk ban requires Manage Server too
    async def mass_ban_members(
        self,
        ctx: commands.Context[Bot],
        members: Annotated[list[discord.Member | discord.Object], commands.Greedy[MemberID]] = commands.parameter(  # noqa: B008
            description="The members to ban from the server.", default=None
        ),
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for banning the member(s).", default=None),
    ) -> discord.Message:
        """Ban one or more members from the server.

        Members that can be banned are processed even if another target fails.
        The response reports successful and failed targets separately.

        The bot bans all members in a single bulk operation (up to 200). Members that cannot be banned
        because of role hierarchy, being the server owner, yourself or the bot itself are skipped and reported.

        This command will log the action in the moderation log channel if it is configured for the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if not members:
            return await ctx.reply("Provide at least one member or ID to ban.")

        unique = list({member.id: member for member in members}.values())
        if len(unique) > MAX_BULK_BAN:
            return await ctx.reply(f"You can ban at most {MAX_BULK_BAN} members at once.")

        bannable: list[discord.Member | discord.Object] = []
        skipped: list[discord.Member | discord.Object] = []
        for target in unique:
            (skipped if self._target_problem(ctx, target, "ban") else bannable).append(target)

        if not bannable:
            return await ctx.reply(
                f"No members could be banned. {len(skipped)} member(s) could not be banned.{self._format_skipped_members(skipped)}"
            )

        try:
            result = await ctx.guild.bulk_ban(bannable, reason=audit_reason(ctx, reason))
        except discord.HTTPException as exc:
            return await ctx.reply(_http_error(exc))

        success_count = len(result.banned)
        failure_count = len(result.failed)

        if not success_count and not failure_count:
            return await ctx.reply("No members were banned. Please check the provided member(s) and try again.")

        entries: list[ModAction] = []
        if success_count:
            metadata = {"bulk": f"{success_count} banned"}
            if skipped or failure_count:
                metadata["not_banned"] = str(len(skipped) + failure_count)
            entries.append(
                await self.log_action(
                    guild=ctx.guild,
                    action="ban",
                    moderator=ctx.author,
                    targets=list(result.banned),
                    reason=reason,
                    metadata=metadata,
                )
            )

        if not success_count:
            message = f"Failed to ban any members. {failure_count} member(s) could not be banned."
        else:
            message = f"Successfully banned {success_count} member(s) from the server."
            if failure_count:
                message += f" Failed to ban {failure_count} member(s)."

        return await ctx.reply(message + self._format_skipped_members(skipped) + _case_note(*entries))

    @staticmethod
    def _format_skipped_members(members: list[discord.Member | discord.Object]) -> str:
        if not members:
            return ""

        prefix = "\nThe following member(s) could not be banned (role hierarchy, owner, yourself or the bot itself):\n- "
        details = "\n- ".join(f"{member} (ID: {member.id})" if isinstance(member, discord.Member) else f"ID: {member.id}" for member in members)
        message = prefix + details

        if len(message) > DISCORD_MESSAGE_LIMIT:
            return f"\n-# Some members [{len(members)}] could not be banned (role hierarchy, owner, yourself or the bot itself)."

        return message

    @commands.command(name="softban", aliases=["soft-ban"])
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def soft_ban_member(
        self,
        ctx: commands.Context[Bot],
        member: Annotated[discord.Member | discord.Object, MemberID] = commands.parameter(description="The member to softban from the server."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for softbanning the member(s).", default=None),
    ) -> discord.Message:
        """Softban a member from the server.

        A softban is a ban followed by an immediate unban.
        This removes the member from the server and deletes their messages from the last 7 days, but allows them to rejoin if they wish.

        This command will log the action in the moderation log channel if it is configured for the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        problem = self._target_problem(ctx, member, "softban")
        if problem is not None:
            return await ctx.reply(problem)

        await self._dm_user(member, ctx.guild, f"You have been softbanned from {ctx.guild.name}", reason)

        try:
            await ctx.guild.ban(member, reason=audit_reason(ctx, reason), delete_message_seconds=7 * 24 * 60 * 60)
            await ctx.guild.unban(member, reason=f"Softban completed by {ctx.author} (ID: {ctx.author.id})")
        except discord.HTTPException as exc:
            return await ctx.reply(_http_error(exc))

        entry = await self.log_action(guild=ctx.guild, action="softban", moderator=ctx.author, targets=[member], reason=reason)
        label = f"**{member}** (ID: {member.id})" if isinstance(member, discord.Member) else f"ID: {member.id}"
        return await ctx.reply(f"{label} has been softbanned from the server.{_case_note(entry)}")

    @commands.command(name="unban", aliases=["pardon"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def unban_member(
        self,
        ctx: commands.Context[Bot],
        member: Annotated[discord.BanEntry, BannedMember] = commands.parameter(description="The member to unban from the server."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for unbanning the member(s).", default=None),
    ) -> discord.Message:
        """Unban a member from the server.

        Unbanning a member removes the ban restriction on their account, allowing them to rejoin the server if they wish.

        This command will log the action in the moderation log channel if it is configured for the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        try:
            await ctx.guild.unban(member.user, reason=audit_reason(ctx, reason))
        except discord.HTTPException as exc:
            return await ctx.reply(_http_error(exc))

        entry = await self.log_action(guild=ctx.guild, action="unban", moderator=ctx.author, targets=[member.user], reason=reason)
        return await ctx.reply(f"**{member.user}** (ID: {member.user.id}) has been unbanned from the server.{_case_note(entry)}")

    async def _timeout_or_mute(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member,
        duration: FutureTime | None,
        reason: str | None,
    ) -> discord.Message:
        if TYPE_CHECKING:
            assert ctx.guild is not None

        problem = self._target_problem(ctx, member, "timeout")
        if problem is not None:
            return await ctx.reply(problem)

        # Discord's native timeout is capped at 28 days; anything longer (or indefinite) uses the mute role.
        use_role = duration is None or duration.dt - discord.utils.utcnow() > MAX_TIMEOUT
        action: ModActionType = "mute" if use_role else "timeout"

        await self._dm_user(member, ctx.guild, f"You have been {'muted' if use_role else 'timed out'} in {ctx.guild.name}", reason)

        try:
            if use_role:
                response = await self._mute_with_role(ctx, member=member, duration=duration, reason=reason)
            else:
                if TYPE_CHECKING:
                    assert duration is not None
                await member.timeout(duration.dt, reason=audit_reason(ctx, reason))
                relative_duration = discord.utils.format_dt(duration.dt, style="R")
                response = f"**{member}** (ID: {member.id}) has been timed out. Expires: {relative_duration}."
        except discord.HTTPException as exc:
            return await ctx.reply(_http_error(exc))

        entry = await self.log_action(
            guild=ctx.guild,
            action=action,
            moderator=ctx.author,
            targets=[member],
            reason=reason,
            expires_at=duration.dt if duration else None,
        )
        return await ctx.reply(response + _case_note(entry))

    async def _mute_with_role(
        self,
        ctx: commands.Context[Bot],
        *,
        member: discord.Member,
        duration: FutureTime | None,
        reason: str | None,
    ) -> str:
        """Mute a member using the configured mute role. Returns the reply text."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        mute_role_id = await ctx.bot.database.get_guild_mute_role(guild_id=ctx.guild.id)
        mute_role = ctx.guild.get_role(mute_role_id) if mute_role_id else None
        if mute_role is None:
            message = "No mute role has been set for this server. Use `mute create` or `mute role <role>` first."
            raise commands.CommandError(message)

        # A re-mute replaces any pending unmute timer.
        await ctx.bot.event_scheduler.delete(event_name="mute", metadata_filter={"guild_id": ctx.guild.id, "member_id": member.id})

        if duration is not None:
            await ctx.bot.event_scheduler.create_timer(
                event_name="mute",
                expires_at=duration.dt,
                metadata=MuteMetadata(
                    guild_id=ctx.guild.id,
                    member_id=member.id,
                    moderator_id=ctx.author.id,
                    reason=reason,
                ),
            )

        await member.add_roles(mute_role, reason=audit_reason(ctx, reason))
        await ctx.bot.database.add_muted_member(guild_id=ctx.guild.id, member_id=member.id)

        if duration is not None:
            return f"**{member}** (ID: {member.id}) has been muted until {discord.utils.format_dt(duration.dt, style='R')}."
        return f"**{member}** (ID: {member.id}) has been muted indefinitely."

    @commands.command(name="timeout", aliases=["stfu"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True, manage_roles=True)
    async def timeout_member(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member = commands.parameter(description="The member to timeout."),  # noqa: B008
        duration: FutureTime | None = commands.parameter(description="The duration of the timeout.", default=None),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for timing out the member(s).", default=None),
    ) -> discord.Message:
        """Timeout a member from the server.

        A timeout is a temporary restriction on a member's ability to send messages or interact with the server.
        The duration of the timeout is specified in seconds, minutes, hours, or days.

        If the duration is not specified or exceeds 28 days, the bot will mute the member using the configured mute role instead.
        This is because Discord's built-in timeout feature has a maximum duration of 28 days.

        This command will log the action in the moderation log channel if it is configured for the server.
        """
        return await self._timeout_or_mute(ctx, member, duration, reason)

    @commands.command(name="unmute", aliases=["untimeout"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True, manage_roles=True)
    async def unmute_member(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member = commands.parameter(description="The member to unmute."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for unmuting the member(s).", default=None),
    ) -> discord.Message:
        """Unmute a member from the server.

        Removes a timeout and/or the mute role from the member, whichever applies.

        This command will log the action in the moderation log channel if it is configured for the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        audit = audit_reason(ctx, reason)
        actions: list[ModActionType] = []

        try:
            if member.is_timed_out():
                await member.timeout(None, reason=audit)
                actions.append("untimeout")

            mute_role_id = await ctx.bot.database.get_guild_mute_role(guild_id=ctx.guild.id)
            mute_role = ctx.guild.get_role(mute_role_id) if mute_role_id else None
            muted_ids = await ctx.bot.database.get_muted_members(guild_id=ctx.guild.id)
            has_role = mute_role is not None and mute_role in member.roles

            if member.id in muted_ids or has_role:
                # DB first: otherwise the sticky-mute listener would put the role right back.
                await ctx.bot.database.remove_muted_member(guild_id=ctx.guild.id, member_id=member.id)
                await ctx.bot.event_scheduler.delete(
                    event_name="mute",
                    metadata_filter={"guild_id": ctx.guild.id, "member_id": member.id},
                )
                if has_role and mute_role is not None:
                    await member.remove_roles(mute_role, reason=audit)
                actions.append("unmute")
        except discord.HTTPException as exc:
            return await ctx.reply(_http_error(exc))

        if not actions:
            return await ctx.reply(f"**{member}** (ID: {member.id}) is not currently muted in this server.")

        entries = [await self.log_action(guild=ctx.guild, action=action, moderator=ctx.author, targets=[member], reason=reason) for action in actions]
        return await ctx.reply(f"**{member}** (ID: {member.id}) has been unmuted from the server.{_case_note(*entries)}")

    @commands.group(name="mute", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True, manage_roles=True)
    async def mute(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member = commands.parameter(description="The member to timeout."),  # noqa: B008
        duration: FutureTime | None = commands.parameter(description="The duration of the timeout.", default=None),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for timing out the member(s).", default=None),
    ) -> discord.Message:
        """Mute a member, or manage the mute role of the server.

        Without a subcommand this behaves like `timeout`.
        Subcommands: `role`, `sync`, `create`, `remove`, `list`.
        """
        return await self._timeout_or_mute(ctx, member, duration, reason)

    @mute.command(name="role")
    @commands.has_permissions(moderate_members=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def mute_role(
        self,
        ctx: commands.Context[Bot],
        *,
        role: discord.Role = commands.parameter(description="The role to assign to muted members."),  # noqa: B008
    ) -> discord.Message:
        """Set the mute role for the server.

        The mute role is assigned to members when they are muted, restricting their ability to send messages or interact with the server.

        This will overwrite any existing mute role for the server.
        Make sure the mute role has the correct permissions set. Use `mute sync` to automatically adjust the permissions of the mute role.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if role.is_default() or role.managed or role >= ctx.guild.me.top_role:
            return await ctx.reply(
                "Bot cannot use that role as a mute role (it is @everyone, managed by an integration, or higher than the bot's top role)."
            )

        await ctx.bot.database.edit_mute_config(guild_id=ctx.guild.id, mute_role_id=role.id)
        suggestion = "-# Use `mute sync` to automatically adjust the permissions of the mute role in every channel."
        return await ctx.reply(f"The mute role for this server has been set to **{role}** (ID: {role.id}).\n{suggestion}")

    async def _sync_mute_permissions(
        self,
        ctx: commands.Context[Bot],
        role: discord.Role,
        message: discord.Message,
        prefix: str,
    ) -> int:
        """Deny the mute role everywhere, editing ``message`` with progress. Returns the number of failed channels."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        channels = ctx.guild.channels
        total = len(channels)
        failed = 0

        for index, channel in enumerate(channels, start=1):
            overwrite = channel.overwrites_for(role)
            overwrite.update(
                send_messages=False,
                speak=False,
                add_reactions=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False,
            )
            try:
                await channel.set_permissions(role, overwrite=overwrite, reason=f"Mute role sync by {ctx.author} (ID: {ctx.author.id})")
            except discord.HTTPException:
                failed += 1

            if index % 10 == 0 or index == total:
                await message.edit(content=f"{prefix} [{index}/{total}]")

        return failed

    @mute.command(name="sync", aliases=["synchronize", "synchronise"])
    @commands.has_permissions(moderate_members=True, manage_roles=True, manage_channels=True)
    @commands.bot_has_guild_permissions(manage_roles=True, manage_channels=True)
    async def mute_sync(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Synchronize the permissions of the mute role with the server's channels.

        Sets the mute role to deny sending messages, adding reactions, creating threads and speaking in all channels.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        mute_role_id = await ctx.bot.database.get_guild_mute_role(guild_id=ctx.guild.id)
        if mute_role_id is None:
            return await ctx.reply("No mute role has been set for this server. Use `mute role <role>` to set a mute role first.")

        mute_role = ctx.guild.get_role(mute_role_id)
        if mute_role is None:
            return await ctx.reply("The configured mute role does not exist in this server. Please set a valid mute role using `mute role <role>`.")

        prefix = f"Synchronizing the permissions of the mute role **{mute_role}** (ID: {mute_role.id}) with all channels. This may take a moment..."
        message = await ctx.reply(f"{prefix} [0/{len(ctx.guild.channels)}]")
        failed = await self._sync_mute_permissions(ctx, mute_role, message, prefix)

        result = f"The permissions of the mute role **{mute_role}** (ID: {mute_role.id}) have been synchronized with all channels."
        if failed:
            result += f"\n-# {failed} channel(s) could not be updated (missing access)."
        await message.edit(content=result)
        return message

    @mute.command(name="create", aliases=["new", "make", "setup"])
    @commands.has_permissions(moderate_members=True, manage_roles=True, manage_channels=True)
    @commands.bot_has_guild_permissions(manage_roles=True, manage_channels=True)
    async def mute_create(
        self,
        ctx: commands.Context[Bot],
        *,
        role_name: str = commands.parameter(description="The name of the mute role to create.", default="Muted"),
    ) -> discord.Message:
        """Create a new mute role for the server.

        Creates a role with the specified name, sets it as the mute role and syncs its channel permissions.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        existing_role_id = await ctx.bot.database.get_guild_mute_role(guild_id=ctx.guild.id)
        existing_role = ctx.guild.get_role(existing_role_id) if existing_role_id else None

        if existing_role is not None:
            return await ctx.reply(
                f"A mute role already exists ({existing_role} - {existing_role_id}) for this server. "
                "Use `mute role <role>` to change the mute role or `mute sync` to synchronize its permissions."
            )

        mute_role = await ctx.guild.create_role(
            name=role_name,
            reason=f"Mute role created by {ctx.author} (ID: {ctx.author.id})",
        )
        await ctx.bot.database.edit_mute_config(guild_id=ctx.guild.id, mute_role_id=mute_role.id)

        prefix = f"A new mute role **{mute_role}** (ID: {mute_role.id}) has been created. Syncing its permissions with all channels. This may take a moment..."
        message = await ctx.reply(f"{prefix} [0/{len(ctx.guild.channels)}]")
        failed = await self._sync_mute_permissions(ctx, mute_role, message, prefix)

        result = f"A new mute role **{mute_role}** (ID: {mute_role.id}) has been created and synchronized with all channels."
        if failed:
            result += f"\n-# {failed} channel(s) could not be updated (missing access)."
        await message.edit(content=result)
        return message

    @mute.command(name="remove", aliases=["delete", "del", "rm", "unbind"])
    @commands.has_permissions(moderate_members=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def mute_remove(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Remove the mute role from the server.

        Deletes the mute role and forgets all currently muted members and pending unmute timers.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        mute_role_id = await ctx.bot.database.get_guild_mute_role(guild_id=ctx.guild.id)
        if mute_role_id is None:
            return await ctx.reply("No mute role has been set for this server.")

        mute_role = ctx.guild.get_role(mute_role_id)
        if mute_role is None:
            return await ctx.reply("The configured mute role does not exist in this server.")

        # DB first so the sticky-mute listener doesn't fight the role deletion.
        await ctx.bot.database.delete_mute_role(guild_id=ctx.guild.id)
        await ctx.bot.event_scheduler.delete(event_name="mute", metadata_filter={"guild_id": ctx.guild.id}, multiple=True)

        try:
            await mute_role.delete(reason=f"Mute role removed by {ctx.author} (ID: {ctx.author.id})")
        except discord.HTTPException as exc:
            return await ctx.reply(f"The mute role was unbound, but Bot could not delete it: {_http_error(exc)}")

        return await ctx.reply(f"The mute role **{mute_role}** (ID: {mute_role.id}) has been removed from the server.")

    @mute.command(name="list", aliases=["show", "view", "ls"])
    @commands.has_permissions(moderate_members=True)
    async def mute_list(self, ctx: commands.Context[Bot]) -> discord.Message:
        """List all currently muted members in the server.

        Includes members muted through the mute role and through Discord's built-in timeout.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        muted_ids = set(await ctx.bot.database.get_muted_members(guild_id=ctx.guild.id))

        lines: list[str] = []
        for member_id in muted_ids:
            member = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
            lines.append(f"{member} (ID: {member.id})" if member is not None else f"Unknown Member (ID: {member_id})")

        lines.extend(
            f"{member} (ID: {member.id}) - Timed Out" for member in ctx.guild.members if member.is_timed_out() and member.id not in muted_ids
        )

        if not lines:
            return await ctx.reply("There are no currently muted members in this server.")

        lines.sort(key=str.lower)
        return await self._paginate_lines(ctx, [f"- {line}" for line in lines], title="Currently muted members", per_page=15)

    @commands.Cog.listener()
    async def on_mute_timer_complete(self, metadata: MuteMetadata) -> None:
        """Handle the completion of a mute timer."""
        guild = self.bot.get_guild(metadata["guild_id"])
        if guild is None:
            return

        # Always forget the mute first, even if the member left. Otherwise they'd be re-muted when rejoining.
        await self.bot.database.remove_muted_member(guild_id=guild.id, member_id=metadata["member_id"])

        member = await self.bot.get_or_fetch_member(guild, metadata["member_id"])
        if member is None:
            return

        mute_role_id = await self.bot.database.get_guild_mute_role(guild_id=guild.id)
        mute_role = guild.get_role(mute_role_id) if mute_role_id else None
        if mute_role is None:
            return

        with contextlib.suppress(discord.HTTPException):
            await member.remove_roles(mute_role, reason=f"Mute expired. Originally muted by moderator ID {metadata['moderator_id']}.")

        await self.log_action(
            guild=guild,
            action="unmute",
            moderator=guild.me,
            targets=[member],
            reason="Mute expired.",
            metadata={"originally_muted_by": f"<@{metadata['moderator_id']}>"},
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Handle a member rejoining the server while muted."""
        muted_members = await self.bot.database.get_muted_members(guild_id=member.guild.id)
        if member.id not in muted_members:
            return

        mute_role_id = await self.bot.database.get_guild_mute_role(guild_id=member.guild.id)
        mute_role = member.guild.get_role(mute_role_id) if mute_role_id else None
        if mute_role is None:
            return

        with contextlib.suppress(discord.HTTPException):
            await member.add_roles(mute_role, reason="Member rejoined while muted.")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Keep the muted-members database in sync with the mute role.

        * Role added manually -> remember the member as muted.
        * Role removed from a member that is still muted in the database -> put it back (sticky mute).
          Our own commands remove the database entry *before* removing the role, so they are not affected.
        """
        if before.roles == after.roles:
            return

        mute_role_id = await self.bot.database.get_guild_mute_role(guild_id=after.guild.id)
        if mute_role_id is None:
            return

        before_ids = {role.id for role in before.roles}
        after_ids = {role.id for role in after.roles}

        if mute_role_id in after_ids - before_ids:
            await self.bot.database.add_muted_member(guild_id=after.guild.id, member_id=after.id)

        elif mute_role_id in before_ids - after_ids:
            muted_members = await self.bot.database.get_muted_members(guild_id=after.guild.id)
            mute_role = after.guild.get_role(mute_role_id)
            if after.id in muted_members and mute_role is not None:
                with contextlib.suppress(discord.HTTPException):
                    await after.add_roles(mute_role, reason="Sticky mute role enforcement.")

    @commands.Cog.listener("on_ready")
    async def sync_mute_roles(self) -> None:
        """Sync mute roles for all guilds on bot startup (once, not on every reconnect)."""
        if self._mutes_synced:
            return
        self._mutes_synced = True

        async for (
            guild_id,
            muted_members_id,
        ) in self.bot.database.get_all_muted_members():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue

            if not guild.chunked:
                await guild.chunk()

            mute_role_id = await self.bot.database.get_guild_mute_role(guild_id=guild.id)
            mute_role = guild.get_role(mute_role_id) if mute_role_id else None
            if mute_role is None:
                continue

            for member_id in muted_members_id:
                member = await self.bot.get_or_fetch_member(guild, member_id)
                if member is None or mute_role in member.roles:
                    continue

                with contextlib.suppress(discord.HTTPException):
                    await member.add_roles(mute_role, reason="Syncing mute roles on bot startup.")

    async def issue_warning(
        self,
        guild: discord.Guild,
        member: discord.Member,
        *,
        moderator: discord.Member | discord.User | None,
        reason: str | None,
        expires_in: datetime.timedelta | None = WARN_EXPIRY,
    ) -> WarnResult:
        """Warn a member: store the strike, DM them and log it.

        Usable from other cogs (e.g. automod passes ``moderator=None``).
        """
        now = discord.utils.utcnow()
        expires_at = now + expires_in if expires_in is not None else None

        await self.bot.database.add_violation(
            guild_id=guild.id,
            violation_name=WARN_VIOLATION,
            user_id=member.id,
            issued_at=now,
            issued_by=moderator.id if moderator else None,
            expired_at=expires_at,
            metadata={"reason": reason} if reason else {},
        )

        active = await self.bot.database.get_violations(guild_id=guild.id, user_id=member.id, violation_name=WARN_VIOLATION, active_only=True)
        active_count = len(active)

        entry = await self.log_action(
            guild=guild,
            action="warn",
            moderator=moderator,
            targets=[member],
            reason=reason,
            expires_at=expires_at,
            metadata={"active_warnings": str(active_count)},
        )

        dm_sent = await self._dm_user(
            member,
            guild,
            f"You have been warned in {guild.name}",
            reason,
            note=f"You now have **{active_count}** active warning(s)."
            + (f" This warning expires {discord.utils.format_dt(expires_at, 'R')}." if expires_at else ""),
        )

        return WarnResult(entry=entry, active_count=active_count, dm_sent=dm_sent)

    @commands.command(name="warn", aliases=["strike"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def warn_member(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member = commands.parameter(description="The member to warn."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for the warning.", default=None),
    ) -> discord.Message:
        """Warn a member (adds a strike).

        Warnings expire after a while. When a member reaches certain amounts of *active* warnings the
        bot automatically punishes them (timeouts, then kick, then ban).
        The member is notified by DM when possible, and the warning is logged as a case.

        The bot needs the matching permissions for the automatic punishments to succeed.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        problem = self._target_problem(ctx, member, "warn", check_bot_hierarchy=False)
        if problem is not None:
            return await ctx.reply(problem)

        result = await self.issue_warning(ctx.guild, member, moderator=ctx.author, reason=reason)

        lines = [f"**{member}** (ID: {member.id}) has been warned. Active warnings: **{result.active_count}**."]
        if not result.dm_sent:
            lines.append("-# Could not DM the member.")
        return await ctx.reply("\n".join(lines) + _case_note(result.entry))

    @commands.command(name="warnings", aliases=["strikes", "infractions"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def warnings_list(
        self,
        ctx: commands.Context[Bot],
        user: discord.User | None = commands.parameter(description="The user to show warnings for (defaults to you).", default=None),  # noqa: B008
    ) -> discord.Message:
        """Show the warnings of a user, newest first, including expired ones.

        The number in front of each warning can be used with `unwarn`.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        target = user or ctx.author
        violations = await ctx.bot.database.get_violations(guild_id=ctx.guild.id, user_id=target.id, violation_name=WARN_VIOLATION)
        if not violations:
            return await ctx.reply(f"**{target}** has no warnings.")

        now = discord.utils.utcnow()
        active_count = 0
        lines: list[str] = []
        for index, violation in enumerate(violations, start=1):
            expires_at = violation.get("expires_at")
            issued_at = violation["issued_at"]
            active = expires_at is None or expires_at > now
            active_count += active

            status = "\N{LARGE GREEN CIRCLE} Active" if active else "\N{MEDIUM WHITE CIRCLE} Expired"
            if active and expires_at is not None:
                status += f" (expires {discord.utils.format_dt(expires_at, 'R')})"

            issuer = f"<@{violation['issued_by']}>" if violation.get("issued_by") else "AutoMod"
            warn_reason = _truncate(violation.get("metadata", {}).get("reason") or "No reason provided", 100)
            when = discord.utils.format_dt(issued_at, "R") if issued_at else "unknown"
            lines.append(f"`#{index}` {status}\n-# {when} \N{BULLET} by {issuer} \N{BULLET} {warn_reason}")

        title = f"Warnings for {target} ({active_count} active / {len(violations)} total)"
        return await self._paginate_lines(ctx, lines, title=title, per_page=CASES_PER_PAGE, colour=discord.Colour.yellow())

    @commands.command(name="unwarn", aliases=["delwarn", "removewarn"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def unwarn_member(
        self,
        ctx: commands.Context[Bot],
        user: discord.User = commands.parameter(description="The user to remove a warning from."),  # noqa: B008
        number: commands.Range[int, 1] = commands.parameter(description="The warning number shown by the warnings command."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for removing the warning.", default=None),
    ) -> discord.Message:
        """Remove one specific warning from a user.

        Use `warnings <user>` to see the number of each warning.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        violations = await ctx.bot.database.get_violations(guild_id=ctx.guild.id, user_id=user.id, violation_name=WARN_VIOLATION)
        if not 1 <= number <= len(violations):
            return await ctx.reply(f"**{user}** has no warning #{number}. Use `warnings {user.id}` to see the list.")

        violation = violations[number - 1]
        await ctx.bot.database.delete_violation(guild_id=ctx.guild.id, _id=violation["_id"])

        metadata = {}
        removed_reason = violation.get("metadata", {}).get("reason")
        if removed_reason is not None:
            metadata["removed_warning"] = _truncate(removed_reason, 200)

        entry = await self.log_action(guild=ctx.guild, action="unwarn", moderator=ctx.author, targets=[user], reason=reason, metadata=metadata)
        return await ctx.reply(f"Removed warning #{number} from **{user}** (ID: {user.id}).{_case_note(entry)}")

    @commands.command(name="clearwarns", aliases=["clearwarnings", "resetwarns"])
    @commands.guild_only()
    @commands.has_permissions(moderate_members=True)
    async def clear_warnings(
        self,
        ctx: commands.Context[Bot],
        user: discord.User = commands.parameter(description="The user to clear all warnings for."),  # noqa: B008
        *,
        reason: Annotated[str | None, ActionReason] = commands.parameter(description="The reason for clearing the warnings.", default=None),
    ) -> discord.Message:
        """Remove every warning (active and expired) from a user."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        previous = await ctx.bot.database.reset_violations(guild_id=ctx.guild.id, violation_name=WARN_VIOLATION, user_id=user.id)
        if not previous:
            return await ctx.reply(f"**{user}** has no warnings.")

        entry = await self.log_action(
            guild=ctx.guild,
            action="clearwarns",
            moderator=ctx.author,
            targets=[user],
            reason=reason,
            metadata={"cleared": str(previous)},
        )
        return await ctx.reply(f"Cleared **{previous}** warning(s) from **{user}** (ID: {user.id}).{_case_note(entry)}")

    async def _basic_cleanup_strategy(self, ctx: commands.Context[Bot], search: int):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
                await msg.delete(delay=0)
                count += 1
        return {"Bot": count}

    async def _complex_cleanup_strategy(self, ctx: commands.Context[Bot], search: int):
        assert ctx.guild is not None

        prefixes = await self.bot.get_prefix(ctx.message)

        def check(m: discord.Message):
            return m.author == ctx.me or m.content.startswith(tuple(prefixes))

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)  # pyright: ignore[reportAttributeAccessIssue]
        return Counter(m.author.display_name for m in deleted)

    async def _regular_user_cleanup_strategy(self, ctx: commands.Context[Bot], search: int):
        prefixes = await self.bot.get_prefix(ctx.message)

        def check(m: discord.Message):
            return (m.author == ctx.me or m.content.startswith(tuple(prefixes))) and not (m.mentions or m.role_mentions)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)  # pyright: ignore[reportAttributeAccessIssue]
        return Counter(m.author.display_name for m in deleted)

    @commands.command(hidden=True)
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def cleanup(
        self,
        ctx: commands.Context[Bot],
        search: commands.Range[int, 2, 1000] | None = commands.parameter(  # noqa: B008
            description="The number of messages to search through.", default=25
        ),
    ):
        """Cleans up the bot's messages from the channel.

        If a search number is specified, it searches that many messages to delete.
        If the bot has Manage Messages permissions then it will try to delete
        messages that look like they invoked the bot as well.

        After the cleanup is completed, the bot will send you a message with
        which people got their messages deleted and their count. This is useful
        to see which users are spammers.

        Members with Manage Messages can search up to 1000 messages.
        Members without can search up to 25 messages.
        """

        assert isinstance(ctx.me, discord.Member)
        assert isinstance(ctx.author, discord.Member)

        search = search or 25

        strategy = self._basic_cleanup_strategy
        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            strategy = self._complex_cleanup_strategy if is_mod else self._regular_user_cleanup_strategy

        search = min(max(2, search), 1000) if is_mod else min(max(2, search), 25)

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [f"{deleted} message{' was' if deleted == 1 else 's were'} removed."]
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"- **{author}**: {count}" for author, count in spammers)

        await ctx.send("\n".join(messages), delete_after=10)

    def _prepare_purge_predicates(self, flags: PurgeFlags) -> list[Callable[[discord.Message], Any]]:
        predicates: list[Callable[[discord.Message], Any]] = []
        if flags.bot:
            if flags.webhooks:
                predicates.append(lambda m: m.author.bot)
            else:
                predicates.append(lambda m: (m.webhook_id is None or m.interaction is not None) and m.author.bot)
        elif flags.webhooks:
            predicates.append(lambda m: m.webhook_id is not None)

        if flags.embeds:
            predicates.append(lambda m: len(m.embeds))

        if flags.files:
            predicates.append(lambda m: len(m.attachments))

        if flags.reactions:
            predicates.append(lambda m: len(m.reactions))

        if flags.emoji:
            custom_emoji = re.compile(r"<a?:(\w+):(\d+)>")
            predicates.append(lambda m: custom_emoji.search(m.content))

        if flags.user:
            predicates.append(lambda m: m.author == flags.user)

        if flags.contains:
            predicates.append(lambda m: flags.contains in m.content)  # pyright: ignore[reportOperatorIssue]

        if flags.prefix:
            predicates.append(lambda m: m.content.startswith(flags.prefix))  # pyright: ignore[reportArgumentType]

        if flags.suffix:
            predicates.append(lambda m: m.content.endswith(flags.suffix))  # pyright: ignore[reportArgumentType]

        return predicates

    @commands.command(aliases=["remove"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: commands.Context[Bot],
        limit: commands.Range[int, 1, 2000] | None = commands.parameter(  # noqa: B008
            description="The number of messages to search through.", default=100
        ),
        *,
        flags: PurgeFlags = commands.parameter(description="Filters that pick which messages to remove"),  # noqa: B008
    ):
        """Removes messages that meet a criteria.

        This command uses a syntax similar to Discord's search bar.
        The messages are only deleted if all options are met unless
        the `--require ` flag is passed to override the behaviour.
        Messages older than 14 days are never removed.

        The following flags are valid.

        `--user` Remove messages from the given user.
        `--contains` Remove messages that contain a substring.
        `--prefix` Remove messages that start with a string.
        `--suffix` Remove messages that end with a string.
        `--after` Search for messages that come after this message ID.
        `--before` Search for messages that come before this message ID.
        `--bot yes` Remove messages from bots (not webhooks!)
        `--webhooks yes` Remove messages from webhooks
        `--embeds yes` Remove messages that have embeds
        `--files yes` Remove messages that have attachments
        `--emoji yes` Remove messages that have custom emoji
        `--reactions yes` Remove messages that have reactions
        `--require any or all` Whether any or all flags should be met before deleting messages.

        In order to use this command, you must have Manage Messages permissions.
        Note that the bot needs Manage Messages as well. These commands cannot
        be used in a private message.

        When the command is done doing its work, you will get a message
        detailing which users got removed and how many messages got removed.
        The purge is also recorded in the moderation log.
        """

        await ctx.defer()

        predicates: list[Callable[[discord.Message], Any]] = self._prepare_purge_predicates(flags)

        if not predicates:
            # If nothing is passed then default to `True` to emulate ?purge all behaviour
            predicates.append(lambda m: True)

        # Bulk delete only works on messages younger than 14 days. This is a hard requirement,
        # so it must not take part in the any/all combination of the user's flags.
        threshold = discord.utils.utcnow() - datetime.timedelta(days=14)

        op = all if flags.require == "all" else any

        def predicate(m: discord.Message) -> bool:
            return m.created_at >= threshold and op(p(m) for p in predicates)

        before = discord.Object(id=flags.before) if flags.before else None
        after = discord.Object(id=flags.after) if flags.after else None

        if before is None and ctx.interaction is not None:
            # If no before: is passed and we're in a slash command,
            # the deferred message will be deleted by purge and the followup will not show up.
            # To work around this, we need to get the deferred message's ID and avoid deleting it.
            before = await ctx.interaction.original_response()

        if not ctx.bot_permissions.manage_messages:
            return await ctx.reply("Bot lacks permission to delete messages.")

        try:
            to_delete = [msg async for msg in ctx.channel.history(limit=limit, before=before, after=after) if predicate(msg)]
        except discord.Forbidden:
            return await ctx.reply("Bot lacks permission to search messages.")
        except discord.HTTPException as e:
            return await ctx.reply(f"Error: {e} (try a smaller search?)")

        for chunk in discord.utils.as_chunks(to_delete, 100):
            try:
                await ctx.channel.delete_messages(  # pyright: ignore[reportAttributeAccessIssue]
                    chunk,
                    reason=f"Action done by {ctx.author} (ID: {ctx.author.id}): Purge",
                )
            except discord.Forbidden:
                return await ctx.reply("Bot lacks permission to delete messages.")
            except discord.HTTPException as e:
                return await ctx.reply(f"Error while deleting: {e}")

        deleted = len(to_delete)
        spammers = Counter(m.author.display_name for m in to_delete)
        messages = [f"{deleted} message{' was' if deleted == 1 else 's were'} removed."]
        if deleted:
            messages.append("")
            messages.extend(f"**{name}**: {count}" for name, count in sorted(spammers.items(), key=lambda t: t[1], reverse=True))

            if ctx.guild is not None:
                await self.log_action(
                    guild=ctx.guild,
                    action="purge",
                    moderator=ctx.author,
                    metadata={"channel": ctx.channel.mention, "messages_removed": str(deleted)},  # pyright: ignore[reportAttributeAccessIssue]
                )

        to_send = "\n".join(messages)

        if len(to_send) > DISCORD_HARD_LIMIT:
            await ctx.send(f"Successfully removed {deleted} messages.", delete_after=10)
        else:
            await ctx.send(to_send, delete_after=10)
        return None

    @commands.command(name="clear_reactions", aliases=["clear-reactions"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear_reactions(
        self,
        ctx: commands.Context[Bot],
        search: commands.Range[int, 1, 2000] = commands.parameter(default=100, description="How many recent messages to scan (1-2000)"),  # noqa: B008
    ):
        """Removes all reactions from messages that have them.

        This command searches through the specified number of messages in the channel and removes all reactions from messages that have them.
        """

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.reply(f"Successfully removed {total_reactions} reactions.")

    def _role_problem(self, ctx: commands.Context[Bot], role: discord.Role, verb: str) -> str | None:
        """Why ``role`` cannot be given/removed by this invocation (bot *and* author hierarchy), or ``None``."""
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        if role.is_default() or role.managed:
            return f"The role **{role}** (ID: {role.id}) is managed by Discord or an integration and cannot be {verb} manually."
        if ctx.guild.me.top_role <= role:
            return f"Cannot manage the role **{role}** (ID: {role.id}) because it is higher than or equal to bot top role."
        if not _is_owner(ctx, ctx.author) and ctx.author.top_role <= role:
            return f"You cannot manage the role **{role}** (ID: {role.id}) because it is higher than or equal to your top role."
        return None

    @commands.group(name="role", invoke_without_command=True)
    @commands.guild_only()
    async def role(self, ctx: commands.Context[Bot]) -> discord.Message | None:
        """Manage roles in the server.

        This command allows you to manage roles in the server, including creating, deleting, and modifying roles.
        """
        return await ctx.send_help(ctx.command)

    async def _add_role_to_member(
        self, member: discord.Member, role: discord.Role, target: str, author: discord.User | discord.Member
    ) -> tuple[bool, str | None]:
        try:
            await member.add_roles(role, reason=f"Role assigned to {target} by {author} (ID: {author.id})")
        except discord.Forbidden:
            return False, "Permission denied"
        except discord.HTTPException as exc:
            return False, f"HTTP error ({exc.status})"
        except discord.DiscordException:
            return False, "Discord error"
        return True, None

    async def _assign_role(
        self, ctx: commands.Context[Bot], role: discord.Role, members: list[discord.Member], *, target: Literal["bots", "humans", "members"]
    ) -> discord.Message:
        """Assign a role to multiple members with a rolling progress display."""

        if TYPE_CHECKING:
            assert ctx.guild is not None

        problem = self._role_problem(ctx, role, "assigned")
        if problem is not None:
            return await ctx.reply(problem)

        if not members:
            return await ctx.reply(f"There are no {target} in this server.")

        members = [member for member in members if role not in member.roles]

        if not members:
            return await ctx.reply(f"All {target} already have the role **{role}**.")

        page_size = 5
        edit_interval = 2.0

        results: list[tuple[discord.Member, bool]] = []
        failures: Counter[str] = Counter()

        started_at = time.monotonic()
        last_edit = started_at

        def build_progress() -> str:
            lines = [f"**Adding role {role.mention}...**", ""]

            visible = results[-page_size:]
            start_index = len(results) - len(visible) + 1

            for index, (member, success) in enumerate(visible, start=start_index):
                status = "\N{WHITE HEAVY CHECK MARK}" if success else "\N{CROSS MARK}"
                lines.append(f"{index}. {member.mention} {status}")

            lines.append("")
            lines.append(f"Progress: `{len(results)}/{len(members)}`")

            return "\n".join(lines)

        message = await ctx.reply(build_progress(), allowed_mentions=discord.AllowedMentions.none())

        for member in members:
            succeeded, failure = await self._add_role_to_member(member, role, target, ctx.author)
            results.append((member, succeeded))
            if failure is not None:
                failures[failure] += 1

            now = time.monotonic()

            if now - last_edit >= edit_interval or len(results) == len(members):
                try:
                    await message.edit(content=build_progress(), allowed_mentions=discord.AllowedMentions.none())
                except discord.HTTPException:
                    pass
                else:
                    last_edit = now

        success = sum(success for _, success in results)
        failed = len(results) - success
        elapsed = time.monotonic() - started_at

        lines = [f"**Role assignment complete: {role.mention}**"]
        lines.append(f"\N{WHITE HEAVY CHECK MARK} Successful: `{success}`")
        lines.append(f"\N{CROSS MARK} Failed: `{failed}`")
        lines.append("")
        lines.append(f"\N{ALARM CLOCK} Time: `{elapsed:.1f}s`")

        if failures:
            lines.append("")
            lines.append("**Failures:**")

            for reason, count in failures.items():
                lines.append(f"- `{count}` - {reason}")

        await message.edit(content="\n".join(lines), allowed_mentions=discord.AllowedMentions.none())

        return message

    @role.command(name="bot", aliases=["bots"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 10.0, type=commands.BucketType.guild)
    async def role_bot(
        self,
        ctx: commands.Context[Bot],
        *,
        role: discord.Role = commands.parameter(description="The role to assign to bots."),  # noqa: B008
    ) -> discord.Message:
        """Assign a role to all bots in the server."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        bots = [member for member in ctx.guild.members if member.bot]

        return await self._assign_role(ctx, role, bots, target="bots")

    @role.command(name="human", aliases=["humans"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 10.0, type=commands.BucketType.guild)
    async def role_human(
        self,
        ctx: commands.Context[Bot],
        *,
        role: discord.Role = commands.parameter(description="The role to assign to humans."),  # noqa: B008
    ) -> discord.Message:
        """Assign a role to all humans in the server."""

        if TYPE_CHECKING:
            assert ctx.guild is not None

        humans = [member for member in ctx.guild.members if not member.bot]

        return await self._assign_role(ctx, role, humans, target="humans")

    @role.command(name="everyone", aliases=["all"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 10.0, type=commands.BucketType.guild)
    async def role_everyone(
        self,
        ctx: commands.Context[Bot],
        *,
        role: discord.Role = commands.parameter(description="The role to assign to everyone."),  # noqa: B008
    ) -> discord.Message:
        """Assign a role to everyone in the server."""

        if TYPE_CHECKING:
            assert ctx.guild is not None

        return await self._assign_role(ctx, role, list(ctx.guild.members), target="members")

    @role.command(name="add", aliases=["assign", "give", "+=", "+"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_add(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member = commands.parameter(description="The member to assign the role to."),  # noqa: B008
        *,
        role: discord.Role = commands.parameter(description="The role to assign to the member."),  # noqa: B008
    ) -> discord.Message:
        """Assign a role to a member in the server.

        This command assigns the specified role to the specified member in the server.
        You can only assign roles that are below your own top role.
        """
        problem = self._role_problem(ctx, role, "assigned")
        if problem is not None:
            return await ctx.reply(problem)

        try:
            await member.add_roles(role, reason=f"Role assigned by {ctx.author} (ID: {ctx.author.id})")
        except discord.Forbidden:
            return await ctx.reply(f"Failed to assign the role **{role}** (ID: {role.id}) to {member} due to insufficient permissions.")
        except discord.HTTPException as e:
            return await ctx.reply(f"Failed to assign the role **{role}** (ID: {role.id}) to {member} due to an error: {e}.")
        return await ctx.reply(f"Successfully assigned the role **{role}** (ID: {role.id}) to {member}.")

    @role.command(name="remove", aliases=["unassign", "take", "-=", "-"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role_remove(
        self,
        ctx: commands.Context[Bot],
        member: discord.Member = commands.parameter(description="The member to remove the role from."),  # noqa: B008
        *,
        role: discord.Role = commands.parameter(description="The role to remove from the member."),  # noqa: B008
    ) -> discord.Message:
        """Remove a role from a member in the server.

        This command removes the specified role from the specified member in the server.
        You can only remove roles that are below your own top role.
        """
        if problem := self._role_problem(ctx, role, "removed"):
            return await ctx.reply(problem)

        try:
            await member.remove_roles(role, reason=f"Role removed by {ctx.author} (ID: {ctx.author.id})")
        except discord.Forbidden:
            return await ctx.reply(f"Failed to remove the role **{role}** (ID: {role.id}) from {member} due to insufficient permissions.")
        except discord.HTTPException as e:
            return await ctx.reply(f"Failed to remove the role **{role}** (ID: {role.id}) from {member} due to an error: {e}.")
        return await ctx.reply(f"Successfully removed the role **{role}** (ID: {role.id}) from {member}.")


async def setup(bot: Bot) -> None:
    """Load the moderation cog into the bot."""
    await bot.add_cog(Mod(bot))
