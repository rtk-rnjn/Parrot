from discord.ext import commands
import discord, typing, aiohttp
from discord import Webhook
from core import Parrot, Context, Cog

from database.server_config import collection as csc, guild_join, guild_update
from database.global_chat import collection as cgc, gchat_on_join, gchat_update
from database.telephone import collection as ct, telephone_update, telephone_on_join
from utilities.checks import has_verified_role_ticket
from cogs.ticket import method as mt


class BotConfig(Cog, name="botconfig"):
    """To config the bot. In the server"""
    def __init__(self, bot: Parrot):
        self.bot = bot

    @commands.group(name='serverconfig', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def config(self, ctx: Context):
        """
				To config the bot, mod role, prefix, or you can disable the commands and cogs.
				"""
        if not csc.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)
        if not ctx.invoked_subcommand:
            data = csc.find_one({'_id': ctx.guild.id})
            await ctx.send(
                f"Configuration of this server [server_config]\n\n"
                f"Prefix: {data['prefix']}\n"
                f"ModRole: {ctx.guild.get_role(data['mod_role']).name} ID: {data['mod_role']}\n"
                f"MogLog: {ctx.guild.get_channel(data['action_log']).name} ID: {data['action_log']}\n"
            )

    @config.command(aliases=['prefix'])
    @commands.has_permissions(administrator=True)
    async def botprefix(self, ctx: Context, *, arg: str):
        """
				To set the prefix of the bot. Whatever prefix you passed, will be case sensitive. It is advised to keep a symbol as a prefix. Must not greater than 6 chars
				"""
        if not csc.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)
        if len(arg) > 6:
            return await ctx.reply(
                f"{ctx.author.mention} length of prefix can not be more than 6 characters."
            )
        post = {'prefix': arg}
        await guild_update(ctx.guild.id, post)

        await ctx.send(
            f"{ctx.author.mention} success! Prefix for **{ctx.guild.name}** is **{arg}**."
        )

    @config.command(aliases=['mute-role'])
    @commands.has_permissions(administrator=True)
    async def muterole(self, ctx: Context, *, role: discord.Role = None):
        """
				To set the mute role of the server. By default role with name `Muted` is consider as mute role.
				"""
        if not csc.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)
        post = {'mute_role': role.id if role else None}
        await guild_update(ctx.guild.id, post)
        if not role:
            return await ctx.send(
                f"{ctx.author.mention} mute role reseted! or removed")
        await ctx.send(
            f"{ctx.author.mention} success! Mute role for **{ctx.guild.name}** is **{role.name} ({role.id})**"
        )

    @config.command(aliases=['mod-role'])
    @commands.has_permissions(administrator=True)
    async def modrole(self, ctx: Context, *, role: discord.Role = None):
        """
				To set mod role of the server. People with mod role can accesss the Moderation power of Parrot. By default the mod functionality works on the basis of permission
				"""
        if not csc.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)

        post = {'mod_role': role.id if role else None}
        await guild_update(ctx.guild.id, post)
        if not role:
            return await ctx.send(
                f"{ctx.author.mention} mod role reseted! or removed")
        await ctx.send(
            f"{ctx.author.mention} success! Mod role for **{ctx.guild.name}** is **{role.name} ({role.id})**"
        )

    @config.command(aliases=['action-log', 'modlog', 'mod-log'])
    @commands.has_permissions(administrator=True)
    async def actionlog(self,
                        ctx: Context,
                        *,
                        channel: discord.TextChannel = None):
        """
				To set the action log, basically the mod log.
				"""

        if not csc.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)

        post = {'action_log': channel.id if channel else None}
        await guild_update(ctx.guild.id, post)
        if not channel:
            return await ctx.send(
                f"{ctx.author.mention} action log reseted! or removed")
        await ctx.reply(
            f"{ctx.author.mention} success! Action log for **{ctx.guild.name}** is **{channel.name} ({channel.id})**"
        )

    @config.command(aliases=['g-setup'])
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_webhooks=True,
                                  manage_roles=True)
    async def gsetup(self,
                     ctx: Context,
                     setting: str = None,
                     *,
                     role: typing.Union[discord.Role] = None):
        """
				This command will connect your server with other servers which then connected to #global-chat must try this once
				"""
        if not cgc.find_one({'_id': ctx.guild.id}):
            await gchat_on_join(ctx.guild.id)

        if not setting:
            guild = ctx.guild
            overwrites = {
                guild.default_role:
                discord.PermissionOverwrite(read_messages=True,
                                            send_messages=True,
                                            read_message_history=True),
                guild.me:
                discord.PermissionOverwrite(read_messages=True,
                                            send_messages=True,
                                            read_message_history=True)
            }
            channel = await guild.create_text_channel(
                'global-chat',
                topic="Hmm. Please be calm, be very calm",
                overwrites=overwrites)

            webhook = await channel.create_webhook(name="GlobalChat")

            post = {'channel_id': channel.id, 'webhook': webhook.url}

            await gchat_update(guild.id, post)
            await ctx.send(f"{channel.mention} created successfully.")
            return

        if (setting.lower() in ['ignore-role', 'ignore_role', 'ignorerole'
                                ]) and (role is not None):
            post = {'ignore-role': role.id}
            await gchat_update(ctx.guild.id, post)
            await ctx.reply(
                f"{ctx.author.mention} success! **{role.name} ({role.id})** will be ignored from global chat!"
            )

    @commands.command(hidden=True)
    @commands.is_owner()
    async def broadcast(self, ctx: Context, *, message: str):
        """
				To broadcast all over the global channel. Only for owners.
				"""
        data = cgc.find({})

        for webhooks in data:
            hook = webhooks['webhook']
            try:

                async def send_webhook():
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(f"{hook}", adapter=session)

                        await webhook.send(
                            content=f"{message}",
                            username="SYSTEM",
                            avatar_url=f"{self.bot.guild.me.avatar.url}")

                await send_webhook()
            except:
                continue

    @commands.group(aliases=['telconfig'], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def telsetup(self, ctx: Context):
        """
    To set the telephone phone line, in the server to call and receive the call from other server. Available settings 'channel', 'pingrole', 'memberping', 'block', 'unblock'
    """
        if not ct.find_one({'_id': ctx.guild.id}):
            await telephone_on_join(ctx.guild.id)
        if not ctx.invoked_subcommand:
            data = ct.find_one({'_id': ctx.guild.id})
            await ctx.send(
                f"Configuration of this server [telsetup]\n\n"
                f"Channel: {data['channel']}\n"
                f"Pingrole: {ctx.guild.get_role(data['pingrole']).name} ID: {data['pingrole']}\n"
                f"MemberPing: {ctx.guild.get_member(data['pingrole']).name} ID: {data['pingrole']}\n"
                f"Blocked: {', '.join(data['blocked'])}")

    @telsetup.command(name='channel')
    @commands.has_permissions(administrator=True)
    async def tel_config_channel(self,
                                 ctx: Context,
                                 *,
                                 channel: discord.TextChannel = None):
        """
        To setup the telephone line in the channel.
        """
        if not ct.find_one({'_id': ctx.guild.id}):
            await telephone_on_join(ctx.guild.id)
        await telephone_update(ctx.guild.id, 'channel',
                               channel.id if channel else None)
        if not channel:
            return await ctx.send(
                f"{ctx.author.mention} global telephone line is reseted! or removed"
            )
        await ctx.send(
            f"{ctx.author.mention} success! #{channel.name} is now added to global telephone line."
        )

    @telsetup.command(name='pingrole')
    @commands.has_permissions(administrator=True)
    async def tel_config_pingrole(self,
                                  ctx: Context,
                                  *,
                                  role: discord.Role = None):
        """
        To add the ping role. If other server call your server. Then the role will be pinged if set any
        """
        if not ct.find_one({'_id': ctx.guild.id}):
            await telephone_on_join(ctx.guild.id)
        await telephone_update(ctx.guild.id, 'channel',
                               role.id if role else None)
        if not role:
            return await ctx.send(
                f"{ctx.author.mention} ping role reseted! or removed")
        await ctx.send(
            f"{ctx.author.mention} success! @{role.name} will be now pinged when someone calls your server."
        )

    @telsetup.command(name='memberping')
    @commands.has_permissions(administrator=True)
    async def tel_config_memberping(self,
                                    ctx: Context,
                                    *,
                                    member: discord.Member = None):
        """
        To add the ping role. If other server call your server. Then the role will be pinged if set any
        """
        if not ct.find_one({'_id': ctx.guild.id}):
            await telephone_on_join(ctx.guild.id)
        await telephone_update(ctx.guild.id, 'channel',
                               member.id if member else None)
        if not member:
            return await ctx.send(
                f"{ctx.author.menton} member ping reseted! or removed")
        await ctx.send(
            f"{ctx.author.mention} success! @{member.name}#{member.discriminator} will be now pinged when someone calls your server."
        )

    @telsetup.command(name='block')
    @commands.has_permissions(administrator=True)
    async def tel_config_block(self, ctx: Context, *, server: discord.Guild):
        """
        There are people who are really anonying, you can block them.
        """
        if server is ctx.guild:
            return await ctx.send(
                f"{ctx.author.mention} can't block your own server")
        if not ct.find_one({'_id': ctx.guild.id}):
            await telephone_on_join(ctx.guild.id)
        ct.update_one({'_id': ctx.guild.id},
                      {'$addToSet': {
                          'blocked': server.id
                      }})
        await ctx.send(f'{ctx.author.mention} success! blocked: {server.name}')

    @telsetup.command(name='unblock')
    @commands.has_permissions(administrator=True)
    async def tel_config_unblock(self, ctx: Context, *, server: discord.Guild):
        """
        Now they understood their mistake. You can now unblock them.
        """
        if server is ctx.guild:
            return await ctx.send(
                f"{ctx.author.mention} ok google, let the server admin get some rest"
            )
        ct.update_one({'_id': ctx.guild.id}, {'$pull': {'blocked': server.id}})
        await ctx.send(f'{ctx.author.mention} Success! unblocked: {server.id}')

    @commands.group()
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def ticketconfig(self, ctx: Context):
        """
				To config the Ticket Parrot Bot in the server
				"""

    @ticketconfig.command()
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def auto(self,
                   ctx: Context,
                   channel: discord.TextChannel = None,
                   *,
                   message: str = None):
        """
			Automatic ticket making system. On reaction basis
			"""
        channel = channel or ctx.channel
        message = message or 'React to ✉️ to create ticket'
        await mt._auto(ctx, channel, message)

    @ticketconfig.command()
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def setcategory(self, ctx: Context, *,
                          channel: discord.CategoryChannel):
        """
			Where the new ticket will created? In category or on the TOP.
			"""
        await mt._setcategory(ctx, channel)

    @ticketconfig.command()
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def setlog(self, ctx: Context, *, channel: discord.TextChannel):
        """
			Where the tickets action will logged? To config the ticket log.
			"""
        await mt._setlog(ctx, channel)

    @ticketconfig.command()
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def addaccess(self, ctx: Context, *, role: discord.Role):
        '''
			This can be used to give a specific role access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			'''
        await mt._addaccess(ctx, role)

    @ticketconfig.command()
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def delaccess(self, ctx: Context, *, role: discord.Role):
        '''
			This can be used to remove a specific role's access to all tickets. This command can only be run if you have an admin-level role for this bot.
			
			Parrot Ticket `Admin-Level` role or Administrator permission for the user.
			'''
        await mt._delaccess(ctx, role)

    @ticketconfig.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def addadminrole(self, ctx: Context, *, role: discord.Role):
        '''
			This command gives all users with a specific role access to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			'''
        await mt._addadimrole(ctx, role)

    @ticketconfig.command(hidden=False)
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def addpingedrole(self, ctx: Context, *, role: discord.Role):
        '''
			This command adds a role to the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			'''
        await mt._addpingedrole(ctx, role)

    @ticketconfig.command()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(embed_links=True)
    async def deladminrole(self, ctx: Context, *, role: discord.Role):
        """
			This command removes access for all users with the specified role to the admin-level commands for the bot, such as `Addpingedrole` and `Addaccess`.
			"""
        await mt._deladminrole(ctx, role)

    @ticketconfig.command()
    @commands.check_any(commands.has_permissions(administrator=True),
                        has_verified_role_ticket())
    @commands.bot_has_permissions(embed_links=True)
    async def delpingedrole(self, ctx: Context, *, role: discord.Role):
        '''
			This command removes a role from the list of roles that are pinged when a new ticket is created. This command can only be run if you have an admin-level role for this bot.
			'''
        await mt._delpingedrole(ctx, role)


def setup(bot):
    bot.add_cog(BotConfig(bot))
