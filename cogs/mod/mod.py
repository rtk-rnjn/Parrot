from __future__ import annotations

import argparse
import asyncio
import re
import shlex
from typing import List, Optional, Union

import wavelink
from typing_extensions import Annotated

import discord
from cogs.mod import method as mt
from cogs.mod.embeds import MEMBER_EMBED, ROLE_EMBED, TEXT_CHANNEL_EMBED, VOICE_CHANNEL_EMBED
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.checks import in_temp_channel, is_mod
from utilities.converters import ActionReason, BannedMember, MemberID
from utilities.time import FutureTime, ShortTime


class Arguments(argparse.ArgumentParser):
    def error(self, message: str):
        raise RuntimeError(message)


class Moderator(Cog):
    """A simple moderator's tool for managing the server."""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.ON_TESTING = False

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
        """Gives a role to the all bots.

        You must have Manage Roles permission to use this command,
        or must have the Moderator Role.

        Bot must have Manage Roles permission.

        `operator` can be `+` or `-` to add or remove the role respectively.
        - `+` adds the role to the bots.
        - `-` removes the role from the bots.

        **Examples:**
        - `[p]role bots + @Role`
        - `[p]role bots - @Role`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]role bots + @Role reason`
        - `[p]role bots - @Role reason`
        """
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
        """Gives a role to the all humans.

        You must have Manage Roles permission to use this command,
        or must have the Moderator Role.

        Bot must have Manage Roles permission.

        `operator` can be `+` or `-` to add or remove the role respectively.
        - `+` adds the role to the humans.
        - `-` removes the role from the humans.

        **Examples:**
        - `[p]role humans + @Role`
        - `[p]role humans - @Role`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]role humans + @Role reason`
        - `[p]role humans - @Role reason`
        """
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
        """Gives a role to the specified member(s).

        You must have Manage Roles permission to use this command,
        or must have the Moderator Role.

        Bot must have Manage Roles permission.

        **Examples:**
        - `[p]role add @Member @Role`
        - `[p]role add 123456789012345678 @Role`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]role add @Member @Role reason`
        - `[p]role add 123456789012345678 @Role reason`
        """
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
        """Remove the mentioned role from mentioned/id member

        You must have Manage Roles permission to use this command,
        or must have the Moderator Role.

        Bot must have Manage Roles permission.

        **Examples:**
        - `[p]role remove @Member @Role`
        - `[p]role remove 123456789012345678 @Role`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]role remove @Member @Role reason`
        - `[p]role remove 123456789012345678 @Role reason`
        """
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
        days: Annotated[int, Optional[int]] = 0,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Bans a member from the server.

        You can also ban from ID to ban regardless whether they're in the server or not.

        In order for this to work, the bot must have Ban Member permissions.
        To use this command you must have Ban Members permission.

        **Examples:**
        - `[p]ban @Member`
        - `[p]ban 123456789012345678`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]ban @Member reason`
        - `[p]ban 123456789012345678 reason`

        You can also specify the number of days worth of messages to delete.

        **Examples:**
        - `[p]ban @Member 7`
        - `[p]ban 123456789012345678 7`
        """
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
        days: Optional[int] = 0,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Bans multiple members from the server.

        This only works through banning via ID.

        In order for this to work, the bot must have Ban Member permissions.
        To use this command you must have Ban Members permission.

        **Examples:**
        - `[p]massban 123456789012345678 123456789012345678`
        - `[p]massban 123456789012345678 123456789012345678 7`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]massban 123456789012345678 123456789012345678 reason`
        - `[p]massban 123456789012345678 123456789012345678 7 reason`
        """
        await mt._mass_ban(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            members=members,
            days=days,
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

        A softban is basically banning the member from the server but then unbanning the member as well.
        This allows you to essentially kick the member while removing their messages.

        In order for this to work, the bot must have Ban Member permissions.
        To use this command you must have Kick Members permissions

        **Examples:**
        - `[p]softban @Member`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]softban @Member reason`
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
        To use this command you must have Ban Members permission.

        **Examples:**
        - `[p]tempban 30d @Member`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]tempban 30d @Member reason`
        """
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
    @commands.bot_has_permissions(manage_channels=True, manage_permissions=True, manage_roles=True)
    @Context.with_type
    async def block(
        self,
        ctx: Context,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Blocks a user from replying message in that channel.

        In order for this to work, the bot must have Manage Channels, Manage Permissions and Manage Roles permissions.
        To use this command you must have Kick Members permission.

        **Examples:**
        - `[p]block @Member`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]block @Member reason`
        """
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
        channel: Optional[discord.TextChannel] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To clone the channel or to nukes the channel (clones and delete).

        In order for this to work, the bot must have Manage Channels permissions.
        To use this command you must have Manage Channels permission.

        **Examples:**
        - `[p]clone`
        - `[p]clone #channel`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]clone reason`
        - `[p]clone #channel reason`
        """
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
        """To kick a member from guild.

        In order for this to work, the bot must have Kick Members permissions.
        To use this command you must have Kick Members permission.

        **Examples:**
        - `[p]kick @Member`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]kick @Member reason`
        """
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
        """To kick a members from guild.

        In order for this to work, the bot must have Kick Members permissions.
        To use this command you must have Kick Members permission.

        **Examples:**
        - `[p]masskick @Member @Member`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]masskick @Member @Member reason`
        """
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
    @commands.bot_has_permissions(manage_channels=True, manage_permissions=True, manage_roles=True)
    @Context.with_type
    async def lock(
        self,
        ctx: Context,
        channel: commands.Greedy[Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To lock the channel.

        In order for this to work, the bot must have Manage Channels, Manage Permissions and Manage Roles permissions.
        To use this command you must have Kick Members permission.

        **Examples:**
        - `[p]lock`
        - `[p]lock #channel`
        - `[p]lock #channel #channel`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]lock reason`
        - `[p]lock #channel reason`
        - `[p]lock #channel #channel reason`
        """
        channel = channel or [ctx.channel]
        for chn in channel:
            if isinstance(chn, discord.abc.Messageable):
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
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True, manage_permissions=True)
    @Context.with_type
    async def unlock(
        self,
        ctx: Context,
        channel: commands.Greedy[Union[discord.abc.Messageable, discord.VoiceChannel, discord.StageChannel]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To unlock the channel.

        In order for this to work, the bot must have Manage Channels, Manage Permissions and Manage Roles permissions.
        To use this command you must have Kick Members permission.

        **Examples:**
        - `[p]unlock`
        - `[p]unlock #channel`
        - `[p]unlock #channel #channel`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]unlock reason`
        - `[p]unlock #channel reason`
        - `[p]unlock #channel #channel reason`
        """
        channel = channel or [ctx.channel]
        for chn in channel:
            if isinstance(chn, discord.abc.Messageable):
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

    @commands.command(name="selfmute", hidden=True)
    @commands.bot_has_permissions(moderate_members=True, manage_roles=True)
    @Context.with_type
    async def self_mute(
        self,
        ctx: Context,
        duration: ShortTime,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To mute yourself.

        In order for this to work, the bot must have Manage Roles permissions.

        **Examples:**
        - `[p]selfmute 1h`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]selfmute 1h reason`
        """
        await mt._self_mute(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=ctx.author,
            reason=reason or f"Selfmute | {ctx.author} ({ctx.author.id}) | No reason given",
            _datetime=duration.dt,
        )

    @commands.command(aliases=["mute", "stfu"])
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
        """To Timeout the member, from chat.

        In order for this to work, the bot must Moderate Members permissions.
        To use this command you must have Moderate Members permission.

        **Examples:**
        - `[p]timeout @member`
        - `[p]timeout @member 1h`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]timeout @member reason`
        - `[p]timeout @member 1h reason`
        """
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
        """To allow a member to sending message in the Text Channels, if muted/timeouted.

        In order for this to work, the bot must have Manage Roles permissions.
        To use this command you must have Manage Roles permission.

        **Examples:**
        - `[p]unmute @member`

        You can also provide a reason for the action.

        **Examples:**
        - `[p]unmute @member reason`
        """
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
    async def clean(
        self,
        ctx: Context,
        num: Optional[int] = 100,
    ):
        """Removes messages that meet a criteria.

        In order to use this command, you must have Manage Messages permissions.

        Note that the bot needs Manage Messages as well. These commands cannot be used in a private message.
        When the command is done doing its work, you will get a message detailing which users got removed and how many messages got removed.

        **Examples:**
        - `[p]clean 10`
        """
        if ctx.invoked_subcommand is None:

            def check(message: discord.Message) -> bool:
                return True

            await mt.do_removal(ctx, num, check)

    @clean.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def embeds(self, ctx: Context, search: Optional[int] = 100):
        """Removes messages that have embeds in them.

        **Examples:**
        - `[p]clean embeds`
        - `[p]clean embeds 10`
        """
        await mt.do_removal(ctx, search, lambda e: len(e.embeds))

    @clean.command(name="regex")
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def _regex(self, ctx: Context, pattern: Optional[str] = None, search: Optional[int] = 100):
        """Removed messages that matches the regex pattern.

        **Examples:**
        - `[p]clean regex`
        - `[p]clean regex .*`
        - `[p]clean regex .* 10`
        """
        pattern = pattern or r".*"

        def check(m: discord.Message) -> bool:
            return bool(re.match(rf"{pattern}", m.content))

        await mt.do_removal(ctx, search, check)

    @clean.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def files(self, ctx: Context, search: Optional[int] = 100):
        """Removes messages that have attachments in them.

        **Examples:**
        - `[p]clean files`
        - `[p]clean files 10`
        """
        await mt.do_removal(ctx, search, lambda e: len(e.attachments))

    @clean.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def images(self, ctx: Context, search: Optional[int] = 100):
        """Removes messages that have embeds or attachments.

        **Examples:**
        - `[p]clean images`
        - `[p]clean images 10`
        """
        await mt.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @clean.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def user(self, ctx: Context, member: discord.Member, search: Optional[int] = 100):
        """Removes all messages by the member.

        **Examples:**
        - `[p]clean user @member`
        - `[p]clean user @member 10`
        """
        await mt.do_removal(ctx, search, lambda e: e.author == member)

    @clean.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def contains(self, ctx: Context, *, substr: str):
        """Removes all messages containing a substring.
        The substring must be at least 3 characters long.

        **Examples:**
        - `[p]clean contains Hello`
        """
        if len(substr) < 3:
            await ctx.send("The substring length must be at least 3 characters.")
        else:
            await mt.do_removal(ctx, 100, lambda e: substr in e.content)

    @clean.command(name="bot", aliases=["bots"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def _bot(self, ctx: Context, prefix: Optional[str] = None, search: Optional[int] = 100):
        """Removes a bot user's messages and messages with their optional prefix.

        **Examples:**
        - `[p]clean bot`
        - `[p]clean bot !`
        """

        def predicate(m: discord.Message):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

        await mt.do_removal(ctx, search, predicate)

    @clean.command(name="emoji", aliases=["emojis"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def _emoji(self, ctx: Context, search: Optional[int] = 100):
        """Removes all messages containing custom emoji.

        **Examples:**
        - `[p]clean emoji`
        - `[p]clean emoji 10`
        """
        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        def predicate(m):
            return custom_emoji.search(m.content)

        await mt.do_removal(ctx, search, predicate)

    @clean.command(name="reactions")
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    async def _reactions(self, ctx: Context, search: Optional[int] = 100):
        """Removes all reactions from messages that have them.

        **Examples:**
        - `[p]clean reactions`
        - `[p]clean reactions 10`
        """

        if search > 2000:
            return await ctx.error(f"Too many messages to search for ({search}/2000)")

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
        channel: Optional[discord.TextChannel] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To set slowmode in the specified channel.

        In order to set slowmode in a channel, you must have the Manage Channels permission.
        Bot requires the Manage Channels permission in order to set slowmode.

        **Examples:**
        - `[p]slowmode 5`
        - `[p]slowmode 5 #general`
        """
        await mt._slowmode(
            guild=ctx.guild,
            command_name=ctx.command.name,
            ctx=ctx,
            destination=ctx.channel,
            seconds=seconds,
            channel=channel or ctx.channel,
            reason=reason,
        )

    @clean.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
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

        **Examples:**
        - `[p]clean custom --user @Member`
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
        parser.add_argument("--embeds", action="store_const", const=lambda m: len(m.embeds))
        parser.add_argument("--files", action="store_const", const=lambda m: len(m.attachments))
        parser.add_argument("--reactions", action="store_const", const=lambda m: len(m.reactions))
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
            predicates.append(lambda m: any(m.content.startswith(s) for s in args.starts))

        if args.ends:
            predicates.append(lambda m: any(m.content.endswith(s) for s in args.ends))

        op = any if args._or else all

        def predicate(m):
            r = op(p(m) for p in predicates)
            return not r if args._not else r

        if args.after and args.search is None:
            args.search = 2000

        if args.search is None:
            args.search = 100

        args.search = max(0, min(2000, args.search))  # clamp from 0-2000
        await mt.do_removal(ctx, args.search, predicate, before=args.before, after=args.after)

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
        """To Unban a member from a guild.

        In order to unban a member, you must have the Ban Members permission for the guild or be a moderator.
        Bot must have Ban Members permission for the guild.

        **Examples:**
        - `[p]unban @Member`

        You can also provide reason for the unban.
        - `[p]unban @Member reason`
        """
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
        commands.has_permissions(kick_members=True),
    )
    @commands.bot_has_permissions(manage_channels=True, manage_permissions=True, manage_roles=True)
    @Context.with_type
    async def unblock(
        self,
        ctx: Context,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Unblocks a user from the text channel.

        In order to unblock a member, you must have the Kick Members permission for the guild or be a moderator.
        Bot must have Manage Channels, Manage Permissions and Manage Roles permission for the guild.

        **Examples:**
        - `[p]unblock @Member`

        You can also provide reason for the unblock.

        **Examples:**
        - `[p]unblock @Member reason`
        """
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
        self,
        ctx: Context,
        member: discord.Member,
        *,
        name: Optional[commands.clean_content] = None,
    ):
        """To change the nickname of the specified member

        In order to change the nickname of a member, you must have the Manage Nicknames permission for the guild or be a moderator.
        Bot must have Manage Nicknames permission for the guild.

        **Examples:**
        - `[p]nick @Member nickname`
        """
        await mt._change_nickname(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            name=name or "Moderated Nickname",
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
        """Voice Moderation.

        > **Note**
        > Voice Moderation also works for the user who is owner of their temporary channels.
        """
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @voice.command(name="mute")
    @commands.check_any(is_mod(), commands.has_guild_permissions(mute_members=True), in_temp_channel())
    @commands.bot_has_guild_permissions(mute_members=True)
    @Context.with_type
    async def voice_mute(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice mute.

        In order to give a member voice mute, you must have the Mute Members permission for the guild or be a moderator.
        Bot must have Mute Members permission for the guild.

        **Examples:**
        - `[p]voice mute @Member`

        You can also provide reason for the voice mute.

        **Examples:**
        - `[p]voice mute @Member reason`
        """
        await mt._voice_mute(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="unmute")
    @commands.check_any(is_mod(), commands.has_guild_permissions(mute_members=True), in_temp_channel())
    @commands.bot_has_guild_permissions(mute_members=True)
    @Context.with_type
    async def voice_unmute(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice unmute.

        In order to give a member voice unmute, you must have the Mute Members permission for the guild or be a moderator.
        Bot must have Mute Members permission for the guild.

        **Examples:**
        - `[p]voice unmute @Member`

        You can also provide reason for the voice unmute.

        **Examples:**
        - `[p]voice unmute @Member reason`
        """
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
        """To give the member voice ban.

        In order to give a member voice ban, you must have the Manage Channels and Manage Permissions permission for the guild or be a moderator.
        Bot must have Manage Channels and Manage Permissions permission for the guild.

        **Examples:**
        - `[p]voice ban @Member`

        You can also provide reason for the voice ban.

        **Examples:**
        - `[p]voice ban @Member reason`
        """
        if member.voice is None:
            return await ctx.error(f"{ctx.author.mention} {member} is not in Voice Channel")
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
        """To give the member voice unban.

        In order to give a member voice unban, you must have the Manage Channels and Manage Permissions permission for the guild or be a moderator.
        Bot must have Manage Channels and Manage Permissions permission for the guild.

        **Examples:**
        - `[p]voice unban @Member`
        """
        if member.voice is None:
            return await ctx.error(f"{ctx.author.mention} {member} is not in Voice Channel")
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
    @commands.check_any(is_mod(), commands.has_guild_permissions(deafen_members=True), in_temp_channel())
    @commands.bot_has_guild_permissions(deafen_members=True)
    @Context.with_type
    async def voice_deafen(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice deafen.

        In order to give a member voice deafen, you must have the Deafen Members permission for the guild or be a moderator.
        Bot must have Deafen Members permission for the guild.

        **Examples:**
        - `[p]voice deafen @Member`
        """
        await mt._voice_deafen(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="undeafen")
    @commands.check_any(is_mod(), commands.has_guild_permissions(deafen_members=True), in_temp_channel())
    @commands.bot_has_guild_permissions(deafen_members=True)
    @Context.with_type
    async def voice_undeafen(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice undeafen.

        In order to give a member voice undeafen, you must have the Deafen Members permission for the guild or be a moderator.
        Bot must have Deafen Members permission for the guild.

        **Examples:**
        - `[p]voice undeafen @Member`
        """
        await mt._voice_undeafen(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="kick")
    @commands.check_any(is_mod(), commands.has_guild_permissions(move_members=True), in_temp_channel())
    @commands.bot_has_guild_permissions(move_members=True)
    @Context.with_type
    async def voice_kick(
        self,
        ctx: Context,
        member: Annotated[discord.abc.Snowflake, MemberID],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice kick.

        In order to give a member voice kick, you must have the Move Members permission for the guild or be a moderator.
        Bot must have Move Members permission for the guild.

        **Examples:**
        - `[p]voice kick @Member`
        """
        await mt._voice_kick(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            member=member,
            reason=reason,
        )

    @voice.command(name="limit")
    @commands.check_any(is_mod(), commands.has_guild_permissions(move_members=True), in_temp_channel())
    @commands.bot_has_guild_permissions(manage_channels=True)
    @Context.with_type
    async def voice_limit(
        self,
        ctx: Context,
        limit: Optional[int] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To set the VC limit.

        In order to set the VC limit, you must have the Move Members permission for the guild or be a moderator.
        Bot must have Manage Channels permission for the guild.

        **Examples:**
        - `[p]voice limit 5`

        **NOTE:** To remove the limit, use the command without any arguments.
        """
        if not ctx.author.voice:
            return await ctx.error(f"{ctx.author.mention} you must be in voice channel to use the command")
        await ctx.author.voice.channel.edit(
            user_limit=limit,  # type: ignore
            reason=f"Action requested by {ctx.author} ({ctx.author.id}) | Reason: {reason}",
        )
        if limit:
            await ctx.send(f"{ctx.author.mention} set limit to **{limit}**")
            return
        await ctx.send(f"{ctx.author.mention} removed the limit from {ctx.author.voice.channel.mention}")

    @voice.command(name="move")
    @commands.check_any(is_mod(), commands.has_guild_permissions(move_members=True))
    @commands.bot_has_guild_permissions(connect=True, move_members=True)
    @Context.with_type
    async def voice_move(
        self,
        ctx: Context,
        member: Annotated[List[discord.abc.Snowflake], commands.Greedy[MemberID]] = None,  # type: ignore
        channel: Optional[discord.VoiceChannel] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To give the member voice move.

        In order to give a member voice move, you must have the Move Members permission for the guild or be a moderator.
        Bot must have Move Members permission for the guild.

        **Examples:**
        - `[p]voice move @Member`
        - `[p]voice move @Member #voice-channel`

        **NOTE:** If you don't specify the channel, it will move the member to the channel you are in.
        """
        if member:
            member: List[discord.Member] = [i async for i in self.bot.resolve_member_ids(ctx.guild, member)]

        def check(m: discord.Member, b: discord.VoiceState, a: discord.VoiceState) -> bool:
            return m.id == ctx.me.id and (b.channel.id != a.channel.id)

        if channel is None:
            if voicestate := ctx.author.voice:
                if not ctx.guild.me.voice:
                    await voicestate.channel.connect(cls=wavelink.Player)
                    # await voicestate.channel.connect()
                else:
                    await ctx.guild.me.edit(voice_channel=voicestate.channel)
                if not member:
                    member = voicestate.channel.members
            else:
                return await ctx.error(
                    f"{ctx.author.mention} you must specify the the channel or must be in the voice channel to use this command"
                )

            try:
                await ctx.send(f"{ctx.author.mention} move the bot to other channel as to move other users")
                _, _, a = await ctx.wait_for("voice_state_update", timeout=60, check=check)
            except asyncio.TimeoutError:
                return await ctx.error(f"{ctx.author.mention} you ran out time")

            a: discord.VoiceState = a

            for mem in member:
                await mem.edit(
                    voice_channel=a.channel,
                    reason=reason,
                )
            return await ctx.send(f"{ctx.author.mention} moved **{len(member)}** members")

        if not member:
            member = channel.members

        for mem in member:
            await mem.edit(
                voice_channel=channel,
                reason=reason,
            )
        return await ctx.send(f"{ctx.author.mention} moved {len(member)} members to {channel.mention}")

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
        """To delete the emoji.

        In order to delete the emoji, you must have the Manage Emojis permission for the guild or be a moderator.
        Bot must have Manage Emojis permission for the guild.

        **Examples:**
        - `[p]emoji delete [emoji]`
        """
        if not emoji:
            return await ctx.error(f"{ctx.author.mention} you must specify the emoji to delete")
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
        """To add the emoji.

        In order to add the emoji, you must have the Manage Emojis permission for the guild or be a moderator.
        Bot must have Manage Emojis permission for the guild.

        **Examples:**
        - `[p]emoji add [emoji]`
        """
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
        name: Optional[commands.clean_content] = "emoji",  # type: ignore
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To add the emoji from url.

        In order to add the emoji, you must have the Manage Emojis permission for the guild or be a moderator.
        Bot must have Manage Emojis permission for the guild.

        **Examples:**
        - `[p]emoji addurl url`
        - `[p]emoji addurl url name`

        **Note:**
        - The name must be less than 32 characters.
        """
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
        """To rename the emoji.

        In order to rename the emoji, you must have the Manage Emojis permission for the guild or be a moderator.
        Bot must have Manage Emojis permission for the guild.

        **Examples:**
        - `[p]emoji rename emoji name`

        **Note:**
        - The name must be less than 32 characters.
        """
        await mt._emoji_rename(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            reason=reason,
            emoji=emoji,
            name=name,
        )

    @commands.group()
    @commands.check_any(is_mod(), commands.has_permissions(manage_emojis=True))
    @Context.with_type
    async def sticker(self, ctx: Context):
        """Sticker Management of the server."""
        if not ctx.invoked_subcommand:
            await self.bot.invoke_help_command(ctx)

    @sticker.command(name="add")
    async def sticker_add(self, ctx: Context, emoji: str, *, description: str):
        """To add sticker"""
        if not ctx.message.stickers:
            return await ctx.send(f"{ctx.author.mention} You did not provide any sticker")

        await mt._sticker_add(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            emoji=emoji,
            sticker=ctx.message.stickers[0],
            description=description,
            reason=f"Action requested by: {ctx.author} {ctx.author.id}",
        )

    @sticker.command(name="delete")
    async def sticker_delete(
        self,
        ctx: Context,
        sticker: Optional[discord.GuildSticker] = None,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To delete sticker"""
        if not ctx.message.stickers:
            return await ctx.send(f"{ctx.author.mention} You did not provide any sticker")
        sticker = sticker or ctx.message.stickers[0]
        await mt._sticker_delete(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            reason=reason,
            sticker=sticker,
        )

    @sticker.command(name="addurl")
    async def sticker_addurl(
        self,
        ctx: Context,
        url: str,
        name: str,
        emoji: str,
        description: str,
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """To add sticker from url"""
        await mt._sticker_addurl(
            guild=ctx.guild,
            command_name=ctx.command.qualified_name,
            ctx=ctx,
            destination=ctx.channel,
            reason=reason,
            url=url,
            name=name,
            emoji=emoji,
            description=description,
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
        target: Union[discord.Member, discord.TextChannel, discord.VoiceChannel, discord.Role],
        *,
        reason: Annotated[Optional[str], ActionReason] = None,
    ):
        """Why to learn the commands? This is all in one mod command.

        **Examples:**
        - `[p]mod @member`
        - `[p]mod #channel`
        - `[p]mod @role`
        """

        def check_msg(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        if not target:
            return await ctx.send_help(ctx.command)

        guild = ctx.guild

        if isinstance(target, discord.Member):
            member_embed = MEMBER_EMBED.copy()
            member_embed.description = (
                f"Reason: {reason or 'no reason provided'}\n" f"Action will be performed on: {target} ({target.id})"
            )
            member_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon is not None:
                member_embed.set_thumbnail(url=target.display_avatar.url)

            msg = await ctx.send(embed=member_embed)
            await ctx.bulk_add_reactions(msg, *mt.MEMBER_REACTION)

            def check(reaction: discord.Reaction, user: discord.User) -> bool:
                return str(reaction.emoji) in mt.MEMBER_REACTION and user == ctx.author and reaction.message.id == msg.id

            try:
                reaction, _ = await ctx.wait_for("reaction_add", timeout=60.0, check=check)
                reaction: discord.Reaction = reaction
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            func = mt.MEMBER_REACTION[str(reaction.emoji)]

            if str(reaction.emoji) in {
                "\N{DOWNWARDS BLACK ARROW}",
                "\N{UPWARDS BLACK ARROW}",
            }:
                temp: discord.Message = await ctx.send(f"{ctx.author.mention} Enter the Role, [ID, NAME, MENTION]")
                try:
                    m: discord.Message = await ctx.wait_for("message", timeout=30, check=check_msg)
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
                return await msg.delete(delay=0)

            if str(reaction.emoji) == "\N{LOWER LEFT FOUNTAIN PEN}":
                await ctx.send(
                    f"{ctx.author.mention} Enter the Nickname, [Not more than 32 char]",
                    delete_after=30,
                )
                try:
                    m: discord.Message = await ctx.wait_for("message", timeout=30, check=check_msg)
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
                return await msg.delete(delay=0)

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
            tc_embed.description = (
                f"Reason: {reason or 'no reason provided'}\n" f"Action will be performed on: {target} ({target.id})"
            )
            tc_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon:
                tc_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg: discord.Message = await ctx.send(embed=tc_embed)
            await ctx.bulk_add_reactions(msg, *mt.TEXT_REACTION)

            def check(reaction: discord.Reaction, user: discord.User) -> bool:
                return str(reaction.emoji) in mt.TEXT_REACTION and user == ctx.author and reaction.message.id == msg.id

            def check_msg(m: discord.Message) -> bool:
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                reaction, _ = await ctx.wait_for("reaction_add", timeout=60.0, check=check)
                reaction: discord.Reaction = reaction
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
                    m: discord.Message = await ctx.wait_for("message", timeout=60, check=check_msg)
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
                return await msg.delete(delay=0)

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
            vc_embed.description = (
                f"Reason: {reason or 'no reason provided'}\n" f"Action will be performed on: {target} ({target.id})"
            )
            vc_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon:
                vc_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg: discord.Message = await ctx.send(embed=vc_embed)
            await ctx.bulk_add_reactions(msg, *mt.VC_REACTION)

            def check_reaction_vc(reaction: discord.Reaction, user: discord.User) -> bool:
                return str(reaction.emoji) in mt.VC_REACTION and user == ctx.author and reaction.message.id == msg.id

            try:
                reaction, _ = await ctx.wait_for("reaction_add", timeout=60.0, check=check_reaction_vc)
                reaction: discord.Reaction = reaction
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            func = mt.VC_REACTION[str(reaction.emoji)]

            if str(reaction.emoji) == "\N{LOWER LEFT FOUNTAIN PEN}":
                await ctx.send(f"{ctx.author.mention} Enter the Channel Name", delete_after=60)
                try:
                    m: discord.Message = await ctx.wait_for("message", timeout=60, check=check_msg)
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
                return await msg.delete(delay=0)

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
            role_embed.description = (
                f"Reason: {reason or 'no reason provided'}\n" f"Action will be performed on: {target} ({target.id})"
            )
            role_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if ctx.guild.icon:
                role_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg: discord.Message = await ctx.send(embed=role_embed)
            await ctx.bulk_add_reactions(msg, *mt.ROLE_REACTION)

            def check_reaction_role(reaction: discord.Reaction, user: discord.User):
                return str(reaction.emoji) in mt.ROLE_REACTION and user == ctx.author and reaction.message.id == msg.id

            try:
                reaction, _ = await ctx.wait_for("reaction_add", timeout=60.0, check=check_reaction_role)
                reaction: discord.Reaction = reaction
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            func = mt.ROLE_REACTION[str(reaction.emoji)]

            if str(reaction.emoji) == "\N{RAINBOW}":
                await ctx.send(
                    f"{ctx.author.mention} Enter the Colour, in whole number",
                    delete_after=60,
                )
                try:
                    m: discord.Message = await ctx.wait_for("message", timeout=60, check=check_msg)
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
                return await msg.delete(delay=0)

            if str(reaction.emoji) == "\N{LOWER LEFT FOUNTAIN PEN}":
                await ctx.send(f"{ctx.author.mention} Enter the Role Name", delete_after=60)
                try:
                    m: discord.Message = await ctx.wait_for("message", timeout=60, check=check_msg)
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
                return await msg.delete(delay=0)

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
