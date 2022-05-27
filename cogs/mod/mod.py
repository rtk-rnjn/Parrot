from __future__ import annotations

import argparse
import shlex
from cogs.mod.embeds import (
    MEMBER_EMBED,
    ROLE_EMBED,
    TEXT_CHANNEL_EMBED,
    VOICE_CHANNEL_EMBED,
)

from cogs.mod.flags import warnFlag
from cogs.mod import method as mt
from cogs.meta.robopage import TextPageSource, RoboPages

from discord.ext import commands
import discord
import re
import asyncio
from typing import Any, List, Optional, Union
from typing_extensions import Annotated

from core import Parrot, Context, Cog

from utilities.checks import is_mod, in_temp_channel
from utilities.converters import ActionReason, BannedMember, MemberID
from utilities.time import FutureTime, ShortTime
from utilities.infraction import delete_many_warn, custom_delete_warn, warn, show_warn


class Arguments(argparse.ArgumentParser):
    def error(self, message: str):
        raise RuntimeError(message)


class Moderator(Cog):
    """A simple moderator's tool for managing the server."""

    def __init__(self, bot: Parrot):
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="moderator", id=892424227007918121)

    @commands.group()
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def role(self, ctx: Context):
        """Role Management of the server."""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @role.command(name="bots")
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def add_role_bots(
        self,
        ctx: Context,
        operator: str,
        role: discord.Role,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Gives a role to the all bots."""
        await mt._add_roles_bot(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            operator=operator,
            role=role,
            reason=reason,
        )

    @role.command(name="humans")
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def add_role_human(
        self,
        ctx: Context,
        operator: str,
        role: discord.Role,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Gives a role to the all humans."""
        await mt._add_roles_humans(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            operator=operator,
            role=role,
            reason=reason,
        )

    @role.command(name="add", aliases=["arole", "giverole", "grole"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def add_role(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        role: discord.Role,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Gives a role to the specified member(s)."""
        await mt._add_roles(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            role=role,
            reason=reason,
        )

    @role.command(name="remove", aliases=["urole", "removerole", "rrole"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def remove_role(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        role: discord.Role,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Remove the mentioned role from mentioned/id member"""
        await mt._remove_roles(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            role=role,
            reason=reason,
        )

    @commands.command(aliases=["hackban"])
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def ban(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        days: Optional[int] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Bans a member from the server.

        You can also ban from ID to ban regardless whether they're in the server or not.

        In order for this to work, the bot must have Ban Member permissions.
        To use this command you must have Ban Members permission.
        """
        if days is None:
            days = 0
        await mt._ban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            days=days,
            reason=reason,
            silent=False,
        )

    @commands.command(name="massban")
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def mass_ban(
        self,
        ctx: Context,
        members: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        days: Optional[int] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Bans multiple members from the server.

        This only works through banning via ID.

        In order for this to work, the bot must have Ban Member permissions.

        To use this command you must have Ban Members permission."""
        if days is None:
            days = 0
        await mt._mass_ban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            members=members,
            days=0,
            reason=reason,
        )

    @commands.command(aliases=["softkill"])
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def softban(
        self,
        ctx: Context,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Soft bans a member from the server.

        A softban is basically banning the member from the server but then unbanning the member as well. This allows you to essentially kick the member while removing their messages.

        In order for this to work, the bot must have Ban Member permissions.
        To use this command you must have Kick Members permissions
        """
        await mt._softban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            members=member,
            reason=reason,
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def tempban(
        self,
        ctx: Context,
        duration: FutureTime,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Temporarily bans a member for the specified duration.

        The duration can be a a short time form, e.g. 30d or a more human duration such as "until thursday at 3PM" or a more concrete time such as "2024-12-31".

        Note that times are in UTC.

        You can also ban from ID to ban regardless whether they're in the server or not.

        In order for this to work, the bot must have Ban Member permissions.
        To use this command you must have Ban Members permission."""
        await mt._temp_ban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            members=member,
            reason=reason,
            duration=duration,
            silent=False,
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(
        manage_channels=True, manage_permissions=True, manage_roles=True
    )
    @Context.with_type
    async def block(
        self,
        ctx: Context,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Blocks a user from replying message in that channel."""
        await mt._block(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            channel=ctx.channel,
            members=member,
            reason=reason,
            silent=False,
        )

    @commands.command(aliases=["nuke"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_channels=True))
    @commands.bot_has_permissions(manage_channels=True)
    @Context.with_type
    async def clone(
        self,
        ctx: Context,
        channel: discord.TextChannel = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To clone the channel or to nukes the channel (clones and delete)."""
        await mt._clone(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            reason=reason,
            channel=channel or ctx.channel,
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(kick_members=True)
    @Context.with_type
    async def kick(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To kick a member from guild."""
        await mt._kick(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @commands.command(name="masskick")
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(kick_members=True)
    @Context.with_type
    async def mass_kick(
        self,
        ctx: Context,
        members: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To kick a member from guild."""
        await mt._mass_kick(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            members=members,
            reason=reason,
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(
        manage_channels=True, manage_permissions=True, manage_roles=True
    )
    @Context.with_type
    async def lock(
        self,
        ctx: Context,
        channel: commands.Greedy[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]
        ],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To lock the channel"""
        channel = channel or [ctx.channel]
        for chn in channel:
            if isinstance(chn, discord.TextChannel):
                await mt._text_lock(
                    guild=ctx.guild,
                    command_name=ctx.command.qualified_name,
                    ctx=ctx,
                    destination=ctx.channel,
                    channel=chn,
                    reason=reason,
                )
            elif isinstance(chn, (discord.VoiceChannel, discord.StageChannel)):
                await mt._vc_lock(
                    guild=ctx.guild,
                    command_name=ctx.command.qualified_name,
                    ctx=ctx,
                    destination=ctx.channel,
                    channel=chn,
                    reason=reason,
                )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_channels=True))
    @commands.bot_has_permissions(
        manage_channels=True, manage_roles=True, manage_permissions=True
    )
    @Context.with_type
    async def unlock(
        self,
        ctx: Context,
        channel: commands.Greedy[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]
        ],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To unlock the channel"""
        channel = channel or [ctx.channel]
        for chn in channel:
            if isinstance(chn, discord.TextChannel):
                await mt._text_unlock(
                    guild=ctx.guild,
                    command_name=ctx.command.qualified_name,
                    ctx=ctx,
                    destination=ctx.channel,
                    channel=chn,
                    reason=reason,
                )

            elif isinstance(chn, (discord.VoiceChannel, discord.StageChannel)):
                await mt._vc_unlock(
                    guild=ctx.guild,
                    command_name=ctx.command.qualified_name,
                    ctx=ctx,
                    destination=ctx.channel,
                    channel=chn,
                    reason=reason,
                )

    @commands.command(aliases=["mute"])
    @commands.bot_has_permissions(moderate_members=True)
    @commands.check_any(is_mod(), commands.has_permissions(moderate_members=True))
    @Context.with_type
    async def timeout(
        self,
        ctx: Context,
        member: discord.Member,
        duration: Optional[ShortTime] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To Timeout the member, from chat."""
        if duration:
            await mt._timeout(
                guild=ctx.guild,
                command_name=ctx.command.qualified_name,
                ctx=ctx,
                destination=ctx.channel,
                member=member,
                _datetime=duration.dt,
                reason=reason,
            )
        else:
            await mt._mute(
                guild=ctx.guild,
                command_name=ctx.command.qualified_name,
                ctx=ctx,
                destination=ctx.channel,
                member=member,
                reason=reason,
            )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def unmute(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To allow a member to sending message in the Text Channels, if muted/timeouted."""
        await mt._unmute(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @commands.group(aliases=["purge"], invoke_without_command=True)
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    @Context.with_type
    async def clear(
        self,
        ctx: Context,
        num: int = 100,
    ):
        """Removes messages that meet a criteria.

        In order to use this command, you must have Manage Messages permissions.

        Note that the bot needs Manage Messages as well. These commands cannot be used in a private message.
        When the command is done doing its work, you will get a message detailing which users got removed and how many messages got removed.
        """
        if ctx.invoked_subcommand is None:

            def check(message: discord.Message) -> bool:
                return True

            await mt.do_removal(ctx, num, check)

    @clear.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def embeds(self, ctx: Context, search: int = 100):
        """Removes messages that have embeds in them."""
        await mt.do_removal(ctx, search, lambda e: len(e.embeds))

    @clear.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def files(self, ctx: Context, search: int = 100):
        """Removes messages that have attachments in them."""
        await mt.do_removal(ctx, search, lambda e: len(e.attachments))

    @clear.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def images(self, ctx: Context, search: int = 100):
        """Removes messages that have embeds or attachments."""
        await mt.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @clear.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def user(self, ctx: Context, member: discord.Member, search: int = 100):
        """Removes all messages by the member."""
        await mt.do_removal(ctx, search, lambda e: e.author == member)

    @clear.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def contains(self, ctx: Context, *, substr: str):
        """Removes all messages containing a substring.
        The substring must be at least 3 characters long.
        """
        if len(substr) < 3:
            await ctx.send("The substring length must be at least 3 characters.")
        else:
            await mt.do_removal(ctx, 100, lambda e: substr in e.content)

    @clear.command(name="bot", aliases=["bots"])
    async def _bot(self, ctx: Context, prefix: Optional[str] = None, search: int = 100):
        """Removes a bot user's messages and messages with their optional prefix."""

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or (
                prefix and m.content.startswith(prefix)
            )

        await mt.do_removal(ctx, search, predicate)

    @clear.command(name="emoji", aliases=["emojis"])
    async def _emoji(self, ctx: Context, search: int = 100):
        """Removes all messages containing custom emoji."""
        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        def predicate(m):
            return custom_emoji.search(m.content)

        await mt.do_removal(ctx, search, predicate)

    @clear.command(name="reactions")
    async def _reactions(self, ctx: Context, search: int = 100):
        """Removes all reactions from messages that have them."""

        if search > 2000:
            return await ctx.send(f"Too many messages to search for ({search}/2000)")

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        await ctx.send(f"Successfully removed {total_reactions} reactions.")

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_channels=True))
    @commands.bot_has_permissions(manage_channels=True)
    @Context.with_type
    async def slowmode(
        self,
        ctx: Context,
        seconds: int,
        channel: discord.TextChannel = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To set slowmode in the specified channel"""
        await mt._slowmode(
            guild=ctx.guild,
            command_name=ctx.command.name,
            ctx=ctx,
            destination=ctx.channel,
            seconds=seconds,
            channel=channel or ctx.channel,
            reason=reason,
        )

    @clear.command()
    async def custom(self, ctx: Context, *, arguments: str):
        """A more advanced purge command.

        This command uses a powerful "command line" syntax.

        Most options support multiple values to indicate 'any' match.
        If the value has spaces it must be quoted.
        The messages are only deleted if all options are met unless the `--or` flag is passed, in which case only if any is met.

        The following options are valid.
        `--user`: A mention or name of the user to remove.
        `--contains`: A substring to search for in the message.
        `--starts`: A substring to search if the message starts with.
        `--ends`: A substring to search if the message ends with.
        `--search`: How many messages to search. Default 100. Max 2000.
        `--after`: Messages must come after this message ID.
        `--before`: Messages must come before this message ID.

        Flag options (no arguments):
        `--bot`: Check if it's a bot user.
        `--embeds`: Check if the message has embeds.
        `--files`: Check if the message has attachments.
        `--emoji`: Check if the message has custom emoji.
        `--reactions`: Check if the message has reactions
        `--or`: Use logical OR for all options.
        `--not`: Use logical NOT for all options.
        """
        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument("--user", nargs="+")
        parser.add_argument("--contains", nargs="+")
        parser.add_argument("--starts", nargs="+")
        parser.add_argument("--ends", nargs="+")
        parser.add_argument("--or", action="store_true", dest="_or")
        parser.add_argument("--not", action="store_true", dest="_not")
        parser.add_argument("--emoji", action="store_true")
        parser.add_argument("--bot", action="store_const", const=lambda m: m.author.bot)
        parser.add_argument(
            "--embeds", action="store_const", const=lambda m: len(m.embeds)
        )
        parser.add_argument(
            "--files", action="store_const", const=lambda m: len(m.attachments)
        )
        parser.add_argument(
            "--reactions", action="store_const", const=lambda m: len(m.reactions)
        )
        parser.add_argument("--search", type=int)
        parser.add_argument("--after", type=int)
        parser.add_argument("--before", type=int)

        try:
            args = parser.parse_args(shlex.split(arguments))
        except Exception as e:
            await ctx.send(str(e))
            return

        predicates = []
        if args.bot:
            predicates.append(args.bot)

        if args.embeds:
            predicates.append(args.embeds)

        if args.files:
            predicates.append(args.files)

        if args.reactions:
            predicates.append(args.reactions)

        if args.emoji:
            custom_emoji = re.compile(r"<:(\w+):(\d+)>")
            predicates.append(lambda m: custom_emoji.search(m.content))

        if args.user:
            users = []
            converter = commands.MemberConverter()
            for u in args.user:
                try:
                    user = await converter.convert(ctx, u)
                    users.append(user)
                except Exception as e:
                    await ctx.send(str(e))
                    return

            predicates.append(lambda m: m.author in users)

        if args.contains:
            predicates.append(lambda m: any(sub in m.content for sub in args.contains))

        if args.starts:
            predicates.append(
                lambda m: any(m.content.startswith(s) for s in args.starts)
            )

        if args.ends:
            predicates.append(lambda m: any(m.content.endswith(s) for s in args.ends))

        op = all if not args._or else any

        def predicate(m):
            r = op(p(m) for p in predicates)
            if args._not:
                return not r
            return r

        if args.after and args.search is None:
            args.search = 2000

        if args.search is None:
            args.search = 100

        args.search = max(0, min(2000, args.search))  # clamp from 0-2000
        await mt.do_removal(
            ctx, args.search, predicate, before=args.before, after=args.after
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def unban(
        self,
        ctx: Context,
        member: BannedMember,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To Unban a member from a guild"""
        await mt._unban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @commands.command()
    @commands.check_any(
        is_mod(),
        commands.has_permissions(
            manage_permissions=True, manage_roles=True, manage_channels=True
        ),
    )
    @commands.bot_has_permissions(
        manage_channels=True, manage_permissions=True, manage_roles=True
    )
    @Context.with_type
    async def unblock(
        self,
        ctx: Context,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Unblocks a user from the text channel"""
        await mt._unblock(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            members=member,
            channel=ctx.channel,
            reason=reason,
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_nicknames=True))
    @commands.bot_has_permissions(manage_nicknames=True)
    @Context.with_type
    async def nick(
        self, ctx: Context, member: discord.Member, *, name: commands.clean_content
    ):
        """
        To change the nickname of the specified member
        """
        await mt._change_nickname(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            name=name,
        )

    @commands.group()
    @commands.check_any(
        is_mod(),
        commands.has_guild_permissions(
            mute_members=True,
            manage_channels=True,
            manage_permissions=True,
            deafen_members=True,
            move_members=True,
        ),
        in_temp_channel(),
    )
    @commands.bot_has_guild_permissions(
        mute_members=True,
        manage_channels=True,
        manage_permissions=True,
        deafen_members=True,
        move_members=True,
    )
    @Context.with_type
    async def voice(self, ctx: Context):
        """Voice Moderation"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @voice.command(name="mute")
    @commands.check_any(
        is_mod(), commands.has_guild_permissions(mute_members=True), in_temp_channel()
    )
    @commands.bot_has_guild_permissions(mute_members=True)
    @Context.with_type
    async def voice_mute(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice mute"""
        await mt._voice_mute(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="unmute")
    @commands.check_any(
        is_mod(), commands.has_guild_permissions(mute_members=True), in_temp_channel()
    )
    @commands.bot_has_guild_permissions(mute_members=True)
    @Context.with_type
    async def voice_unmute(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice unmute"""
        await mt._voice_unmute(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="ban")
    @commands.check_any(
        is_mod(),
        commands.has_guild_permissions(manage_channels=True, manage_permissions=True),
        in_temp_channel(),
    )
    @commands.bot_has_guild_permissions(manage_channels=True, manage_permissions=True)
    @Context.with_type
    async def voice_ban(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice ban"""
        if not member.voice:
            return await ctx.send(f"{ctx.author.mention} {member} not in voice channel")
        await mt._voice_ban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
            channel=member.voice.channel,
        )

    @voice.command(name="unban")
    @commands.check_any(
        is_mod(),
        commands.has_guild_permissions(manage_channels=True, manage_permissions=True),
        in_temp_channel(),
    )
    @commands.bot_has_guild_permissions(manage_channels=True, manage_permissions=True)
    @Context.with_type
    async def voice_unban(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice unban"""
        if not member.voice:
            return await ctx.send(f"{ctx.author.mention} {member} not in voice channel")
        await mt._voice_unban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
            channel=member.voice.channel,
        )

    @voice.command(name="deafen")
    @commands.check_any(
        is_mod(), commands.has_guild_permissions(deafen_members=True), in_temp_channel()
    )
    @commands.bot_has_guild_permissions(deafen_members=True)
    @Context.with_type
    async def voice_deafen(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice deafen"""
        await mt._voice_deafen(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="undeafen")
    @commands.check_any(
        is_mod(), commands.has_guild_permissions(deafen_members=True), in_temp_channel()
    )
    @commands.bot_has_guild_permissions(deafen_members=True)
    @Context.with_type
    async def voice_undeafen(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice undeafen"""
        await mt._voice_undeafen(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="kick")
    @commands.check_any(
        is_mod(), commands.has_guild_permissions(move_members=True), in_temp_channel()
    )
    @commands.bot_has_guild_permissions(move_members=True)
    @Context.with_type
    async def voice_kick(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice kick"""
        await mt._voice_kick(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="limit")
    @commands.check_any(
        is_mod(), commands.has_guild_permissions(move_members=True), in_temp_channel()
    )
    @commands.bot_has_guild_permissions(manage_channels=True)
    @Context.with_type
    async def voice_limit(
        self,
        ctx: Context,
        limit: Optional[int] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To set the VC limit"""
        if not ctx.author.voice:
            return await ctx.send(
                f"{ctx.author.mention} you must be in voice channel to use the command"
            )
        await ctx.voice.channel.edit(
            user_limit=limit,
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        if limit:
            await ctx.send(f"{ctx.author.mention} set limit to **{limit}**")
            return
        await ctx.send(
            f"{ctx.author.mention} removed the limit from {ctx.author.voice.channel.mention}"
        )

    @voice.command(name="move")
    @commands.check_any(is_mod(), commands.has_guild_permissions(move_members=True))
    @commands.bot_has_guild_permissions(connect=True, move_members=True)
    @Context.with_type
    async def voice_move(
        self,
        ctx: Context,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        channel: Union[discord.VoiceChannel, None],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice move"""

        def check(m, b, a):
            return m.id == ctx.me.id and (b.channel.id != a.channel.id)

        if channel is None:
            if voicestate := ctx.author.voice:
                if not ctx.guild.me.voice:
                    await voicestate.channel.connect()
                else:
                    await ctx.guild.me.edit(voice_channel=voicestate.channel)
                if not member:
                    member = voicestate.channel.members
            else:
                return await ctx.send(
                    f"{ctx.author.mention} you must specify the the channel or must be in the voice channel to use this command"
                )

            try:
                _, __, a = await self.bot.wait_for(
                    "voice_state_update", timeout=60, check=check
                )
            except asyncio.TimeoutError:
                return await ctx.send(f"{ctx.author.mention} you ran out time")
            else:
                for mem in member:
                    await mem.edit(
                        voice_channel=a.channel,
                        reason=reason,
                    )
        else:
            if not member:
                member = channel.members

            for mem in member:
                await mem.edit(
                    voice_channel=a,
                    reason=reason,
                )

    @commands.group(aliases=["emote"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_emojis=True))
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @Context.with_type
    async def emoji(self, ctx: Context):
        """For Emoji Moderation"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @emoji.command(name="delete")
    @commands.check_any(is_mod(), commands.has_permissions(manage_emojis=True))
    @commands.bot_has_guild_permissions(manage_emojis=True, embed_links=True)
    @Context.with_type
    async def emoji_delete(
        self,
        ctx: Context,
        emoji: commands.Greedy[discord.Emoji],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To delete the emoji"""
        if not emoji:
            return
        await mt._emoji_delete(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            reason=reason,
            emojis=emoji,
        )

    @emoji.command(name="add")
    @commands.check_any(is_mod(), commands.has_permissions(manage_emojis=True))
    @commands.bot_has_guild_permissions(manage_emojis=True, embed_links=True)
    @Context.with_type
    async def emoji_add(
        self,
        ctx: Context,
        emoji: commands.Greedy[discord.Emoji],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To add the emoji"""
        if not emoji:
            return
        await mt._emoji_add(
            guild=ctx.guild,
            command_name=ctx.command.name,
            ctx=ctx,
            destination=ctx.channel,
            emojis=emoji,
            reason=reason,
        )

    @emoji.command(name="addurl")
    @commands.check_any(is_mod(), commands.has_permissions(manage_emojis=True))
    @commands.bot_has_guild_permissions(manage_emojis=True, embed_links=True)
    @Context.with_type
    async def emoji_addurl(
        self,
        ctx: Context,
        url: str,
        name: commands.clean_content,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To add the emoji from url"""
        await mt._emoji_addurl(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            reason=reason,
            url=url,
            name=name,
        )

    @emoji.command(name="rename")
    @commands.check_any(is_mod(), commands.has_permissions(manage_emojis=True))
    @commands.bot_has_guild_permissions(manage_emojis=True, embed_links=True)
    @Context.with_type
    async def emoji_rename(
        self,
        ctx: Context,
        emoji: discord.Emoji,
        name: commands.clean_content,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To rename the emoji"""
        await mt._emoji_rename(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            reason=reason,
            emoji=emoji,
            name=name,
        )

    @commands.command()
    @commands.check_any(
        is_mod(),
        commands.has_permissions(
            manage_permissions=True,
            manage_messages=True,
            manage_channels=True,
            ban_members=True,
            manage_roles=True,
            kick_members=True,
            manage_nicknames=True,
        ),
    )
    @commands.bot_has_permissions(
        manage_permissions=True,
        manage_messages=True,
        manage_channels=True,
        ban_members=True,
        manage_roles=True,
        kick_members=True,
        read_message_history=True,
        add_reactions=True,
        manage_nicknames=True,
    )
    @Context.with_type
    async def mod(
        self,
        ctx: Context,
        target: Union[
            discord.Member, discord.TextChannel, discord.VoiceChannel, discord.Role
        ],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Why to learn the commands? This is all in one mod command."""

        def check_msg(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        if not target:
            return await ctx.send_help(ctx.command)

        guild = ctx.guild

        if isinstance(target, discord.Member):
            member_embed = MEMBER_EMBED.copy()
            member_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon is not None:
                member_embed.set_thumbnail(url=ctx.guild.icon.url)

            msg = await ctx.send(embed=member_embed)
            await ctx.bulk_add_reactions(msg, *mt.MEMBER_REACTION)

            def check(reaction, user) -> bool:
                return (
                    str(reaction.emoji) in mt.MEMBER_REACTION
                    and user == ctx.author
                    and reaction.message.id == msg.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            func = mt.MEMBER_REACTION[str(reaction.emoji)]

            if str(reaction.emoji) in {
                "\N{DOWNWARDS BLACK ARROW}",
                "\N{UPWARDS BLACK ARROW}",
            }:
                temp = await ctx.send(
                    f"{ctx.author.mention} Enter the Role, [ID, NAME, MENTION]"
                )
                try:
                    m = await self.bot.wait_for("message", timeout=30, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                role = await commands.RoleConverter().convert(ctx, m.content)
                await temp.delete()
                await func(
                    guild=ctx.guild,
                    command_name=ctx.command.name,
                    ctx=ctx,
                    destination=ctx.channel,
                    member=target,
                    members=target,
                    role=role,
                    reason=reason,
                )
                return

            if str(reaction.emoji) == "\N{LOWER LEFT FOUNTAIN PEN}":
                await ctx.send(
                    f"{ctx.author.mention} Enter the Nickname, [Not more than 32 char]",
                    delete_after=30,
                )
                try:
                    m = await self.bot.wait_for("message", timeout=30, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)

                await func(
                    guild=ctx.guild,
                    command_name=ctx.command.name,
                    ctx=ctx,
                    destination=ctx.channel,
                    member=target,
                    name=(m.content)[:32:],
                )
                return

            await func(
                guild=ctx.guild,
                command_name=ctx.command.qualified_name,
                ctx=ctx,
                destination=ctx.channel,
                reason=reason,
                member=target,
                members=target,
            )

        if isinstance(target, discord.TextChannel):
            tc_embed = TEXT_CHANNEL_EMBED.copy()
            tc_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon:
                tc_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg = await ctx.send(embed=tc_embed)
            await ctx.bulk_add_reactions(msg, *mt.TEXT_REACTION)

            def check(reaction, user):
                return (
                    str(reaction.emoji) in mt.TEXT_REACTION
                    and user == ctx.author
                    and reaction.message.id == msg.id
                )

            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            func = mt.TEXT_REACTION[str(reaction.emoji)]

            if str(reaction.emoji) in {"\N{MEMO}", "\N{LOWER LEFT FOUNTAIN PEN}"}:
                await ctx.send(
                    f"{ctx.author.mention} Enter the Channel Topic"
                    if str(reaction.emoji) == "\N{MEMO}"
                    else f"{ctx.author.mention} Enter the Channel Name",
                    delete_after=60,
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                await func(
                    guild=ctx.guild,
                    command_name=ctx.command.name,
                    ctx=ctx,
                    destination=ctx.channel,
                    channel=target,
                    channels=target,
                    text=m.content,
                )
                return

            await func(
                guild=ctx.guild,
                command_name=ctx.command.qualified_name,
                ctx=ctx,
                destination=ctx.channel,
                reason=reason,
                channel=target,
                channels=target,
            )

        if isinstance(
            target,
            (
                discord.VoiceChannel,
                discord.StageChannel,
            ),
        ):
            vc_embed = VOICE_CHANNEL_EMBED
            vc_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon:
                vc_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg = await ctx.send(embed=vc_embed)
            await ctx.bulk_add_reactions(msg, *mt.VC_REACTION)

            def check_reaction_vc(reaction, user):
                return (
                    str(reaction.emoji) in mt.VC_REACTION
                    and user == ctx.author
                    and reaction.message.id == msg.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check_reaction_vc
                )
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            func = mt.VC_REACTION[str(reaction.emoji)]

            if str(reaction.emoji) == "\N{LOWER LEFT FOUNTAIN PEN}":
                await ctx.send(
                    f"{ctx.author.mention} Enter the Channel Name", delete_after=60
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                await func(
                    guild=ctx.guild,
                    command_name=ctx.command.name,
                    ctx=ctx,
                    destination=ctx.channel,
                    channel=ctx.channel,
                    text=m.content,
                )
                return
            await func(
                guild=guild,
                command_name=ctx.command.qualified_name,
                ctx=ctx,
                destination=ctx.channel,
                reason=reason,
                channel=target,
                channels=target,
            )

        if isinstance(target, discord.Role):
            role_embed = ROLE_EMBED
            role_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if ctx.guild.icon:
                role_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg = await ctx.send(embed=role_embed)
            await ctx.bulk_add_reactions(msg, *mt.ROLE_REACTION)

            def check_reaction_role(reaction, user):
                return (
                    str(reaction.emoji) in mt.ROLE_REACTION
                    and user == ctx.author
                    and reaction.message.id == msg.id
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check_reaction_role
                )
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            func = mt.ROLE_REACTION[str(reaction.emoji)]

            if str(reaction.emoji) == "\N{RAINBOW}":
                await ctx.send(
                    f"{ctx.author.mention} Enter the Colour, in whole number",
                    delete_after=60,
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                try:
                    color = int(m.content)
                except ValueError:
                    return await ctx.send(f"{ctx.author.mention} invalid color")

                await func(
                    guild=ctx.guild,
                    command_name=ctx.command.name,
                    ctx=ctx,
                    destination=ctx.channel,
                    role=target,
                    int_=color,
                    reason=reason,
                )
                return

            if str(reaction.emoji) == "\N{LOWER LEFT FOUNTAIN PEN}":
                await ctx.send(
                    f"{ctx.author.mention} Enter the Role Name", delete_after=60
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                await mt._change_role_name(
                    guild=ctx.guild,
                    command_name=ctx.command.name,
                    ctx=ctx,
                    destination=ctx.channel,
                    role=target,
                    text=m.content,
                    reason=reason,
                )
                return

            await func(
                guild=ctx.guild,
                command_name=ctx.command.name,
                ctx=ctx,
                destination=ctx.channel,
                role=target,
                _bool=str(reaction.emoji) == "\N{UPWARDS BLACK ARROW}",
                reason=reason,
            )

        return await msg.delete(delay=0)

    @commands.command(name="warn")
    @commands.bot_has_permissions(embed_links=True)
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    async def warnuser(self, ctx: Context, user: discord.Member, *, reason: str):
        """To warn the user"""
        try:
            await user.send(
                f"{user.mention} you are being in **{ctx.guild.name}** warned for: **{reason}**"
            )
        except discord.Forbidden:
            pass
        else:
            await warn(
                ctx.guild,
                user,
                reason,
                moderator=ctx,
                message=ctx.message,
                at=ctx.message.created_at.timestamp(),
                ctx=ctx,
            )
            await ctx.send(f"{ctx.author.mention} **{user}** warned")
        finally:
            await self.warn_task(target=user, ctx=ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    async def delwarn(self, ctx: Context, warn_id: Optional[int] = None):
        """To delete warn of user by ID"""
        if not warn_id:
            return
        somthing = await custom_delete_warn(ctx, ctx.guild, warn_id=warn_id)
        if somthing:
            await ctx.send(f"{ctx.author.mention} deleted the warn ID: {warn_id}")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    async def delwarns(self, ctx: Context, *, flags: warnFlag):
        """To delete warn of user by ID"""
        payload = {}
        if flags.target:
            payload["target"] = flags.target.id
        if flags.moderator:
            payload["moderator"] = flags.moderator.id
        if flags.message:
            payload["message"] = flags.message
        if flags.channel:
            payload["channel"] = flags.channel.id
        if flags.message:
            payload["warn_id"] = flags.warn_id

        await delete_many_warn(ctx, ctx.guild, **payload)
        await ctx.send(
            f"{ctx.author.mention} deleted all warns matching: `{'`, `'.join(payload)}`"
        )
        if flags.target:
            target = await self.bot.get_or_fetch_member(ctx.guild, flags.target.id)
            await self.warn_task(target=target, ctx=ctx)

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    async def warns(self, ctx: Context, *, flags: warnFlag):
        """To display warning in the server"""
        payload = {}
        if flags.target:
            payload["target"] = flags.target.id
        if flags.moderator:
            payload["moderator"] = flags.moderator.id
        if flags.message:
            payload["message"] = flags.message
        if flags.channel:
            payload["channel"] = flags.channel.id
        if flags.message:
            payload["warn_id"] = flags.warn_id
        data = await show_warn(ctx, ctx.guild, **payload)
        page = RoboPages(TextPageSource(data, max_size=1000), ctx=ctx)
        await page.start()

    async def warn_task(
        self,
        *,
        ctx: Context,
        target: Union[discord.Member, discord.User],
    ):
        """|coro|

        Main system to warn

        Parameters
        -----------
        target: Member
            Target, which will be issued warn
        ctx: Context
            commands.Context instance
        """
        count = 0
        col = self.bot.mongo.warn_db[f"{ctx.guild.id}"]
        async for data in col.find({"target": target.id}):
            count += 1
        if data := await self.bot.mongo.parrot_db.server_config.find_one(
            {"_id": ctx.guild.id, "warn_auto.count": count}
        ):
            for i in data["warn_auto"]:
                if i["count"] == count:
                    await self.execute_action(
                        action=i["action"].lower(),
                        duration=i.get("duration"),
                        mod=ctx,
                        ctx=ctx,
                        target=target,
                    )

    async def execute_action(self, *, ctx: Context, action: str, duration: str, **kw):
        target: Union[discord.Member, discord.User] = kw.get("target")
        perms = ctx.guild.me.guild_permissions
        if not (perms.kick_members and perms.moderate_members and perms.ban_members):
            return  # sob sob sob
        if action == "kick":
            return await mt._kick(
                guild=ctx.guild,
                command_name=ctx.command,
                ctx=ctx,
                destination=ctx.channel,
                member=target,
                members=target,
                reason=f"Automod. {target} reached warncount threshold",
                silent=True,
            )
        if action == "ban":
            return await mt._ban(
                guild=ctx.guild,
                command_name=ctx.command,
                ctx=ctx,
                destination=ctx.channel,
                member=target,
                members=target,
                reason=f"Automod. {target} reached warncount threshold",
                silent=True,
            )
        if action == "mute":
            return await mt._mute(
                guild=ctx.guild,
                command_name=ctx.command,
                ctx=ctx,
                destination=ctx.channel,
                member=target,
                members=target,
                reason=f"Automod. {target} reached warncount threshold",
                silent=True,
            )
        if duration:
            dt = ShortTime(duration)
            if action == "timeout":
                return await mt._timeout(
                    guild=ctx.guild,
                    command_name=ctx.command,
                    ctx=ctx,
                    destination=ctx.channel,
                    member=target,
                    members=target,
                    _datetime=dt.dt,
                    reason=f"Automod. {target} reached warncount threshold",
                    silent=True,
                )
            if action == "tempban":
                return await mt._temp_ban(
                    guild=ctx.guild,
                    command_name=ctx.command,
                    ctx=ctx,
                    destination=ctx.channel,
                    member=target,
                    members=target,
                    duration=dt.dt,
                    reason=f"Automod. {target} reached warncount threshold",
                    silent=True,
                )
