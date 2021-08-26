import discord, traceback, math, random
from discord.ext import commands
from datetime import datetime

from utilities.exceptions import ParrotCheckFaliure
from core import Parrot, Context, Cog

from utilities.database import cmd_increment

with open("extra/quote.txt") as f:
    quote = f.read()

quote = quote.split('\n')

class Cmd(Cog, command_attrs=dict(hidden=True)):
    """This category is of no use for you, ignore it."""
    def __init__(self, bot: Parrot):
        self.bot = bot
    
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
    async def on_command_error(self, ctx: Context, error):
        # if command has local error handler, return
        if hasattr(ctx.command, 'on_error'): return

        # get the original exception
        error = getattr(error, 'original', error)

        ignore = (commands.CommandNotFound, discord.errors.NotFound, discord.Forbidden)

        if isinstance(error, ignore): return

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
            return await ctx.send(_message)

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(
                f'{random.choice(quote)}\n\n{ctx.author.mention} this command has been disabled. Consider asking your Server Manager to fix this out'
            )

        elif isinstance(error, commands.CommandOnCooldown):
            is_owner = await ctx.bot.is_owner(ctx.author)
            if is_owner: return await ctx.reinvoke()
            return await ctx.send(
                f"**{random.choice(quote)}**\nCommand On Cooldown. You are on command cooldown, please retry in **{math.ceil(error.retry_after)}**s"
            )

        elif isinstance(error, commands.MissingPermissions):
            is_owner = await ctx.bot.is_owner(ctx.author)
            if is_owner: return await ctx.reinvoke()
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
            await ctx.send(_message)
            return

        elif isinstance(error, commands.MissingRole):

            _message = '**{}**\nMissing Role. You need the the following role(s) to use the command```\n{}```'.format(
                random.choice(quote), fmt)
            await ctx.send(_message)
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
            await ctx.send(_message)
            return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.send(
                    f'**{random.choice(quote)}**\nNo Private Message. This command cannot be used in direct messages. It can only be used in server'
                )
            except discord.Forbidden:
                pass
            return

        elif isinstance(error, commands.NSFWChannelRequired):
            em = discord.Embed(timestamp=datetime.utcnow())
            em.set_image(url="https://i.imgur.com/oe4iK5i.gif")
            await ctx.send(
                content=
                f"{random.choice(quote)}\n\nNSFW Channel Required. This command will only run in NSFW marked channel. https://i.imgur.com/oe4iK5i.gif",
                embed=em)
            return

        elif isinstance(error, commands.NotOwner):
            await ctx.send(
                f"**{random.choice(quote)}**\nNot Owner. You must have ownership of the bot to run {ctx.command.name}"
            )
            return

        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.send(
                f"**{random.choice(quote)}**\nPrivate Message Only. This comamnd will only work in DM messages"
            )

        elif isinstance(error, commands.BadArgument):
            if isinstance(error, commands.MessageNotFound):
                return await ctx.send(
                    f'**{random.choice(quote)}**\nMessage Not Found. Message ID/Link you provied is either invalid or deleted'
                )
            elif isinstance(error, commands.MemberNotFound):
                return await ctx.send(
                    f'**{random.choice(quote)}**\nMember Not Found. Member ID/Mention/Name you provided is invalid or bot can not see that Member'
                )
            elif isinstance(error, commands.UserNotFound):
                return await ctx.send(
                    f'**{random.choice(quote)}**\nUser Not Found. User ID/Mention/Name you provided is invalid or bot can not see that User'
                )
            elif isinstance(error, commands.ChannelNotFound):
                return await ctx.send(
                    f'**{random.choice(quote)}**\nChannel Not Found. Channel ID/Mention/Name you provided is invalid or bot can not see that Channel'
                )
            elif isinstance(error, commands.RoleNotFound):
                return await ctx.send(
                    f'**{random.choice(quote)}**\nRole Not Found. Role ID/Mention/Name you provided is invalid or bot can not see that Role'
                )
            elif isinstance(error, commands.EmojiNotFound):
                return await ctx.send(
                    f'**{random.choice(quote)}**\nEmoji Not Found. Emoji ID/Name you provided is invalid or bot can not see that Emoji'
                )

        elif isinstance(error, commands.MissingRequiredArgument):
            command = ctx.command
            return await ctx.send(
                f"**{random.choice(quote)}**\nMissing Required Argument. Please use proper syntax.```\n[p]{command.qualified_name}{'|' if command.aliases else ''}{'|'.join(command.aliases if command.aliases else '')} {command.signature}```"
            )

        elif isinstance(error, commands.MaxConcurrencyReached):
            return await ctx.send(
                f"**{random.choice(quote)}**\nMax Concurrenry Reached. This command is already running in this server. You have wait for it to finish"
            )
        
        elif isinstance(error, ParrotCheckFaliure):
            return await ctx.send(error.__str__().format(ctx=ctx))
        
        elif isinstance(error, commands.CheckAnyFailure):
            return await ctx.send(' or '.join(
                [error.__str__().format(ctx=ctx) for error in error.errors]))

        else:
            is_owner = await ctx.bot.is_owner(ctx.author)
            if is_owner: 
                tb = traceback.format_exception(type(error), error, error.__traceback__)
                tbe = "".join(tb) + ""
                er = '```py\nIgnoring exception in command {}: {}\n```'.format(ctx.command.name, tbe)
                text = await self.paste(er)
                if len(tbe) < 1800:
                    await ctx.send(er, delete_after=60)
                else: 
                    await ctx.send(text)
            else:
                ctx.send(f"**{random.choice(quote)}**\nWell this is embarrassing. For some reason **{ctx.command.qualified_name}** is not working")

def setup(bot):
    bot.add_cog(Cmd(bot))
