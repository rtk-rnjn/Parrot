from discord.ext import commands
import discord, typing, re, asyncio
from core import Parrot, Context, Cog
from utilities.checks import is_mod
from utilities.converters import reason_convert, convert_time
from cogs.mod import method as mt
from database.server_config import collection, guild_join
from datetime import datetime


class mod(Cog,
          name="moderator",
          description="A simple moderator's tool for managing the server."):
    """A simple moderator's tool for managing the server."""
    def __init__(self, bot: Parrot):
        self.bot = bot

    async def log(self, ctx, cmd, performed_on, reason):
        if not collection.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)

        data = collection.find_one({'_id': ctx.guild.id})

        embed = discord.Embed(title=f"Mod command, `{cmd}` Used",
                              description=f"```\nREASON: {reason}\n```",
                              timestamp=datetime.utcnow())
        embed.add_field(name="Action Performed by:",
                        value=f"{ctx.author.mention}",
                        inline=True)
        embed.add_field(name="Action Performed on:",
                        value=f"{performed_on}",
                        inline=True)
        embed.set_footer(text=f"{ctx.guild.name}")
        channel = self.bot.get_channel(data['action_log'])
        if channel:
            return await self.bot.get_channel(data['action_log']
                                              ).send(embed=embed)

    @commands.group()
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self, ctx: Context):
        """Role Management of the server."""
        pass

    @role.command(name="bots")
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    async def add_role_bots(self,
                            ctx: Context,
                            operator: str,
                            role: discord.Role,
                            *,
                            reason: reason_convert = None):
        """Gives a role to the all bots."""
        await mt._add_roles_bot(ctx.guild, ctx.command.name, ctx.channel,
                                operator, role, reason)
        await self.log(ctx, 'Role', 'Bots', f'{reason}')

    @role.command(name="humans")
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    async def add_role_human(self,
                             ctx: Context,
                             operator: str,
                             role: discord.Role,
                             *,
                             reason: reason_convert = None):
        """Gives a role to the all humans."""
        await mt._add_roles_humans(ctx.guild, ctx.command.name, ctx.channel,
                                   operator, role, reason)
        await self.log(ctx, 'Role', 'Humans', f'{reason}')

    @role.command(name="add", aliases=['arole', 'giverole', 'grole'])
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    async def add_role(self,
                       ctx: Context,
                       member: discord.Member,
                       role: discord.Role,
                       *,
                       reason: reason_convert = None):
        """Gives a role to the specified member(s)."""
        await mt._add_roles(ctx.guild, ctx.command.name, ctx.author,
                            ctx.channel, member, role, reason)
        await self.log(ctx, 'Role add', f'{member.mention}', f'{reason}')

    @role.command(name='remove', aliases=['urole', 'removerole', 'rrole'])
    @commands.check_any(is_mod(), commands.has_permissions(manage_roles=True))
    @commands.bot_has_permissions(manage_roles=True)
    async def remove_role(self,
                          ctx: Context,
                          member: discord.Member,
                          role: discord.Role,
                          *,
                          reason: reason_convert = None):
        """Remove the mentioned role from mentioned/id member"""
        await mt._remove_roles(ctx.guild, ctx.command.name, ctx.author,
                               ctx.channel, member, role, reason)
        await self.log(ctx, 'Role removed', f'{member.mention}', f'{reason}')

    @commands.command(aliases=['hackban'])
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self,
                  ctx: Context,
                  member: discord.User,
                  days: typing.Optional[int] = None,
                  *,
                  reason: reason_convert = None):
        """To ban a member from guild."""

        if days is None: days = 0
        await mt._ban(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                      member, days, reason)
        await self.log(ctx, 'Ban', f'{member.mention}', f'{reason}')

    @commands.command(name='massban')
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    async def mass_ban(self,
                       ctx: Context,
                       members: commands.Greedy[discord.User],
                       days: typing.Optional[int] = None,
                       *,
                       reason: reason_convert = None):
        """To Mass ban list of members, from the guild"""
        if days is None: days = 0
        await mt._mass_ban(ctx.guild, ctx.command.name, ctx.author,
                           ctx.channel, members, days, reason)
        await self.log(ctx, 'Mass Ban',
                       f'{", ".join([member.mention for member in members])}',
                       f'{reason}')

    @commands.command(aliases=['softkill'])
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self,
                      ctx: Context,
                      member: commands.Greedy[discord.Member],
                      *,
                      reason: reason_convert = None):
        """To Ban a member from a guild then immediately unban"""
        await mt._softban(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                          member, reason)
        await self.log(ctx, 'Soft Ban',
                       f'{", ".join([member.mention for member in member])}',
                       f'{reason}')

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_permissions=True,
                                  manage_roles=True)
    async def block(self,
                    ctx: Context,
                    member: commands.Greedy[discord.Member],
                    *,
                    reason: reason_convert = None):
        """Blocks a user from replying message in that channel."""

        await mt._block(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                        ctx.channel, member, reason)
        await self.log(ctx, 'Block',
                       f'{", ".join([member.mention for member in member])}',
                       f'{reason}')

    @commands.command(aliases=['nuke'])
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_channels=True))
    @commands.bot_has_permissions(manage_channels=True)
    async def clone(self,
                    ctx: Context,
                    channel: discord.TextChannel = None,
                    *,
                    reason: reason_convert = None):
        """To clone the channel or to nukes the channel (clones and delete)."""
        await mt._clone(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                        channel or ctx.channel, reason)
        await self.log(ctx, 'Clone', f'{channel.mention}', f'{reason}')

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self,
                   ctx: Context,
                   member: discord.Member,
                   *,
                   reason: reason_convert = None):
        """To kick a member from guild."""
        await mt._kick(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                       member, reason)
        await self.log(ctx, 'Kick', f'{member.mention}', f'{reason}')

    @commands.command(name='masskick')
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(kick_members=True)
    async def mass_kick(self,
                        ctx: Context,
                        members: commands.Greedy[discord.Member],
                        *,
                        reason: reason_convert = None):
        """To kick a member from guild."""
        await mt._mass_kick(ctx.guild, ctx.command.name, ctx.author,
                            ctx.channel, members, reason)
        await self.log(ctx, 'Mass Kick',
                       f'{", ".join([member.mention for member in members])}',
                       f'{reason}')

    @commands.group()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_permissions=True,
                                  manage_roles=True)
    async def lock(self, ctx: Context):
        """To lock the channel"""
        pass

    @lock.command(name='text')
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_permissions=True,
                                  manage_roles=True)
    async def text_lock(self,
                        ctx: Context,
                        *,
                        channel: discord.TextChannel = None):
        """To lock the text channel"""
        await mt._text_lock(ctx.guild, ctx.command.name, ctx.author,
                            ctx.channel, channel or ctx.channel)
        await self.log(
            ctx, 'Text Lock', f'{channel.mention}',
            f'Action Requested by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id})'
        )

    @lock.command(name='vc')
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_permissions=True,
                                  manage_roles=True)
    async def vc_lock(self,
                      ctx: Context,
                      *,
                      channel: discord.VoiceChannel = None):
        """To lock the Voice Channel"""
        await mt._vc_lock(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                          channel or ctx.author.voice.channel)
        await self.log(
            ctx, 'VC Lock', f'{channel.mention}',
            f'Action Requested by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id})'
        )

    @commands.group()
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_channels=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_roles=True,
                                  manage_permissions=True)
    async def unlock(self, ctx: Context):
        """To unlock the channel (Text channel)"""
        pass

    @unlock.command(name='text')
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_permissions=True,
                                  manage_roles=True)
    async def text_unlock(self,
                          ctx: Context,
                          *,
                          channel: discord.TextChannel = None):
        """To unlock the text channel"""
        await mt._text_unlock(ctx.guild, ctx.command.name, ctx.author,
                              ctx.channel, channel or ctx.channel)
        await self.log(
            ctx, 'Text Un-Lock', f'{channel.mention}',
            f'Action Requested by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id})'
        )

    @unlock.command(name='vc')
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_permissions=True,
                                  manage_roles=True)
    async def vc_unlock(self,
                        ctx: Context,
                        *,
                        channel: discord.VoiceChannel = None):
        """To unlock the Voice Channel"""
        await mt._vc_unlock(ctx.guild, ctx.command.name, ctx.author,
                            ctx.channel, channel or ctx.author.voice.channel)
        await self.log(
            ctx, 'VC Un-Lock', f'{channel.mention}',
            f'Action Requested by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id})'
        )

    @commands.has_permissions(kick_members=True)
    @commands.check_any(is_mod(),
                        commands.bot_has_permissions(manage_roles=True))
    @commands.command()
    async def mute(self,
                   ctx: Context,
                   member: discord.Member,
                   seconds: typing.Union[convert_time, int] = 0,
                   *,
                   reason: reason_convert = None):
        """To restrict a member to sending message in the Server"""
        await mt._mute(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                       member, seconds, reason)
        await self.log(ctx, 'Mute', f'{member.mention}',
                       f'{reason} | For {seconds}s')

    @commands.command()
    @commands.check_any(is_mod(), commands.has_permissions(kick_members=True))
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self,
                     ctx: Context,
                     member: discord.Member,
                     *,
                     reason: reason_convert = None):
        """To allow a member to sending message in the Text Channels, if muted."""
        await mt._unmute(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                         member, reason)
        await self.log(ctx, 'Un-Mute', f'{member.mention}', f'{reason}')

    @commands.command(aliases=['purge'])
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(read_message_history=True,
                                  manage_messages=True)
    async def clean(
        self,
        ctx: Context,
        amount: int,
    ):
        """To delete bulk message."""
        if not ctx.invoked_subcommand:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=amount, bulk=True)
            await ctx.send(
                f"{ctx.author.mention} {len(deleted)} message deleted :')",
                delete_after=5)
            await self.log(
                ctx, 'Clean', f'{ctx.channel.mention}',
                f'Action Requested by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) | Total message deleted {len(deleted)}'
            )

    @commands.command()
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(manage_messages=True,
                                  read_message_history=True)
    async def purgeuser(self, ctx: Context, amount: int, *,
                        member: discord.Member):
        """To delete bulk message, of a specified user."""
        def check_usr(m):
            return m.author == member

        deleted = await ctx.channel.purge(limit=amount,
                                          bulk=True,
                                          check=check_usr)
        await ctx.send(f"{ctx.author.mention} message deleted :')",
                       delete_after=5)
        await self.log(
            ctx, 'Clean user', f'{ctx.channel.mention}',
            f'Action Requested by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) | Total message deleted {len(deleted)}'
        )

    @commands.command()
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(manage_messages=True,
                                  read_message_history=True)
    async def purgebots(self, ctx: Context, amount: int):
        """To delete bulk message, of bots"""
        def check(m):
            return m.author.bot

        deleted = await ctx.channel.purge(limit=amount, bulk=True, check=check)
        await ctx.send(f"{ctx.author.mention} message deleted :')",
                       delete_after=5)
        await self.log(
            ctx, 'Clean Bots', f'{ctx.channel.mention}',
            f'Action Requested by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) | Total message deleted {len(deleted)}'
        )

    @commands.command()
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(manage_messages=True,
                                  read_message_history=True)
    async def purgeregex(self, ctx: Context, amount: int, *, regex: str):
        """
				To delete bulk message, matching the regex
				"""
        def check(m):
            return re.search(regex, m.message.context)

        deleted = await ctx.channel.purge(limit=amount, bulk=True, check=check)
        await ctx.send(f"{ctx.author.mention} message deleted :')",
                       delete_after=5)
        await self.log(
            ctx, 'Clean Regex', f'{ctx.channel.mention}',
            f'Action Requested by {ctx.author.name}#{ctx.author.mention} ({ctx.author.id}) | Total message deleted {len(deleted)}'
        )

    @commands.command()
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_channels=True))
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self,
                       ctx: Context,
                       seconds: typing.Union[int, str],
                       channel: discord.TextChannel = None,
                       *,
                       reason: reason_convert = None):
        """To set slowmode in the specified channel"""
        await mt._slowmode(ctx.guild, ctx.command.name, ctx.author,
                           ctx.channel, seconds, channel or ctx.channel,
                           reason)
        await self.log(ctx, 'Slowmode', f'{channel.mention}',
                       f'{reason} | For {seconds}s')

    @commands.command(brief='To Unban a member from a guild')
    @commands.check_any(is_mod(), commands.has_permissions(ban_members=True))
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self,
                    ctx: Context,
                    member: discord.User,
                    *,
                    reason: reason_convert = None):
        """To Unban a member from a guild"""

        await mt._unban(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                        member, reason)
        await self.log(ctx, 'Un-Ban', f'{member.mention}', f'{reason}')

    @commands.command()
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_permissions=True,
                                                 manage_roles=True,
                                                 manage_channels=True))
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_permissions=True,
                                  manage_roles=True)
    async def unblock(self,
                      ctx: Context,
                      member: commands.Greedy[discord.Member],
                      *,
                      reason: reason_convert = None):
        """Unblocks a user from the text channel"""

        await mt._unblock(ctx.guild, ctx.command.name, ctx.author, ctx.channel,
                          ctx.channel, member, reason)
        await self.log(ctx, 'Un-Block',
                       f'{", ".join([member.mention for member in member])}',
                       f'{reason}')

    @commands.command()
    @commands.check_any(is_mod(),
                        commands.has_permissions(manage_permissions=True,
                                                 manage_messages=True,
                                                 manage_channels=True,
                                                 ban_members=True,
                                                 manage_roles=True,
                                                 kick_members=True,
                                                 manage_nicknames=True))
    @commands.bot_has_permissions(manage_permissions=True,
                                  manage_messages=True,
                                  manage_channels=True,
                                  ban_members=True,
                                  manage_roles=True,
                                  kick_members=True,
                                  read_message_history=True,
                                  add_reactions=True,
                                  manage_nicknames=True)
    async def mod(self,
                  ctx: Context,
                  target: typing.Union[discord.Member, discord.User,
                                       discord.TextChannel,
                                       discord.VoiceChannel, discord.Role],
                  *,
                  reason: reason_convert = None):
        """
        Why to learn the commands. This is all in one mod command.
        """
        if not target: ctx.send_help(ctx.command)
        if (type(target) is discord.Member) or (type(target) is discord.User):
            member_embed = discord.Embed(title='Mod Menu',
                                         description=':hammer: Ban\n'
                                         ':boot: Kick\n'
                                         ':zipper_mouth: Mute\n'
                                         ':grin: Unmute\n'
                                         ':x: Block\n'
                                         ':o: Unblock\n'
                                         ':arrow_up: Add role\n'
                                         ':arrow_down: Remove role'
                                         ':pen_fountain: Change Nickname',
                                         timestamp=datetime.utcnow(),
                                         color=ctx.author.color)
            member_embed.set_footer(text=f'{ctx.author.guild.name} mod tool')
            member_embed.set_thumbnail(url=ctx.guild.icon_url)
            msg = await ctx.send(embed=member_embed)
            for reaction in mt.MEMBER_REACTION:
                await msg.add_reaction(reaction)

            def check(reaction, user):
                return str(
                    reaction.emoji
                ) in mt.MEMBER_REACTION and user == ctx.author and reaction.message.id == msg.id

            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                reaction, user = await self.bot.wait_for('reaction_add',
                                                         timeout=60.0,
                                                         check=check)
            except asyncio.TimeoutError:
                return await msg.delete()
            if str(reaction.emoji) == mt.MEMBER_REACTION[0]:
                await mt._ban(ctx.guild, ctx.command.name, ctx.author,
                              ctx.channel, target, 0, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[1]:
                await mt._kick(ctx.guild, ctx.command.name, ctx.author,
                               ctx.channel, target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[2]:
                await mt._mute(ctx.guild, ctx.command.name, ctx.author,
                               ctx.channel, target, 0, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[3]:
                await mt._unmute(ctx.guild, ctx.command.name, ctx.author,
                                 ctx.channel, target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[4]:
                await mt._block(ctx.guild, ctx.command.name, ctx.author,
                                ctx.channel, ctx.channel, target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[5]:
                await mt._unblock(ctx.guild, ctx.command.name, ctx.author,
                                  ctx.channel, ctx.channel, target, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[6]:
                temp = await ctx.send(
                    f'{ctx.author.mention} Enter the Role, [ID, NAME, MENTION]'
                )
                try:
                    m = await self.bot.wait_for('message',
                                                timeout=30,
                                                check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete()
                role = await commands.RoleConverter().convert(ctx, m.content)
                await temp.delete()
                await mt._add_roles(ctx.guild, ctx.command.name, ctx.author,
                                    ctx.channel, target, role, reason)

            if str(reaction.emoji) == mt.MEMBER_REACTION[7]:
                temp = await ctx.send(
                    f'{ctx.author.mention} Enter the Role, [ID, NAME, MENTION]'
                )
                try:
                    m = await self.bot.wait_for('message',
                                                timeout=30,
                                                check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete()
                role = await commands.RoleConverter().convert(ctx, m.content)
                await temp.delete()
                await mt._remove_roles(ctx.guild, ctx.command.name, ctx.author,
                                       ctx.channel, target, role, reason)
            if str(reaction.emoji) == mt.MEMBER_REACTION[8]:
                await ctx.send(
                    f'{ctx.author.mention} Enter the Nickname, [Not more than 32 char]',
                    delete_after=30)
                try:
                    m = await self.bot.wait_for('message',
                                                timeout=30,
                                                check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete()

                await mt._change_nickname(ctx.guild, ctx.command.name,
                                          ctx.author, ctx.channel, target,
                                          (m.content)[:31:], reason)


        if (type(target) is discord.TextChannel):
            tc_embed = discord.Embed(title='Mod Menu',
                                     description=':lock: Lock\n'
                                     ':unlock: Unlock\n'
                                     ':pencil: Change Topic\n'
                                     ':pen_fountain: Change Name',
                                     timestamp=datetime.utcnow(),
                                     color=ctx.author.color)
            tc_embed.set_footer(text=f'{ctx.author.guild.name} mod tool')
            tc_embed.set_thumbnail(url=ctx.guild.icon_url)
            msg = await ctx.send(embed=tc_embed)
            for reaction in mt.TEXT_REACTION:
                await msg.add_reaction(reaction)

            def check(reaction, user):
                return str(
                    reaction.emoji
                ) in mt.TEXT_REACTION and user == ctx.author and reaction.message.id == msg.id

            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                reaction, user = await self.bot.wait_for('reaction_add',
                                                         timeout=60.0,
                                                         check=check)
            except asyncio.TimeoutError:
                return await msg.delete()

            if str(reaction.emoji) == mt.TEXT_REACTION[0]:
                await mt._text_lock(ctx.guild, ctx.command.name, ctx.author,
                                    ctx.channel, target)

            if str(reaction.emoji) == mt.TEXT_REACTION[1]:
                await mt._text_unlock(ctx.guild, ctx.command.name, ctx.author,
                                      ctx.channel, target)

            if str(reaction.emoji) == mt.TEXT_REACTION[2]:
                await ctx.send(f'{ctx.author.mention} Enter the Channel Topic',
                               delete_after=60)
                try:
                    m = self.bot.wait_for('message',
                                          timeout=60,
                                          check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete()
                await mt._change_channel_topic(ctx.guild, ctx.command.name,
                                               ctx.author, ctx.channel,
                                               target, m.content)

            if str(reaction.emoji) == mt.TEXT_REACTION[3]:
                await ctx.send(f'{ctx.author.mention} Enter the Channel Name',
                               delete_after=60)
                try:
                    m = self.bot.wait_for('message',
                                          timeout=60,
                                          check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete()
                await mt._change_channel_name(ctx.guild, ctx.command.name,
                                              ctx.author, ctx.channel,
                                              ctx.channel, m.content)

        if (type(target) is discord.VoiceChannel):
            vc_embed = discord.Embed(title='Mod Menu',
                                     description=':lock: Lock\n'
                                     ':unlock: Unlock\n'
                                     ':pen_fountain: Change Name',
                                     timestamp=datetime.utcnow(),
                                     color=ctx.author.color)
            vc_embed.set_footer(text=f'{ctx.author.guild.name} mod tool')
            vc_embed.set_thumbnail(url=ctx.guild.icon_url)
            msg = await ctx.send(embed=tc_embed)
            for reaction in mt.VC_REACTION:
                await msg.add_reaction(reaction)

            def check(reaction, user):
                return str(
                    reaction.emoji
                ) in mt.VC_REACTION and user == ctx.author and reaction.message.id == msg.id

            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                reaction, user = await self.bot.wait_for('reaction_add',
                                                         timeout=60.0,
                                                         check=check)
            except asyncio.TimeoutError:
                return await msg.delete()

            if str(reaction.emoji) == mt.VC_REACTION[0]:
                await mt._vc_lock(ctx.guild, ctx.command.name, ctx.author,
                                  ctx.channel, ctx.author.voice.channel or target)

            if str(reaction.emoji) == mt.VC_REACTION[1]:
                await mt._vc_unlock(ctx.guild, ctx.command.name, ctx.author,
                                    ctx.channel, ctx.author.voice.channel or target)

            if str(reaction.emoji) == mt.VC_REACTION[2]:
                await ctx.send(f'{ctx.author.mention} Enter the Channel Name',
                               delete_after=60)
                try:
                    m = self.bot.wait_for('message',
                                          timeout=60,
                                          check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete()
                await mt._change_channel_name(ctx.guild, ctx.command.name,
                                              ctx.author, ctx.channel,
                                              ctx.channel, m.content)


        if (type(target) is discord.Role):
            role_embed = discord.Embed(title='Mod Menu',
                                       description=':lock: Hoist\n'
                                       ':unlock: De-Hoist\n'
                                       ':rainbow: Change Colour'
                                       ':pen_fountain: Change Name',
                                       timestamp=datetime.utcnow(),
                                       color=ctx.author.color)
            role_embed.set_footer(text=f'{ctx.author.guild.name} mod tool')
            role_embed.set_thumbnail(url=ctx.guild.icon_url)
            msg = await ctx.send(embed=tc_embed)
            for reaction in mt.ROLE_REACTION:
                await msg.add_reaction(reaction)

            def check(reaction, user):
                return str(
                    reaction.emoji
                ) in mt.ROLE_REACTION and user == ctx.author and reaction.message.id == msg.id

            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                reaction, user = await self.bot.wait_for('reaction_add',
                                                         timeout=60.0,
                                                         check=check)
            except asyncio.TimeoutError:
                return await msg.delete()

            if str(reaction.emoji) == mt.ROLE_REACTION[0]:
                await mt._role_hoist(ctx.guild, ctx.command.name, ctx.author, ctx.channel, target, True, reason)

            if str(reaction.emoji) == mt.ROLE_REACTION[1]:
                await mt._role_hoist(ctx.guild, ctx.command.name, ctx.author, ctx.channel, target, False, reason)
            if str(reaction.emoji) == mt.ROLE_REACTION[2]: pass #todo: color change
            if str(reaction.emoji) == mt.ROLE_REACTION[3]:
                await ctx.send(f'{ctx.author.mention} Enter the Role Name',
                               delete_after=60)
                try:
                    m = self.bot.wait_for('message',
                                          timeout=60,
                                          check=check_msg)
                except asyncio.TimeoutError:
                    return await msg.delete()
                await mt._change_role_name(ctx.guild, ctx.command.name,
                                           ctx.author, ctx.channel,
                                           ctx.channel, m.content, reason)

        return await msg.delete()


def setup(bot):
    bot.add_cog(mod(bot))
