from __future__ import annotations

import datetime
import logging
import re
from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict, cast

import arrow

import discord
from core.utils import FutureTime
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.mod")


class Snowflake:
    @classmethod
    async def convert(cls, ctx: commands.Context[Parrot], argument: str) -> int:
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
    contains: str | None = commands.flag(description="Remove messages that contains this string (case sensitive)", default=None)
    prefix: str | None = commands.flag(description="Remove messages that start with this string (case sensitive)", default=None)
    suffix: str | None = commands.flag(description="Remove messages that end with this string (case sensitive)", default=None)
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


def can_execute_action(ctx: commands.Context[Parrot], user: discord.Member, target: discord.Member) -> bool:
    """Return whether ``user`` has sufficient authority to act on ``target``.

    A user may act on another member when they are either:

    * the guild owner;
    * the bot owner; or
    * higher than the target in Discord's role hierarchy.

    This check only determines whether the *user* is allowed to target the
    member. Discord's own permission and role-hierarchy checks still apply
    when the bot attempts to perform the action.
    """
    if TYPE_CHECKING:
        assert ctx.guild is not None

    is_guild_owner = ctx.guild.owner_id == user.id
    is_bot_owner = user.id in (ctx.bot.owner_ids or []) or user.id == ctx.bot.owner_id
    has_higher_role = user.top_role > target.top_role

    return is_guild_owner or is_bot_owner or has_higher_role


class ActionReason(commands.Converter):
    """Convert a command argument into a Discord audit-log reason.

    Discord limits audit-log reason strings to 512 characters. The converter
    prefixes the supplied reason with the invoking user's name and ID so that
    moderation actions retain their source even when viewed outside the
    original command context.
    """

    async def convert(self, ctx: commands.Context[Parrot], argument: str) -> str:
        """Build and validate an audit-log reason."""
        ret = f"{ctx.author} (ID: {ctx.author.id}): {argument}"

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            error_message = f"Reason is too long ({len(argument)}/{reason_max})"
            raise commands.BadArgument(error_message)

        return ret


class MemberID(commands.Converter):
    """Resolve a command argument to a guild member or a member ID.

    Normal Discord member conversion is attempted first. If that fails, the
    argument is interpreted as a raw numeric member ID and looked up through
    the bot.

    A member that cannot be fetched can still be represented by a lightweight
    ID-only object. This supports moderation actions such as hackbans, where a
    full :class:`discord.Member` object is not required.
    """

    async def convert(self, ctx: commands.Context[Parrot], argument: str) -> discord.Member:
        """Convert a command argument into a target member."""
        if TYPE_CHECKING:
            assert ctx.guild is not None and isinstance(ctx.author, discord.Member)

        try:
            member = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                error_message = f"{argument} is not a valid member or member ID."
                raise commands.BadArgument(error_message) from None
            else:
                member = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)

                if member is None:
                    # Some moderation actions only require an ID. Keeping an
                    # ID-only object allows commands such as hackban to target
                    # users who are no longer members of the guild.
                    return cast(
                        discord.Member,
                        discord.Object(id=member_id),
                    )

        if not can_execute_action(ctx, ctx.author, member):
            error_message = f"{ctx.author} does not have sufficient authority to act on {member}."
            raise commands.BadArgument(error_message)

        return member


