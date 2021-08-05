import discord
from discord.ext import commands

from utilities.paginator import Paginator
from utilities.config import SUPPORT_SERVER, INVITE, DEV_LOGO
from core import Parrot, Cog
from cogs.help.method import common_command_formatting, get_command_signature


class HelpCommand(commands.HelpCommand):
    """Shows help about the bot, a command, or a category"""
    def __init__(self, *args, **kwargs):
        super().__init__(command_attrs={
            'help':
            'Shows help about the bot, a command, or a category'
        },
                         **kwargs)

    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(str(error.original))

    async def send_command_help(self, command):
        embed = discord.Embed(colour=discord.Colour(0x55ddff))
        common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_bot_help(self, mapping):
        bot = self.context.bot

        em_list = []

        get_bot = f"[Add me to your server]({INVITE})"
        support_server = f"[Support Server]({SUPPORT_SERVER})"
        
        description = f"```\nPrefixes are '{self.context.prefix}' and '@Parrot#9209'\n```"
        
        embed = discord.Embed(color=discord.Colour(0x55ddff))
        
        embed.set_author(
            name=
            f"Server: {self.context.guild.name or self.context.author.name}",
            icon_url=self.context.guild.icon.url or self.context.me.avatar.url)
        
        embed.description = description + f"\n• {get_bot}\n• {support_server}"
        embed.set_thumbnail(url=self.context.me.avatar.url)
        for cog in bot.cogs:
            if bot.cogs[cog].get_commands() or (str(cog).lower() != 'jishaku'):
                embed.add_field(name=f"{str(cog).upper()}", value=f"```\n{bot.cogs[cog].description if bot.cogs[cog].description else 'No help available :('}\n```", inline=True)

        embed.set_footer(text="Built with ❤️ and `discord.py`",
                         icon_url=f"{DEV_LOGO}")

        em_list.append(embed)

        for cog in bot.cogs:
            if bot.cogs[cog].get_commands():

                em = discord.Embed(
                    description=
                    f"```\n{bot.cogs[cog].description if bot.cogs[cog].description else 'No help available :('}\n```\n"
                    f"**Commands**```\n{', '.join([cmd.name for cmd in bot.cogs[cog].get_commands()])}\n```",
                    color=discord.Colour(0x55ddff))
                em.set_author(name=f"COG: {str(cog).upper()}")
                em.set_footer(text="Built with ❤️ and `discord.py`",
                              icon_url=f"{DEV_LOGO}")
                em_list.append(em)
                em.set_thumbnail(url=self.context.me.avatar.url)
            else:
                pass

        paginator = Paginator(pages=em_list)
        await paginator.start(self.context)

    async def send_group_help(self, group):

        em_list = []
        cmds = list(group.commands)

        e = discord.Embed(
            color=discord.Colour(0x55ddff),
            description=
            f"Sub commands\n```\n{', '.join([cmd.name for cmd in cmds])}\n```")
        e.title = f"Help with group **{group.name}{'|'.join(group.aliases) if group.aliases else ''}**"
        e.set_footer(text="Built with ❤️ and `discord.py`",
                     icon_url=f"{DEV_LOGO}")
        e.set_thumbnail(url=self.context.me.avatar.url)
        em_list.append(e)

        for cmd in cmds:
            e = discord.Embed(
                title=cmd.name,
                description=
                f"```{cmd.help if cmd.help else 'No description.'}```\n"
                f"Usage:\n```\n[p]{group.qualified_name}{'|'.join(group.aliases) if group.aliases else ''} {cmd.name}{'|' if cmd.aliases else ''}{'|'.join(cmd.aliases if cmd.aliases else 'NA')} {cmd.signature}\n```",
                color=discord.Colour(0x55ddff))
            em_list.append(e)
            e.set_thumbnail(url=self.context.me.avatar.url)
        
        paginator = Paginator(pages=em_list)
        await paginator.start(self.context)

    async def send_cog_help(self, cog):

        em_list = []

        embed = discord.Embed(
            title=f'{str(cog.qualified_name).capitalize()} Commands',
            description=
            f"```\n{cog.description if cog.description else 'NA'}\n```",
            color=discord.Colour(0x55ddff))
        embed.set_footer(text="Built with ❤️ and `discord.py`",
                         icon_url=f"{DEV_LOGO}")
        em_list.append(embed)

        for cmd in cog.get_commands():
            if cog.get_commands():
                em = discord.Embed(title=f"Help with {cmd.name}",
                                   description=f"```\n{cmd.help}\n```",
                                   color=discord.Colour(0x55ddff))
                em.add_field(name=f"Usage",
                             value=f"```\n{get_command_signature(cmd)}\n```")
                em.add_field(
                    name="Aliases",
                    value=
                    f"```\n{', '.join(cmd.aliases if cmd.aliases else 'NA')}\n```"
                )

                em_list.append(em)
            else:
                pass

        paginator = Paginator(pages=em_list)
        await paginator.start(self.context)


class HelpCog(Cog):
    """Shows help about the bot, a command, or a category"""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = HelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.old_help_command


def setup(bot):
    bot.add_cog(HelpCog(bot))
