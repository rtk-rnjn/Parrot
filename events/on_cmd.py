from __future__ import annotations

import discord
import traceback
import math
import random
import aiohttp
from discord.ext import commands
from datetime import datetime

from utilities.exceptions import ParrotCheckFaliure
from core import Parrot, Context, Cog

from utilities.database import cmd_increment, parrot_db

with open("extra/quote.txt") as f:
    quote = f.read()

quote = quote.split('\n')


class ErrorView(discord.ui.View):
    def __init__(self, author_id, *, ctx: Context = None, error=None):
        super().__init__(timeout=300.0)
        self.author_id = author_id
        self.ctx = ctx
        self.error = error

    async def paste(self, text):
        """Return an online bin of given text"""
        async with aiohttp.ClientSession() as aioclient:
            post = await aioclient.post('https://hastebin.com/documents',
                                        data=text)
            if post.status == 200:
                response = await post.text()
                return f'https://hastebin.com/{response[8:-2]}'

            # Rollback bin
            post = await aioclient.post("https://bin.readthedocs.fr/new",
                                        data={
                                            'code': text,
                                            'lang': 'txt'
                                        })
            if post.status == 200:
                return str(post.url)

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        else:
            await interaction.response.send_message('Stay away',
                                                    ephemeral=True)
            return False

    @discord.ui.button(label='Show full error',
                       style=discord.ButtonStyle.green)
    async def show_full_traceback(self, button: discord.ui.button,
                                  interaction: discord.Interaction):
        tb = traceback.format_exception(type(self.error), self.error,
                                        self.error.__traceback__)
        tbe = "".join(tb) + ""
        er = f'```py\nIgnoring exception in command {self.ctx.command.name}: {tbe}\n```'
        text = await self.paste(er)
        if len(er) < 1950:
            await interaction.response.send_message(er, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)