class BannedMember(commands.Converter):
    """Resolve a command argument to an existing guild ban.

    Numeric arguments are treated as Discord user IDs and queried directly
    through Discord's ban endpoint. Other arguments are matched against the
    string representation of users in the guild's ban list.
    """

    async def convert(
        self,
        ctx: commands.Context[Parrot],
        argument: str,
    ) -> discord.BanEntry:
        """Find a banned user from a command argument."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if argument.isdigit():
            member_id = int(argument, base=10)

            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                error_message = f"User ID {member_id} has not been banned before."
                raise commands.BadArgument(error_message) from None

        entity = await discord.utils.find(
            lambda u: str(u.user) == argument,
            ctx.guild.bans(limit=None),
        )

        if entity is None:
            error_message = f"{argument} has not been banned before."
            raise commands.BadArgument(error_message) from None

        return entity


class MuteMetadata(TypedDict):
    guild_id: int
    member_id: int
    moderator_id: int
    reason: str | None


class Mod(commands.Cog):
    """Commands for moderators and administrators."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    async def kick_member(
        self,
        ctx: commands.Context[Parrot],
        member: Annotated[
            discord.Member,
            MemberID,
        ] = commands.parameter(  # noqa: B008
            description="The member to kick from the server.",
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for kicking the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Kick member from the server."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if reason is None:
            reason = f"{ctx.author} (ID: {ctx.author.id})"

        if member == ctx.guild.me:
            error_message = "Cannot kick the bot itself."
            return await ctx.reply(error_message)

        if member.top_role >= ctx.guild.me.top_role:
            error_message = f"Cannot kick {member}. The bot's role is not high enough."
            return await ctx.reply(error_message)

        await ctx.guild.kick(member, reason=reason)
        return await ctx.reply(f"**{member}** (ID: {member.id}) has been kicked from the server.")

    @commands.command(name="ban", aliases=["hackban"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def ban_member(
        self,
        ctx: commands.Context[Parrot],
        member: Annotated[
            discord.Member,
            MemberID,
        ] = commands.parameter(  # noqa: B008
            description="The member(s) to ban from the server.",
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for banning the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Ban one or more members from the server.

        Members that can be banned are processed even if another target fails.
        The response reports successful and failed targets separately.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if reason is None:
            reason = f"{ctx.author} (ID: {ctx.author.id})"

        if member == ctx.guild.me:
            error_message = "Cannot ban the bot itself."
            return await ctx.reply(error_message)

        if member.top_role >= ctx.guild.me.top_role:
            error_message = f"Cannot ban {member}. The bot's role is not high enough."
            return await ctx.reply(error_message)

        await ctx.guild.ban(member, reason=reason)
        if isinstance(member, discord.Object):
            return await ctx.reply(f"ID: {member.id} has been banned from the server.")
        else:
            return await ctx.reply(f"**{member}** (ID: {member.id}) has been banned from the server.")

    @commands.command(name="massban", aliases=["mass-ban", "multiban", "multi-ban"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def mass_ban_members(
        self,
        ctx: commands.Context[Parrot],
        members: Annotated[
            list[discord.Member],
            commands.Greedy[MemberID],
        ] = commands.parameter(  # noqa: B008
            description="The members to ban from the server.",
            default=None,
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for banning the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Ban one or more members from the server.

        Members that can be banned are processed even if another target fails.
        The response reports successful and failed targets separately.

        The bot will attempt to ban all members in a single bulk operation,
        which is more efficient than banning them one by one.
        However, if any member cannot be banned due to role hierarchy or being the bot itself,
        they will be skipped and reported in the response.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        reason = reason or f"{ctx.author} (ID: {ctx.author.id})"
        me = ctx.guild.me

        bannable, skipped = self._partition_bannable_members(members, me)

        if not bannable:
            return await ctx.reply(
                f"No members could be banned. {len(skipped)} member(s) could not be banned.{self._format_skipped_members(skipped)}",
            )

        result = await ctx.guild.bulk_ban(bannable, reason=reason)

        success_count = len(result.banned)
        failure_count = len(result.failed)

        if not success_count and not failure_count:
            return await ctx.reply(
                "No members were banned. Please check the provided member(s) and try again.",
            )

        if not success_count:
            message = f"Failed to ban any members. {failure_count} member(s) could not be banned."
        else:
            message = f"Successfully banned {success_count} member(s) from the server."

            if failure_count:
                message += f" Failed to ban {failure_count} member(s)."

        return await ctx.reply(
            message + self._format_skipped_members(skipped),
        )

    @staticmethod
    def _partition_bannable_members(members: list[discord.Member], me: discord.Member) -> tuple[list[discord.Member], list[discord.Member]]:
        bannable: list[discord.Member] = []
        skipped: list[discord.Member] = []

        for member in members:
            if member is me or member.top_role >= me.top_role:
                skipped.append(member)
            else:
                bannable.append(member)

        return bannable, skipped

    @staticmethod
    def _format_skipped_members(members: list[discord.Member]) -> str:
        if not members:
            return ""

        prefix = "\nThe following member(s) could not be banned due to role hierarchy or being the bot itself:\n- "
        details = "\n- ".join(f"{member} (ID: {member.id})" for member in members)
        message = prefix + details

        if len(message) > 1900:
            return f"\n-# Some members [{len(members)}] could not be banned due to role hierarchy or being the bot itself."

        return message

    @commands.command(name="softban", aliases=["soft-ban"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def soft_ban_member(
        self,
        ctx: commands.Context[Parrot],
        member: Annotated[
            discord.Member,
            MemberID,
        ] = commands.parameter(  # noqa: B008
            description="The member to softban from the server.",
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for softbanning the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Softban a member from the server.

        A softban is a ban followed by an immediate unban. This removes the
        member from the server and deletes their messages, but allows them to
        rejoin if they wish.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if reason is None:
            reason = f"{ctx.author} (ID: {ctx.author.id})"

        if member == ctx.guild.me:
            error_message = "Cannot softban the bot itself."
            return await ctx.reply(error_message)

        if member.top_role >= ctx.guild.me.top_role:
            error_message = f"Cannot softban {member}. The bot's role is not high enough."
            return await ctx.reply(error_message)

        await ctx.guild.ban(member, reason=reason)
        await ctx.guild.unban(member, reason=f"Softban completed by {ctx.author} (ID: {ctx.author.id})")

        return await ctx.reply(f"**{member}** (ID: {member.id}) has been softbanned from the server.")

    @commands.command(name="unban", aliases=["pardon"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def unban_member(
        self,
        ctx: commands.Context[Parrot],
        member: Annotated[
            discord.BanEntry,
            BannedMember,
        ] = commands.parameter(  # noqa: B008
            description="The member to unban from the server.",
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for unbanning the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Unban a member from the server."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if reason is None:
            reason = f"{ctx.author} (ID: {ctx.author.id})"

        await ctx.guild.unban(member.user, reason=reason)
        return await ctx.reply(f"**{member.user}** (ID: {member.user.id}) has been unbanned from the server.")

    @commands.command(name="timeout", aliases=["stfu"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    async def timeout_member(
        self,
        ctx: commands.Context[Parrot],
        member: discord.Member = commands.parameter(  # noqa: B008
            description="The member to timeout.",
        ),
        duration: FutureTime | None = commands.parameter(  # noqa: B008
            description="The duration of the timeout.",
            default=None,
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for timing out the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Timeout a member from the server.

        A timeout is a temporary restriction on a member's ability to send
        messages or interact with the server. The duration of the timeout is
        specified in seconds, minutes, hours, or days.

        If the duration is not specified or exceeds 28 days, the bot will
        attempt to mute the member using the configured mute role instead. This
        is because Discord's built-in timeout feature has a maximum duration of
        28 days. Mute roles can be used to enforce longer timeouts, but they
        require proper configuration and permissions to work correctly.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if reason is None:
            reason = f"{ctx.author} (ID: {ctx.author.id})"

        if member == ctx.guild.me:
            error_message = "Cannot timeout the bot itself."
            return await ctx.reply(error_message)

        if member.top_role >= ctx.guild.me.top_role:
            error_message = f"Cannot timeout {member}. The bot's role is not high enough."
            return await ctx.reply(error_message)

        if duration is None or (duration and duration.dt > arrow.utcnow().shift(days=28)):
            return await self.mute_using_role(ctx, member=member, duration=duration, reason=reason)

        await member.timeout(duration.dt, reason=reason)

        relative_duration = discord.utils.format_dt(duration.dt, style="R")
        response = f"**{member}** (ID: {member.id}) has been timed out for {relative_duration}."

        return await ctx.reply(response)

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    async def unmute_member(
        self,
        ctx: commands.Context[Parrot],
        member: discord.Member = commands.parameter(  # noqa: B008
            description="The member to unmute.",
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for unmuting the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Unmute a member from the server.

        Unmuting a member removes any timeout restrictions on their ability to
        send messages or interact with the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if reason is None:
            reason = f"{ctx.author} (ID: {ctx.author.id})"

        if member.timed_out_until is not None:
            await member.timeout(None, reason=reason)
            return await ctx.reply(f"**{member}** (ID: {member.id}) has been unmuted from the server.")

        mute_role_id = await ctx.bot.database_manager.get_guild_mute_role(guild_id=ctx.guild.id)
        if mute_role_id is None:
            return await ctx.reply(f"**{member}** (ID: {member.id}) is not currently muted in this server.")

        mute_role = ctx.guild.get_role(mute_role_id) if mute_role_id else None
        if mute_role is None:
            return await ctx.reply(f"**{member}** (ID: {member.id}) is not currently muted in this server.")

        await ctx.bot.database_manager.remove_muted_member(guild_id=ctx.guild.id, member_id=member.id)
        await ctx.bot.timer_manager.delete_timer(event_name="mute", metadata_filter={"guild_id": ctx.guild.id, "member_id": member.id})
        await member.remove_roles(mute_role, reason=reason)

        return await ctx.reply(f"**{member}** (ID: {member.id}) has been unmuted from the server.")

    async def mute_using_role(
        self,
        ctx: commands.Context[Parrot],
        *,
        member: discord.Member,
        duration: FutureTime | None = None,
        reason: str | None = None,
    ) -> discord.Message:
        """Mute a member using the configured mute role."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        mute_role_id = await ctx.bot.database_manager.get_guild_mute_role(guild_id=ctx.guild.id)
        if mute_role_id is None:
            return await ctx.reply("No mute role has been set for this server. Use `mute role <role>` to set a mute role first.")

        mute_role = ctx.guild.get_role(mute_role_id)
        if mute_role is None:
            return await ctx.reply(
                "The configured mute role does not exist in this server. Please set a valid mute role using `mute role <role>` "
                "or create a new mute role using `mute create`.",
            )

        if reason is None:
            reason = f"{ctx.author} (ID: {ctx.author.id})"

        if duration is not None:
            await ctx.bot.timer_manager.create_timer(
                event_name="mute",
                expires_at=duration.dt,
                metadata=MuteMetadata(
                    guild_id=ctx.guild.id,
                    member_id=member.id,
                    moderator_id=ctx.author.id,
                    reason=reason,
                ),
            )

        await member.add_roles(mute_role, reason=reason)
        await ctx.bot.database_manager.add_muted_member(guild_id=ctx.guild.id, member_id=member.id)

        if duration is not None:
            relative_duration = discord.utils.format_dt(duration.dt, style="R")
            return await ctx.reply(f"**{member}** (ID: {member.id}) has been muted for {relative_duration}.")
        else:
            return await ctx.reply(f"**{member}** (ID: {member.id}) has been muted indefinitely.")

    @commands.group(name="mute", invoke_without_command=True)
    @commands.has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context[Parrot],
        member: discord.Member = commands.parameter(  # noqa: B008
            description="The member to timeout.",
        ),
        duration: FutureTime | None = commands.parameter(  # noqa: B008
            description="The duration of the timeout.",
            default=None,
        ),
        *,
        reason: Annotated[
            str | None,
            ActionReason,
        ] = commands.parameter(
            description="The reason for timing out the member(s).",
            default=None,
        ),
    ) -> discord.Message:
        """Manage the mute role for the server."""
        if ctx.invoked_subcommand is None:
            return await self.timeout_member(ctx, member=member, duration=duration, reason=reason)

        return await ctx.send_help(ctx.command)

    @mute.command(name="role")
    @commands.has_permissions(moderate_members=True, manage_roles=True)
    async def mute_role(
        self,
        ctx: commands.Context[Parrot],
        *,
        role: discord.Role = commands.parameter(  # noqa: B008
            description="The role to assign to muted members.",
        ),
    ) -> discord.Message:
        """Set the mute role for the server.

        The mute role is assigned to members when they are muted, restricting
        their ability to send messages or interact with the server.

        This will overwrite any existing mute role for the server. Make sure
        the mute role has the correct permissions set to prevent muted members
        from sending messages or interacting with the server. Use `mute sync`
        to automatically adjust the permissions of the mute role.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        await ctx.bot.database_manager.set_guild_mute_role(guild_id=ctx.guild.id, mute_role_id=role.id)
        suggestion = (
            "-# Make sure the mute role has the correct permissions set to prevent muted members "
            "from sending messages or interacting with the server. Use `mute sync` to automatically adjust the permissions of the mute role."
        )
        return await ctx.reply(f"The mute role for this server has been set to **{role}** (ID: {role.id}).\n{suggestion}")

    @mute.command(name="sync", aliases=["synchronize", "synchronise"])
    @commands.has_permissions(moderate_members=True, manage_roles=True, manage_channels=True)
    @commands.bot_has_guild_permissions(manage_roles=True, manage_channels=True)
    async def mute_sync(self, ctx: commands.Context[Parrot]) -> discord.Message:
        """Synchronize the permissions of the mute role with the server's channels.

        This command ensures that the mute role has the correct permissions set
        to prevent muted members from sending messages or interacting with the
        server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        mute_role_id = await ctx.bot.database_manager.get_guild_mute_role(guild_id=ctx.guild.id)
        if mute_role_id is None:
            return await ctx.reply("No mute role has been set for this server. Use `mute role <role>` to set a mute role first.")

        mute_role = ctx.guild.get_role(mute_role_id)
        if mute_role is None:
            return await ctx.reply("The configured mute role does not exist in this server. Please set a valid mute role using `mute role <role>`.")

        message_contents = [
            f"Synchronizing the permissions of the mute role **{mute_role}** (ID: {mute_role.id}) with all channels."
            f"This may take a moment... [0/{len(ctx.guild.channels)}]",
        ]
        message = await ctx.reply("\n".join(message_contents))
        for index, channel in enumerate(ctx.guild.channels, start=1):
            overwrite = channel.overwrites_for(mute_role)
            overwrite.send_messages = False
            overwrite.speak = False
            await channel.set_permissions(mute_role, overwrite=overwrite)

            if index % 10 == 0 or index == len(ctx.guild.channels):
                message_contents[1] = f"This may take a moment... [{index}/{len(ctx.guild.channels)}]"
                await message.edit(content="\n".join(message_contents))

        await message.edit(content=f"The permissions of the mute role **{mute_role}** (ID: {mute_role.id}) have been synchronized with all channels.")
        return message

    @mute.command(name="create", aliases=["new", "make", "setup"])
    @commands.has_permissions(moderate_members=True, manage_roles=True, manage_channels=True)
    @commands.bot_has_guild_permissions(manage_roles=True, manage_channels=True)
    async def mute_create(
        self,
        ctx: commands.Context[Parrot],
        *,
        role_name: str = commands.parameter(  # noqa: B008
            description="The name of the mute role to create.",
            default="Muted",
        ),
    ) -> discord.Message:
        """Create a new mute role for the server.

        This command creates a new role with the specified name and sets it as
        the mute role for the server. The role will have permissions set to
        prevent muted members from sending messages or interacting with the
        server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        existing_role_id = await ctx.bot.database_manager.get_guild_mute_role(guild_id=ctx.guild.id)
        existing_role = ctx.guild.get_role(existing_role_id) if existing_role_id else None

        if existing_role is not None:
            return await ctx.reply(
                f"A mute role already exists ({existing_role} - {existing_role_id}) for this server. "
                "Use `mute role <role>` to change the mute role or `mute sync` to synchronize its permissions.",
            )

        mute_role = await ctx.guild.create_role(name=role_name, reason=f"Mute role created by {ctx.author} (ID: {ctx.author.id})")
        await ctx.bot.database_manager.set_guild_mute_role(guild_id=ctx.guild.id, mute_role_id=mute_role.id)

        message_contents = [
            f"A new mute role **{mute_role}** (ID: {mute_role.id}) has been created for this server. ",
            f"Syncing its permissions with all channels. This may take a moment... [0/{len(ctx.guild.channels)}]",
        ]
        message = await ctx.reply("".join(message_contents))

        for index, channel in enumerate(ctx.guild.channels, start=1):
            overwrite = channel.overwrites_for(mute_role)
            overwrite.send_messages = False
            overwrite.speak = False
            await channel.set_permissions(mute_role, overwrite=overwrite)

            if index % 10 == 0 or index == len(ctx.guild.channels):
                message_contents[1] = f"Syncing its permissions with all channels. This may take a moment... [{index}/{len(ctx.guild.channels)}]"
                await message.edit(content="".join(message_contents))

        await message.edit(content=f"A new mute role **{mute_role}** (ID: {mute_role.id}) has been created and synchronized with all channels.")
        return message

    @mute.command(name="remove", aliases=["delete", "del", "rm", "unbind"])
    @commands.has_permissions(moderate_members=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def mute_remove(self, ctx: commands.Context[Parrot]) -> discord.Message:
        """Remove the mute role from the server.

        This command removes the mute role from the server and deletes it. Any
        members who were muted will no longer have the mute role assigned to
        them.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        mute_role_id = await ctx.bot.database_manager.get_guild_mute_role(guild_id=ctx.guild.id)
        if mute_role_id is None:
            return await ctx.reply("No mute role has been set for this server.")

        mute_role = ctx.guild.get_role(mute_role_id)
        if mute_role is None:
            return await ctx.reply("The configured mute role does not exist in this server.")

        await mute_role.delete(reason=f"Mute role removed by {ctx.author} (ID: {ctx.author.id})")
        await ctx.bot.database_manager.delete_mute_role(guild_id=ctx.guild.id)
        await ctx.bot.timer_manager.delete_timer(event_name="mute", metadata_filter={"guild_id": ctx.guild.id}, multiple=True)

        return await ctx.reply(f"The mute role **{mute_role}** (ID: {mute_role.id}) has been removed from the server.")

    @mute.command(name="list", aliases=["show", "view", "ls"])
    @commands.has_permissions(moderate_members=True)
    async def mute_list(self, ctx: commands.Context[Parrot]) -> discord.Message:
        """List all currently muted members in the server."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        muted_members = await ctx.bot.database_manager.get_muted_members(guild_id=ctx.guild.id)
        if not muted_members:
            return await ctx.reply("There are no currently muted members in this server.")

        member_mentions = []
        for member_id in muted_members:
            member = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
            if member is not None:
                member_mentions.append(f"{member} (ID: {member.id})")
            else:
                member_mentions.append(f"Unknown Member (ID: {member_id})")

        timed_out_members = [member for member in ctx.guild.members if member.timed_out_until is not None]
        for member in timed_out_members:
            if member.id not in muted_members:
                member_mentions.append(f"{member} (ID: {member.id}) - Timed Out")

        member_mentions.sort(key=lambda m: m.lower())

        message_lines = ["Currently muted members in this server:"]
        message_lines.extend(f"- {mention}" for mention in member_mentions)

        return await ctx.reply("\n".join(message_lines))

    @commands.Cog.listener()
    async def on_mute_timer_complete(self, metadata: MuteMetadata) -> None:
        """Handle the completion of a mute timer."""
        guild = self.bot.get_guild(metadata["guild_id"])
        if guild is None:
            _log.warning("Guild not found for mute timer completion: %s", metadata)
            return

        member = await self.bot.get_or_fetch_member(guild, metadata["member_id"])
        if member is None:
            _log.warning("Member not found for mute timer completion: %s", metadata)
            return

        mute_role_id = await self.bot.database_manager.get_guild_mute_role(guild_id=guild.id)
        if mute_role_id is None:
            _log.warning("Mute role not set for guild: %s", guild.id)
            return

        mute_role = guild.get_role(mute_role_id)
        if mute_role is None:
            _log.warning("Mute role not found in guild: %s", guild.id)
            return

        responsible_moderator = await self.bot.get_or_fetch_member(guild, metadata["moderator_id"])
        reason = ""
        if responsible_moderator is not None:
            reason = f"Mute timer completed. Originally muted by {responsible_moderator} (ID: {responsible_moderator.id})."
        else:
            reason = "Mute timer completed. Original moderator not found."

        await member.remove_roles(mute_role, reason=reason)
        await self.bot.database_manager.remove_muted_member(guild_id=guild.id, member_id=member.id)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Handle a member rejoining the server while muted."""
        if TYPE_CHECKING:
            assert member.guild is not None

        muted_members = await self.bot.database_manager.get_muted_members(guild_id=member.guild.id)
        if member.id in muted_members:
            mute_role_id = await self.bot.database_manager.get_guild_mute_role(guild_id=member.guild.id)
            if mute_role_id is None:
                _log.warning("Mute role not set for guild: %s", member.guild.id)
                return

            mute_role = member.guild.get_role(mute_role_id)
            if mute_role is None:
                _log.warning("Mute role not found in guild: %s", member.guild.id)
                return

            reason = "Member rejoined while muted."
            await member.add_roles(mute_role, reason=reason)

    @commands.Cog.listener("on_member_update")
    async def sticky_mute_role(self, before: discord.Member, after: discord.Member) -> None:
        """If someone removes the mute role from a muted member, reapply it.
        We don't care if they are muted via timeout, since Discord handles that automatically."""

        removed_roles = set(before.roles) - set(after.roles)
        if not removed_roles:
            return

        muted_members = await self.bot.database_manager.get_muted_members(guild_id=before.guild.id)
        if after.id in muted_members:
            mute_role_id = await self.bot.database_manager.get_guild_mute_role(guild_id=before.guild.id)
            if mute_role_id is None:
                _log.warning("Mute role not set for guild: %s", before.guild.id)
                return

            mute_role = before.guild.get_role(mute_role_id)
            if mute_role is None:
                _log.warning("Mute role not found in guild: %s", before.guild.id)
                return

            if mute_role in removed_roles:
                reason = "Sticky mute role enforcement."
                await after.add_roles(mute_role, reason=reason)

    @commands.Cog.listener("on_member_update")
    async def mimic_mute_command(self, before: discord.Member, after: discord.Member) -> None:
        """If someone mutes by adding role then sync them to the database."""
        if TYPE_CHECKING:
            assert before.guild is not None and after.guild is not None

        before_roles = set(before.roles)
        after_roles = set(after.roles)

        added_mute_role = after_roles - before_roles

        mute_role_id = await self.bot.database_manager.get_guild_mute_role(guild_id=before.guild.id)
        if mute_role_id is None:
            _log.warning("Mute role not set for guild: %s", before.guild.id)
            return

        has_mute_role = any(role.id == mute_role_id for role in added_mute_role)
        if added_mute_role and has_mute_role:
            await self.bot.database_manager.add_muted_member(guild_id=before.guild.id, member_id=after.id)

    @commands.Cog.listener("on_ready")
    async def sync_mute_roles(self) -> None:
        """Sync mute roles for all guilds on bot startup."""
        async for guild_id, muted_members_id in self.bot.database_manager.get_all_muted_members():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                _log.warning("Guild not found for mute role sync: %s", guild_id)
                continue

            if not guild.chunked:
                await guild.chunk()

            mute_role_id = await self.bot.database_manager.get_guild_mute_role(guild_id=guild.id)
            if mute_role_id is None:
                _log.warning("Mute role not set for guild: %s", guild.id)
                continue

            mute_role = guild.get_role(mute_role_id)
            if mute_role is None:
                _log.warning("Mute role not found in guild: %s", guild.id)
                continue

            for member_id in muted_members_id:
                member = await self.bot.get_or_fetch_member(guild, member_id)
                if member is None:
                    _log.warning("Muted member not found in guild: %s, member ID: %s", guild.id, member_id)
                    continue

                if mute_role not in member.roles:
                    reason = "Syncing mute roles on bot startup."
                    await member.add_roles(mute_role, reason=reason)

    async def _basic_cleanup_strategy(self, ctx: commands.Context[Parrot], search: int):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
                await msg.delete()
                count += 1
        return {"Bot": count}

    async def _complex_cleanup_strategy(self, ctx: commands.Context[Parrot], search: int):
        assert ctx.guild is not None

        prefixes = await self.bot.get_prefix(ctx.message)

        def check(m: discord.Message):
            return m.author == ctx.me or m.content.startswith(tuple(prefixes))

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)  # pyright: ignore[reportAttributeAccessIssue]
        return Counter(m.author.display_name for m in deleted)

    async def _regular_user_cleanup_strategy(self, ctx: commands.Context[Parrot], search: int):
        prefixes = await self.bot.get_prefix(ctx.message)

        def check(m: discord.Message):
            return (m.author == ctx.me or m.content.startswith(tuple(prefixes))) and not (m.mentions or m.role_mentions)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)  # pyright: ignore[reportAttributeAccessIssue]
        return Counter(m.author.display_name for m in deleted)

    @commands.command(hidden=True)
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def cleanup(self, ctx: commands.Context[Parrot], search: int = 100):
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

        assert isinstance(ctx.me, discord.Member) and isinstance(ctx.author, discord.Member)

        strategy = self._basic_cleanup_strategy
        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            if is_mod:
                strategy = self._complex_cleanup_strategy
            else:
                strategy = self._regular_user_cleanup_strategy

        if is_mod:
            search = min(max(2, search), 1000)
        else:
            search = min(max(2, search), 25)

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [f"{deleted} message{' was' if deleted == 1 else 's were'} removed."]
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"- **{author}**: {count}" for author, count in spammers)

        await ctx.reply("\n".join(messages), delete_after=10)

    @commands.command(aliases=["remove"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(  # noqa: PLR0912, PLR0915, C901
        self,
        ctx: commands.Context[Parrot],
        limit: commands.Range[int, 1, 2000] = commands.parameter(  # noqa: B008
            description="The number of messages to search through.",
            default=100,
        ),
        *,
        flags: PurgeFlags,
    ):
        """Removes messages that meet a criteria.

        This command uses a syntax similar to Discord's search bar.
        The messages are only deleted if all options are met unless
        the `--require ` flag is passed to override the behaviour.

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
        """

        await ctx.defer()

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
            predicates.append(lambda m: flags.contains in m.content)  # type: ignore

        if flags.prefix:
            predicates.append(lambda m: m.content.startswith(flags.prefix))  # type: ignore

        if flags.suffix:
            predicates.append(lambda m: m.content.endswith(flags.suffix))  # type: ignore

        if not predicates:
            # If nothing is passed then default to `True` to emulate ?purge all behaviour
            predicates.append(lambda m: True)

        # Only allow deleting recent messages
        # Technically a breaking change since the old purge allowed single deletes
        threshold = discord.utils.utcnow() - datetime.timedelta(days=14)
        predicates.append(lambda m: m.created_at >= threshold)

        op = all if flags.require == "all" else any

        def predicate(m: discord.Message) -> bool:
            r = op(p(m) for p in predicates)
            return r

        if flags.after:
            if limit is None:
                limit = 2000

        if limit is None:
            limit = 100

        before = discord.Object(id=flags.before) if flags.before else None
        after = discord.Object(id=flags.after) if flags.after else None

        if before is None and ctx.interaction is not None:
            # If no before: is passed and we're in a slash command,
            # the deferred message will be deleted by purge and the followup will not show up.
            # To work around this, we need to get the deferred message's ID and avoid deleting it.
            before = await ctx.interaction.original_response()

        if not ctx.bot_permissions.manage_messages:
            return await ctx.reply("I do not have permissions to delete messages.")

        try:
            deleted = [msg async for msg in ctx.channel.history(limit=limit, before=before, after=after) if predicate(msg)]
        except discord.Forbidden:
            return await ctx.reply("I do not have permissions to search for messages.")
        except discord.HTTPException as e:
            return await ctx.reply(f"Error: {e} (try a smaller search?)")

        for chunk in discord.utils.as_chunks(deleted, 100):
            try:
                await ctx.channel.delete_messages(chunk, reason=f"Action done by {ctx.author} (ID: {ctx.author.id}): Purge")  # pyright: ignore[reportAttributeAccessIssue]
            except discord.Forbidden:
                return await ctx.reply("I do not have permissions to delete messages.")
            except discord.HTTPException as e:
                return await ctx.reply(f"Error while deleting: {e}")

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f"{deleted} message{' was' if deleted == 1 else 's were'} removed."]
        if deleted:
            messages.append("")
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"**{name}**: {count}" for name, count in spammers)

        to_send = "\n".join(messages)

        if len(to_send) > 2000:
            await ctx.reply(f"Successfully removed {deleted} messages.", delete_after=10)
        else:
            await ctx.reply(to_send, delete_after=10)

    @commands.command(name="clear_reactions", aliases=["clear-reactions"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear_reactions(self, ctx: commands.Context[Parrot], search: commands.Range[int, 1, 2000] = 100):
        """Removes all reactions from messages that have them.

        You must have Manage Messages to use this command.
        """

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.reply(f"Successfully removed {total_reactions} reactions.")

    @commands.group(name="role", invoke_without_command=True)
    async def role(self, ctx: commands.Context[Parrot]) -> discord.Message | None:
        """Manage roles in the server.

        This command allows you to manage roles in the server, including
        creating, deleting, and modifying roles. You must have Manage Roles
        permissions to use this command.
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @role.command(name="bot", aliases=["bots"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def role_bot(
        self,
        ctx: commands.Context[Parrot],
        *,
        role: discord.Role = commands.parameter(  # noqa: B008
            description="The role to assign to bots.",
        ),
    ) -> discord.Message:
        """Assign a role to all bots in the server.

        This command assigns the specified role to all bots in the server.
        You must have Manage Roles permissions to use this command.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if ctx.guild.me.top_role <= role:
            return await ctx.reply(f"Cannot assign the role **{role}** (ID: {role.id}) because it is higher than or equal to bot top role.")

        bots = [member for member in ctx.guild.members if member.bot]
        if not bots:
            return await ctx.reply("There are no bots in this server.")

        success = 0
        error = 0

        for bot in bots:
            try:
                await bot.add_roles(role, reason=f"Role assigned to bot by {ctx.author} (ID: {ctx.author.id})")
                success += 1
            except discord.Forbidden, discord.HTTPException:
                error += 1

        if error:
            return await ctx.reply(
                f"Successfully assigned the role **{role}** (ID: {role.id}) to {success} bots, but failed to assign it to {error} bots.",
            )
        else:
            return await ctx.reply(f"Successfully assigned the role **{role}** (ID: {role.id}) to all {success} bots in the server.")

    @role.command(name="human", aliases=["humans"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def role_human(
        self,
        ctx: commands.Context[Parrot],
        *,
        role: discord.Role = commands.parameter(  # noqa: B008
            description="The role to assign to humans.",
        ),
    ) -> discord.Message:
        """Assign a role to all humans in the server.

        This command assigns the specified role to all humans in the server.
        You must have Manage Roles permissions to use this command.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if ctx.guild.me.top_role <= role:
            return await ctx.reply(f"Cannot assign the role **{role}** (ID: {role.id}) because it is higher than or equal to bot top role.")

        humans = [member for member in ctx.guild.members if not member.bot]
        if not humans:
            return await ctx.reply("There are no humans in this server.")

        success = 0
        error = 0

        for human in humans:
            try:
                await human.add_roles(role, reason=f"Role assigned to human by {ctx.author} (ID: {ctx.author.id})")
                success += 1
            except discord.Forbidden, discord.HTTPException:
                error += 1

        if error:
            return await ctx.reply(
                f"Successfully assigned the role **{role}** (ID: {role.id}) to {success} humans, but failed to assign it to {error} humans.",
            )
        else:
            return await ctx.reply(f"Successfully assigned the role **{role}** (ID: {role.id}) to all {success} humans in the server.")

    @role.command(name="everyone", aliases=["all"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def role_everyone(
        self,
        ctx: commands.Context[Parrot],
        *,
        role: discord.Role = commands.parameter(  # noqa: B008
            description="The role to assign to everyone.",
        ),
    ) -> discord.Message:
        """Assign a role to everyone in the server.

        This command assigns the specified role to everyone in the server.
        You must have Manage Roles permissions to use this command.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None

        if ctx.guild.me.top_role <= role:
            return await ctx.reply(f"Cannot assign the role **{role}** (ID: {role.id}) because it is higher than or equal to bot top role.")

        members = ctx.guild.members
        if not members:
            return await ctx.reply("There are no members in this server.")

        success = 0
        error = 0

        for member in members:
            try:
                await member.add_roles(role, reason=f"Role assigned to everyone by {ctx.author} (ID: {ctx.author.id})")
                success += 1
            except discord.Forbidden, discord.HTTPException:
                error += 1

        if error:
            return await ctx.reply(
                f"Successfully assigned the role **{role}** (ID: {role.id}) to {success} members, but failed to assign it to {error} members.",
            )
        else:
            return await ctx.reply(f"Successfully assigned the role **{role}** (ID: {role.id}) to all {success} members in the server.")


async def setup(bot: Parrot) -> None:
    """Load the moderation cog into the bot."""
    await bot.add_cog(Mod(bot))
