from __future__ import annotations
from cogs.mod.flags import purgeFlag, warnFlag
from cogs.mod import method as mt

from discord.ext import commands, tasks
import discord
import typing
import re
import asyncio

from core import Parrot, Context, Cog

from utilities.checks import is_mod
from utilities.converters import BannedMember, reason_convert
from utilities.database import parrot_db
from utilities.time import ShortTime
from utilities.regex import LINKS_NO_PROTOCOLS
from utilities.infraction import delete_many_warn, custom_delete_warn, warn, show_warn
from datetime import datetime

from cogs.meta.robopage import TextPageSource, RoboPages
from typing import Optional

collection = parrot_db["server_config"]
mute_collection = parrot_db["mute"]
ban_collection = parrot_db["banned_members"]


class Mod(Cog):
    """A simple moderator's tool for managing the server."""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.unban_task.start()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="moderator", id=892424227007918121)

    async def log(self, ctx, cmd, performed_on, reason):
        """A simple and nerdy Logging System"""
        data = await collection.find_one({"_id": ctx.guild.id})
        if not data["action_log"]:
            return
        if not data:
            return
        target = "Can' determined"
        if type(performed_on) is not list:
            if type(performed_on) in (
                discord.Member,
                discord.User,
            ):
                target = f"{performed_on.name}#{performed_on.discriminator}"
            elif type(target) in (
                discord.TextChannel,
                discord.VoiceChannel,
                discord.StageChannel,
                discord.Role,
                discord.Emoji,
            ):
                target = f"{performed_on.name} (ID: {performed_on.id})"
        elif type(target) is list:
            target = ""
            for temp in performed_on:
                if type(temp) is discord.Member:
                    target = target + f"{temp.name}#{temp.discriminator}, "
                elif type(target) is (
                    discord.TextChannel,
                    discord.VoiceChannel,
                    discord.StageChannel,
                    discord.Role,
                    discord.Emoji,
                ):
                    target = target + f"{temp.name} (ID: {temp.id}), "
        target = str(performed_on)
        embed = discord.Embed(
            description=f"**Command Used:** {cmd}\n"
            f"**Used On:** {target}\n"
            f"**Reason:** {reason if reason else 'No Reason Provided'}",
            timestamp=datetime.utcnow(),
            colour=ctx.author.color,
        )

        embed.set_thumbnail(
            url=f"{performed_on.display_avatar.url if type(performed_on) is discord.Member else ctx.guild.icon.url}"
        )
        embed.set_author(
            name=f"{ctx.author} (ID:{ctx.author.id})",
            icon_url=ctx.author.display_avatar.url,
            url=f"https://discord.com/users/{ctx.author.id}",
        )
        embed.set_footer(text=f"{ctx.guild.name}")
        channel = self.bot.get_channel(data["action_log"])
        if channel:
            return await self.bot.get_channel(data["action_log"]).send(embed=embed)

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
        reason: reason_convert = None,
    ):
        """Gives a role to the all bots."""
        await mt._add_roles_bot(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, operator, role, reason
        )
        await self.log(ctx, ctx.command.qualified_name, "Bots", f"{reason}")

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
        reason: reason_convert = None,
    ):
        """Gives a role to the all humans."""
        await mt._add_roles_humans(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, operator, role, reason
        )
        await self.log(ctx, ctx.command.qualified_name, "Humans", f"{reason}")

    @role.command(name="add", aliases=["arole", "giverole", "grole"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def add_role(
        self,
        ctx: Context,
        member: discord.Member,
        role: discord.Role,
        *,
        reason: reason_convert = None,
    ):
        """Gives a role to the specified member(s)."""
        await mt._add_roles(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, role, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @role.command(name="remove", aliases=["urole", "removerole", "rrole"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def remove_role(
        self,
        ctx: Context,
        member: discord.Member,
        role: discord.Role,
        *,
        reason: reason_convert = None,
    ):
        """Remove the mentioned role from mentioned/id member"""
        await mt._remove_roles(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, role, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @commands.command(aliases=["hackban"])
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def ban(
        self,
        ctx: Context,
        member: discord.User,
        days: typing.Optional[int] = None,
        *,
        reason: reason_convert = None,
    ):
        """To ban a member from guild."""
        if days is None:
            days = 0
        await mt._ban(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, days, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @commands.command(name="massban")
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def mass_ban(
        self,
        ctx: Context,
        members: commands.Greedy[discord.User],
        days: typing.Optional[int] = None,
        *,
        reason: reason_convert = None,
    ):
        """To Mass ban list of members, from the guild"""
        if days is None:
            days = 0
        await mt._mass_ban(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, members, days, reason
        )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            f'{", ".join([str(member) for member in members])}',
            f"{reason}",
        )

    @commands.command(aliases=["softkill"])
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def softban(
        self,
        ctx: Context,
        member: commands.Greedy[discord.Member],
        *,
        reason: reason_convert = None,
    ):
        """To Ban a member from a guild then immediately unban"""
        await mt._softban(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            f'{", ".join([str(member) for member in member])}',
            f"{reason}",
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def tempban(
        self,
        ctx: Context,
        member: commands.Greedy[discord.Member],
        duration: ShortTime,
        *,
        reason: reason_convert = None,
    ):
        """To Ban a member from a guild then immediately unban"""
        await mt._tempban(
            ctx.guild,
            ctx.command.name,
            ctx.author,
            ctx.channel,
            member,
            duration,
            reason,
        )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            f'{", ".join([str(member) for member in member])}',
            f"{reason}",
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
        member: commands.Greedy[discord.Member],
        *,
        reason: reason_convert = None,
    ):
        """Blocks a user from replying message in that channel."""
        await mt._block(
            ctx.guild,
            ctx.command.name,
            ctx.author,
            ctx.channel,
            ctx.channel,
            member,
            reason,
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @commands.command(aliases=["nuke"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_channels=True))
    @commands.bot_has_permissions(manage_channels=True)
    @Context.with_type
    async def clone(
        self,
        ctx: Context,
        channel: discord.TextChannel = None,
        *,
        reason: reason_convert = None,
    ):
        """To clone the channel or to nukes the channel (clones and delete)."""
        await mt._clone(
            ctx.guild,
            ctx.command.name,
            ctx.author,
            ctx.channel,
            channel or ctx.channel,
            reason,
        )
        await self.log(
            ctx, ctx.command.qualified_name, channel or ctx.channel, f"{reason}"
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(kick_members=True)
    @Context.with_type
    async def kick(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To kick a member from guild."""
        await mt._kick(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @commands.command(name="masskick")
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(kick_members=True)
    @Context.with_type
    async def mass_kick(
        self,
        ctx: Context,
        members: commands.Greedy[discord.Member],
        *,
        reason: reason_convert = None,
    ):
        """To kick a member from guild."""
        await mt._mass_kick(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, members, reason
        )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            f'{", ".join([str(member) for member in members])}',
            f"{reason}",
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
            typing.Union[
                discord.TextChannel, discord.VoiceChannel, discord.StageChannel
            ]
        ],
        *,
        reason: reason_convert = None,
    ):
        """To lock the channel"""
        for chn in channel:
            if type(chn) is discord.TextChannel:
                await mt._text_lock(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, chn
                )
            elif type(chn) in (discord.VoiceChannel, discord.StageChannel):
                await mt._vc_lock(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, chn
                )
            else:
                pass

        await mt._text_lock(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, ctx.channel
        )
        await self.log(
            ctx, ctx.command.qualified_name, channel if channel else ctx.channel, reason
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
            typing.Union[
                discord.TextChannel, discord.VoiceChannel, discord.StageChannel
            ]
        ],
        *,
        reason: reason_convert = None,
    ):
        """To unlock the channel"""
        for chn in channel:
            if type(chn) is discord.TextChannel:
                await mt._text_unlock(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, chn
                )
                return
            if type(chn) in (discord.VoiceChannel, discord.StageChannel):
                await mt._vc_unlock(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, chn
                )
                return

        await mt._text_unlock(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, ctx.channel
        )
        await self.log(
            ctx, ctx.command.qualified_name, channel if channel else ctx.channel, reason
        )

    @commands.command(aliases=["mute"])
    @commands.bot_has_permissions(moderate_members=True)
    @commands.check_any(is_mod(), commands.has_permissions(moderate_members=True))
    @Context.with_type
    async def timeout(
        self,
        ctx: Context,
        member: discord.Member,
        duration: typing.Optional[ShortTime] = None,
        *,
        reason: reason_convert = None,
    ):
        """To Timeout the member, from chat."""
        seconds = duration
        if seconds:
            await mt._timeout(
                ctx.guild,
                ctx.command.qualified_name,
                ctx.author,
                ctx.channel,
                member,
                duration.dt,
                reason,
            )
        else:
            await mt._mute(
                ctx.guild,
                ctx.command.qualified_name,
                ctx.author,
                ctx.channel,
                member,
                reason,
            )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            member,
            f'{reason} | Till {"<t:" + str(int(seconds.dt.timestamp())) + ">" if seconds else "end"}',
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    @Context.with_type
    async def unmute(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To allow a member to sending message in the Text Channels, if muted/timeouted."""
        await mt._unmute(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @commands.command(aliases=["purge"])
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True, manage_messages=True)
    @Context.with_type
    async def clear(self, ctx, num: int, *, flags: purgeFlag):
        """To delete bulk message"""
        await ctx.message.delete(delay=0)
        if num > 100 or num < 0:
            return await ctx.send("Invalid amount. Maximum is 100.")

        def check(m: discord.Message):
            if flags.member:
                return m.author.id == flags.member.id
            if flags.regex:
                return re.seach(rf"{flags.regex}", m.content)
            if flags.links:
                return LINKS_NO_PROTOCOLS.search(m.content)
            if flags.attachment:
                return m.attachments != []
            return True

        deleted = await ctx.channel.purge(limit=num, check=check)
        await ctx.send(
            f"{ctx.author.mention} deleted **{len(deleted)}/{num}** possible messages for you.",
            delete_after=10,
        )

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
        reason: reason_convert = None,
    ):
        """To set slowmode in the specified channel"""
        await mt._slowmode(
            ctx.guild,
            ctx.command.name,
            ctx.author,
            ctx.channel,
            seconds,
            channel or ctx.channel,
            reason,
        )
        await self.log(
            ctx, ctx.command.qualified_name, channel, f"{reason} | For {seconds}s"
        )

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    @Context.with_type
    async def unban(
        self, ctx: Context, member: BannedMember, *, reason: reason_convert = None
    ):
        """To Unban a member from a guild"""
        await mt._unban(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

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
        member: commands.Greedy[discord.Member],
        *,
        reason: reason_convert = None,
    ):
        """Unblocks a user from the text channel"""
        await mt._unblock(
            ctx.guild,
            ctx.command.name,
            ctx.author,
            ctx.channel,
            ctx.channel,
            member,
            reason,
        )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            f'{", ".join([str(member) for member in member])}',
            f"{reason}",
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
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, name
        )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            member,
            f"Action Requested by {ctx.author.name} ({ctx.author.id})",
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
    @commands.check_any(is_mod(), commands.has_guild_permissions(mute_members=True))
    @commands.bot_has_guild_permissions(mute_members=True)
    @Context.with_type
    async def voice_mute(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To give the member voice mute"""
        await mt._voice_mute(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @voice.command(name="unmute")
    @commands.check_any(is_mod(), commands.has_guild_permissions(mute_members=True))
    @commands.bot_has_guild_permissions(mute_members=True)
    @Context.with_type
    async def voice_unmute(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To give the member voice unmute"""
        await mt._voice_unmute(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @voice.command(name="ban")
    @commands.check_any(
        is_mod(),
        commands.has_guild_permissions(manage_channels=True, manage_permissions=True),
    )
    @commands.bot_has_guild_permissions(manage_channels=True, manage_permissions=True)
    @Context.with_type
    async def voice_ban(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To give the member voice ban"""
        await mt._voice_ban(
            ctx.guild,
            ctx.command.name,
            ctx.author,
            ctx.channel,
            member,
            ctx.author.voice.channel or member.voice.channel,
            reason,
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @voice.command(name="unban")
    @commands.check_any(
        is_mod(),
        commands.has_guild_permissions(manage_channels=True, manage_permissions=True),
    )
    @commands.bot_has_guild_permissions(manage_channels=True, manage_permissions=True)
    @Context.with_type
    async def voice_unban(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To give the member voice unban"""
        await mt._voice_unban(
            ctx.guild,
            ctx.command.name,
            ctx.author,
            ctx.channel,
            member,
            ctx.author.voice.channel or member.voice.channel,
            reason,
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @voice.command(name="deafen")
    @commands.check_any(is_mod(), commands.has_guild_permissions(deafen_members=True))
    @commands.bot_has_guild_permissions(deafen_members=True)
    @Context.with_type
    async def voice_deafen(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To give the member voice deafen"""
        await mt._voice_deafen(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @voice.command(name="undeafen")
    @commands.check_any(is_mod(), commands.has_guild_permissions(deafen_members=True))
    @commands.bot_has_guild_permissions(deafen_members=True)
    @Context.with_type
    async def voice_undeafen(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To give the member voice undeafen"""
        await mt._voice_undeafen(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @voice.command(name="kick")
    @commands.check_any(is_mod(), commands.has_guild_permissions(move_members=True))
    @commands.bot_has_guild_permissions(move_members=True)
    @Context.with_type
    async def voice_kick(
        self, ctx: Context, member: discord.Member, *, reason: reason_convert = None
    ):
        """To give the member voice kick"""
        await mt._voice_kick(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, member, reason
        )
        await self.log(ctx, ctx.command.qualified_name, member, f"{reason}")

    @voice.command(name="move")
    @commands.check_any(is_mod(), commands.has_guild_permissions(move_members=True))
    @commands.bot_has_guild_permissions(connect=True, move_members=True)
    @Context.with_type
    async def voice_move(
        self,
        ctx: Context,
        member: commands.Greedy[discord.Member],
        channel: typing.Union[discord.VoiceChannel, None],
        *,
        reason: reason_convert = None,
    ):
        """To give the member voice move"""

        def check(m, b, a):
            return m.id == ctx.me.id and (b.channel.id != a.channel.id)

        if channel is None:
            if voicestate := ctx.author.voice:
                await voicestate.channel.connet()
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
                        voice_channel=a,
                        reason=f"Action Requested by {ctx.author.name} ({ctx.author.id}) | Reason: {reason}",
                    )
        if channel:
            if not member:
                member = channel.members

            for mem in member:
                await mem.edit(
                    voice_channel=a,
                    reason=f"Action Requested by {ctx.author.name} ({ctx.author.id}) | Reason: {reason}",
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
        reason: reason_convert = None,
    ):
        """To delete the emoji"""
        if not emoji:
            return
        await mt._emoji_delete(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, emoji, reason
        )
        await self.log(
            ctx,
            ctx.command.qualified_name,
            [emoji.name for emoji in emoji],
            f"{reason}",
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
        reason: reason_convert = None,
    ):
        """To add the emoji"""
        if not emoji:
            return
        await mt._emoji_add(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, emoji, reason
        )
        await self.log(ctx, ctx.command.qualified_name, emoji, f"{reason}")

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
        reason: reason_convert = None,
    ):
        """To add the emoji from url"""
        await mt._emoji_addurl(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, url, name, reason
        )
        await self.log(ctx, ctx.command.qualified_name, "Emoji", f"{reason}")

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
        reason: reason_convert = None,
    ):
        """To rename the emoji"""
        await mt._emoji_rename(
            ctx.guild, ctx.command.name, ctx.author, ctx.channel, emoji, name, reason
        )
        await self.log(ctx, ctx.command.qualified_name, emoji, f"{reason}")

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
        target: typing.Union[
            discord.Member, discord.TextChannel, discord.VoiceChannel, discord.Role
        ],
        *,
        reason: reason_convert = None,
    ):
        """Why to learn the commands. This is all in one mod command."""

        def check_msg(m):
            return m.author == ctx.author and m.channel == ctx.channel

        if not target:
            return await ctx.send_help(ctx.command)
        guild = ctx.guild
        if isinstance(target, discord.Member):
            member_embed = discord.Embed(
                title="Mod Menu",
                description=":hammer: Ban\n"
                ":boot: Kick\n"
                ":zipper_mouth: Mute\n"
                ":grin: Unmute\n"
                ":x: Block\n"
                ":o: Unblock\n"
                ":arrow_up: Add role\n"
                ":arrow_down: Remove role\n"
                ":pen_fountain: Change Nickname",
                timestamp=datetime.utcnow(),
                color=ctx.author.color,
            )
            member_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon:
                member_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg = await ctx.send(embed=member_embed)
            for reaction in mt.MEMBER_REACTION:
                await msg.add_reaction(reaction)

            def check(reaction, user):
                return (
                    str(reaction.emoji) in mt.MEMBER_REACTION
                    and user == ctx.author
                    and reaction.message.id == msg.id
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            if str(reaction.emoji) == mt.MEMBER_REACTION[0]:
                await mt._ban(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    0,
                    reason,
                )
                await self.log(ctx, "ban", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[1]:
                await mt._kick(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, target, reason
                )
                await self.log(ctx, "kick", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[2]:
                await mt._mute(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    None,
                    reason,
                )
                await self.log(ctx, "mute", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[3]:
                await mt._unmute(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, target, reason
                )
                await self.log(ctx, "unmute", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[4]:
                await mt._block(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    ctx.channel,
                    [target],
                    reason,
                )
                await self.log(ctx, "block", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[5]:
                await mt._unblock(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    ctx.channel,
                    [target],
                    reason,
                )
                await self.log(ctx, "unblock", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[6]:
                temp = await ctx.send(
                    f"{ctx.author.mention} Enter the Role, [ID, NAME, MENTION]"
                )
                try:
                    m = await self.bot.wait_for("message", timeout=30, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                role = await commands.RoleConverter().convert(ctx, m.content)
                await temp.delete()
                await mt._add_roles(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    role,
                    reason,
                )
                await self.log(ctx, "role", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[7]:
                temp = await ctx.send(
                    f"{ctx.author.mention} Enter the Role, [ID, NAME, MENTION]"
                )
                try:
                    m = await self.bot.wait_for("message", timeout=30, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                role = await commands.RoleConverter().convert(ctx, m.content)
                await temp.delete()
                await mt._remove_roles(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    role,
                    reason,
                )
                await self.log(ctx, "unrole", target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[8]:
                await ctx.send(
                    f"{ctx.author.mention} Enter the Nickname, [Not more than 32 char]",
                    delete_after=30,
                )
                try:
                    m = await self.bot.wait_for("message", timeout=30, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)

                await mt._change_nickname(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    (m.content)[:32:],
                )
                await self.log(ctx, "nickname changed", target, reason)

        if isinstance(target, discord.TextChannel):
            tc_embed = discord.Embed(
                title="Mod Menu",
                description=":lock: Lock\n"
                ":unlock: Unlock\n"
                ":pencil: Change Topic\n"
                ":pen_fountain: Change Name",
                timestamp=datetime.utcnow(),
                color=ctx.author.color,
            )
            tc_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon:
                tc_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg = await ctx.send(embed=tc_embed)
            for reaction in mt.TEXT_REACTION:
                await msg.add_reaction(reaction)

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

            if str(reaction.emoji) == mt.TEXT_REACTION[0]:
                await mt._text_lock(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, target
                )
                await self.log(ctx, "Text lock", target, reason)

            if str(reaction.emoji) == mt.TEXT_REACTION[1]:
                await mt._text_unlock(
                    ctx.guild, ctx.command.name, ctx.author, ctx.channel, target
                )
                await self.log(ctx, "Text unlock", target, reason)

            if str(reaction.emoji) == mt.TEXT_REACTION[2]:
                await ctx.send(
                    f"{ctx.author.mention} Enter the Channel Topic", delete_after=60
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                await mt._change_channel_topic(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    m.content,
                )
                await self.log(ctx, "Text topic changed", target, reason)

            if str(reaction.emoji) == mt.TEXT_REACTION[3]:
                await ctx.send(
                    f"{ctx.author.mention} Enter the Channel Name", delete_after=60
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                await mt._change_channel_name(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    ctx.channel,
                    m.content,
                )
                await self.log(ctx, "Text name changeded", target, reason)

        if type(target) in (
            discord.VoiceChannel,
            discord.StageChannel,
        ):
            vc_embed = discord.Embed(
                title="Mod Menu",
                description=":lock: Lock\n"
                ":unlock: Unlock\n"
                ":pen_fountain: Change Name",
                timestamp=datetime.utcnow(),
                color=ctx.author.color,
            )
            vc_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if guild.icon:
                vc_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg = await ctx.send(embed=vc_embed)
            for reaction in mt.VC_REACTION:
                await msg.add_reaction(reaction)

            def check_reaction_vc(reaction, user):
                return (
                    str(reaction.emoji) in mt.VC_REACTION
                    and user == ctx.author
                    and reaction.message.id == msg.id
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=check_reaction_vc
                )
            except asyncio.TimeoutError:
                return await msg.delete(delay=0)

            if str(reaction.emoji) == mt.VC_REACTION[0]:
                await mt._vc_lock(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    ctx.author.voice.channel or target,
                )
                await self.log(ctx, "VC Lock", target, reason)

            if str(reaction.emoji) == mt.VC_REACTION[1]:
                await mt._vc_unlock(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    ctx.author.voice.channel or target,
                )
                await self.log(ctx, "VC Unlock", target, reason)

            if str(reaction.emoji) == mt.VC_REACTION[2]:
                await ctx.send(
                    f"{ctx.author.mention} Enter the Channel Name", delete_after=60
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                await mt._change_channel_name(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    ctx.channel,
                    m.content,
                )
                await self.log(ctx, "VC name changed", target, reason)

        if isinstance(target, discord.Role):
            role_embed = discord.Embed(
                title="Mod Menu",
                description=":lock: Hoist\n"
                ":unlock: De-Hoist\n"
                ":rainbow: Change Colour\n"
                ":pen_fountain: Change Name",
                timestamp=datetime.utcnow(),
                color=ctx.author.color,
            )
            role_embed.set_footer(text=f"{ctx.author.guild.name} mod tool")
            if ctx.guild.icon:
                role_embed.set_thumbnail(url=ctx.guild.icon.url)
            msg = await ctx.send(embed=role_embed)
            for reaction in mt.ROLE_REACTION:
                await msg.add_reaction(reaction)

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

            if str(reaction.emoji) == mt.ROLE_REACTION[0]:
                await mt._role_hoist(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    True,
                    reason,
                )
                await self.log(ctx, "Role Hoist", target, reason)

            if str(reaction.emoji) == mt.ROLE_REACTION[1]:
                await mt._role_hoist(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    False,
                    reason,
                )
                await self.log(ctx, "Role Dehoist", target, reason)

            if str(reaction.emoji) == mt.ROLE_REACTION[2]:
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
                except Exception:
                    await ctx.send(f"{ctx.author.mention} invalid color")
                else:
                    await mt._change_role_color(
                        ctx.guild,
                        ctx.command.name,
                        ctx.author,
                        ctx.channel,
                        target,
                        color,
                        reason,
                    )
                    await self.log(ctx, "Role color", target, reason)

            if str(reaction.emoji) == mt.ROLE_REACTION[3]:
                await ctx.send(
                    f"{ctx.author.mention} Enter the Role Name", delete_after=60
                )
                try:
                    m = await self.bot.wait_for("message", timeout=60, check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete(delay=0)
                await mt._change_role_name(
                    ctx.guild,
                    ctx.command.name,
                    ctx.author,
                    ctx.channel,
                    target,
                    m.content,
                    reason,
                )
                await self.log(ctx, "Role name changed", target, reason)

        return await msg.delete(delay=0)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    async def warn(self, ctx: Context, user: discord.Member, *, reason: reason_convert):
        """To warn the user"""
        try:
            await user.send(
                f"{user.mention} you are being in **{ctx.guild.name}** warned for: **{reason}**"
            )
        except discord.Forbidden:
            pass
        finally:
            _ = await warn(
                ctx.guild,
                user,
                reason,
                moderator=ctx.author,
                message=ctx.message,
                at=ctx.message.created_at.timestamp(),
            )
            await ctx.send(f"{ctx.author.mention} **{user}** warned")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.check_any(is_mod(), commands.has_permissions(manage_messages=True))
    async def delwarn(self, ctx: Context, warn_id: Optional[int] = None):
        """To delete warn of user by ID"""
        if not warn_id:
            return
        await custom_delete_warn(ctx.guild, warn_id=warn_id)
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

        await delete_many_warn(ctx.guild, **payload)
        await ctx.send(
            f"{ctx.author.mention} deleted all warns matching: `{'`, `'.join(payload)}`"
        )

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
        data = await show_warn(ctx.guild, **payload)
        page = RoboPages(TextPageSource(data, max_size=1000), ctx=ctx)
        await page.start()

    @tasks.loop(seconds=2)
    async def unban_task(self):
        await self.bot.wait_until_ready()
        async for data in ban_collection.find(
            {"duration": {"$lte": datetime.utcnow().timestamp()}}
        ):
            guild = self.bot.get_guild(data["guild_id"])
            if not guild:
                await ban_collection.delete_one({"_id": data["_id"]})
            else:
                try:
                    await guild.unban(
                        discord.Object(id=data["member_id"]),
                        reason="Ban duration expires!",
                    )
                except discord.NotFound:
                    pass
                finally:
                    await ban_collection.delete_one({"_id": data["_id"]})