class Cmd(Cog, command_attrs=dict(hidden=True)):
    """This category is of no use for you, ignore it."""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['logging']

    async def paste(self, text):
        """Return an online bin of given text"""
        async with aiohttp.ClientSession() as aioclient:
            post = await aioclient.post('https://hastebin.com/documents',
                                        data=text)
            if post.status == 200:
                response = await post.text()
                return f'https://hastebin.com/{response[8:-2]}'

            # Rollback bin
            post = await aioclient.post("https://bin.readthedocs.fr/new",
                                        data={
                                            'code': text,
                                            'lang': 'txt'
                                        })
            if post.status == 200:
                return str(post.url)

    @Cog.listener()
    async def on_command(self, ctx: Context):
        """This event will be triggered when the command is being completed; triggered by [discord.User]!"""
        if ctx.author.bot: return
        await cmd_increment(ctx.command.qualified_name)
    
    @Cog.listener()
    async def on_command_completion(self, ctx: Context):
        """Only for logging"""
        if ctx.cog is None: return
        if ctx.cog.qualified_name.lower() == 'mod':
            if data := await self.collection.find_one({'_id': ctx.guild.id, 'on_mod_command': {'$exists': True}}):
                webhook = discord.Webhook.from_url(data['on_mod_command'], session=self.bot.session)
                if webhook:
                    main_content = """**On Moderator Command**

`Mod    `: **{ctx.author}**
`Command`: **{ctx.command.qualified_name}**
`Content`: **{ctx.message.content}**
"""
                    await webhook.send(
                        content=main_content, 
                        avatar_url=self.bot.user.avatar.url, 
                        username=self.bot.user.name,
                    )
        
        if ctx.cog.qualified_name.lower() == 'botconfig':
            if data := await self.collection.find_one({'_id': ctx.guild.id, 'on_config_command': {'$exists': True}}):
                webhook = discord.Webhook.from_url(data['on_config_command'], session=self.bot.session)
                if webhook:
                    main_content = """**On Config Command**

`Admin  `: **{ctx.author}**
`Command`: **{ctx.command.qualified_name}**
`Content`: **{ctx.message.content}**
"""
                    await webhook.send(
                        content=main_content, 
                        avatar_url=self.bot.user.avatar.url, 
                        username=self.bot.user.name,
                    )
                
    @Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        # if command has local error handler, return
        if hasattr(ctx.command, 'on_error'): return

        # get the original exception
        error = getattr(error, 'original', error)

        ignore = (commands.CommandNotFound, discord.NotFound, discord.Forbidden)

        if isinstance(error, ignore): 
            print(error)
            return

        elif isinstance(error, commands.BotMissingPermissions):
            missing = [
                perm.replace('_', ' ').replace('guild', 'server').title()
                for perm in error.missing_permissions
            ]
            if len(missing) > 2:
                fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
            else:
                fmt = ' and '.join(missing)
            _message = f'**{random.choice(quote)}**\nBot Missing permissions. Please provide the following permission(s) to the bot.```\n{fmt}```'
            return await ctx.reply(_message)

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.reply(
                f'{random.choice(quote)}\n\n{ctx.author.mention} this command has been disabled. Consider asking your Server Manager to fix this out'
            )

        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.reply(
                f"**{random.choice(quote)}**\nCommand On Cooldown. You are on command cooldown, please retry in **{math.ceil(error.retry_after)}**s"
            )

        elif isinstance(error, commands.MissingPermissions):
            missing = [
                perm.replace('_', ' ').replace('guild', 'server').title()
                for perm in error.missing_permissions
            ]
            if len(missing) > 2:
                fmt = '{}, and {}'.format("**, **".join(missing[:-1]),
                                          missing[-1])
            else:
                fmt = ' and '.join(missing)
            _message = '**{}**\nMissing Permissions. You need the the following permission(s) to use the command```\n{}```'.format(
                random.choice(quote), fmt)
            await ctx.reply(_message)
            return

        elif isinstance(error, commands.MissingRole):
            missing = [role for role in error.missing_role]
            if len(missing) > 2:
                fmt = '{}, and {}'.format("**, **".join(missing[:-1]),
                                          missing[-1])
            else:
                fmt = ' and '.join(missing)
            _message = '**{}**\nMissing Role. You need the the following role(s) to use the command```\n{}```'.format(
                random.choice(quote), fmt)
            await ctx.reply(_message)
            return

        elif isinstance(error, commands.MissingAnyRole):
            missing = [role for role in error.missing_roles]
            if len(missing) > 2:
                fmt = '{}, and {}'.format("**, **".join(missing[:-1]),
                                          missing[-1])
            else:
                fmt = ' and '.join(missing)
            _message = '**{}**\nMissing Role. You need the the following role(s) to use the command```\n{}```'.format(
                random.choice(quote), fmt)
            await ctx.reply(_message)
            return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.reply(
                    f'**{random.choice(quote)}**\nNo Private Message. This command cannot be used in direct messages. It can only be used in server'
                )
            except discord.Forbidden:
                pass
            return

        elif isinstance(error, commands.NSFWChannelRequired):
            if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                em = discord.Embed(timestamp=datetime.utcnow())
                em.set_image(url="https://i.imgur.com/oe4iK5i.gif")
                await ctx.reply(
                    content=
                    f"**{random.choice(quote)}**\nNSFW Channel Required. This command will only run in NSFW marked channel. https://i.imgur.com/oe4iK5i.gif",
                    embed=em)
            else:
                await ctx.reply(
                    content=
                    f"**{random.choice(quote)}**\nNSFW Channel Required. This command will only run in NSFW marked channel. https://i.imgur.com/oe4iK5i.gif"
                )
            return

        elif isinstance(error, commands.NotOwner):
            await ctx.reply(
                f"**{random.choice(quote)}**\nNot Owner. You must have ownership of the bot to run {ctx.command.name}"
            )
            return

        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.reply(
                f"**{random.choice(quote)}**\nPrivate Message Only. This comamnd will only work in DM messages"
            )

        elif isinstance(error, commands.BadArgument):
            if isinstance(error, commands.MessageNotFound):
                return await ctx.reply(
                    f'**{random.choice(quote)}**\nMessage Not Found. Message ID/Link you provied is either invalid or deleted'
                )
            elif isinstance(error, commands.MemberNotFound):
                return await ctx.reply(
                    f'**{random.choice(quote)}**\nMember Not Found. Member ID/Mention/Name you provided is invalid or bot can not see that Member'
                )
            elif isinstance(error, commands.UserNotFound):
                return await ctx.reply(
                    f'**{random.choice(quote)}**\nUser Not Found. User ID/Mention/Name you provided is invalid or bot can not see that User'
                )
            elif isinstance(error, commands.ChannelNotFound):
                return await ctx.reply(
                    f'**{random.choice(quote)}**\nChannel Not Found. Channel ID/Mention/Name you provided is invalid or bot can not see that Channel'
                )
            elif isinstance(error, commands.RoleNotFound):
                return await ctx.reply(
                    f'**{random.choice(quote)}**\nRole Not Found. Role ID/Mention/Name you provided is invalid or bot can not see that Role'
                )
            elif isinstance(error, commands.EmojiNotFound):
                return await ctx.reply(
                    f'**{random.choice(quote)}**\nEmoji Not Found. Emoji ID/Name you provided is invalid or bot can not see that Emoji'
                )
            else:
                return await ctx.reply(
                    f'**{random.choice(quote)}**\n{error}'
                )

        elif isinstance(error, commands.MissingRequiredArgument):
            command = ctx.command
            return await ctx.reply(
                f"**{random.choice(quote)}**\nMissing Required Argument. Please use proper syntax.```\n{ctx.clean_prefix}{command.qualified_name}{'|' if command.aliases else ''}{'|'.join(command.aliases if command.aliases else '')} {command.signature}```"
            )

        elif isinstance(error, commands.MaxConcurrencyReached):
            return await ctx.reply(
                f"**{random.choice(quote)}**\nMax Concurrenry Reached. This command is already running in this server/channel by you. You have wait for it to finish"
            )

        elif isinstance(error, (commands.BadUnionArgument, commands.BadLiteralArgument)):
            return await ctx.reply(
                f"**{random.choice(quote)}**\nBad Argument! `@Parrot {ctx.command}` for help"
            )

        elif isinstance(error, ParrotCheckFaliure):
            return await ctx.reply(error.__str__().format(ctx=ctx))

        elif isinstance(error, commands.CheckAnyFailure):
            return await ctx.reply(' or '.join(
                [error.__str__().format(ctx=ctx) for error in error.errors]))

        else:
            await ctx.reply(
                f"**{random.choice(quote)}**\nWell this is embarrassing. For some reason **{ctx.command.qualified_name}** is not working",
                view=ErrorView(ctx.author.id, ctx=ctx, error=error))


def setup(bot):
    bot.add_cog(Cmd(bot))
