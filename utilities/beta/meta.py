from __future__ import annotations

from discord.ext import commands, menus

from .robopage import RoboPages
import discord

import datetime
import inspect
import itertools
from typing import Any, Dict, List, Optional, Union


def format_dt(dt, style=None):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


def format_relative(dt):
    return format_dt(dt, 'R')


class plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition('|')
        plural = plural or f'{singular}s'
        if abs(v) != 1:
            return f'{v} {plural}'
        return f'{v} {singular}'


class Prefix(commands.Converter):
    async def convert(self, ctx, argument):
        user_id = ctx.bot.user.id
        if argument.startswith((f'<@{user_id}>', f'<@!{user_id}>')):
            raise commands.BadArgument(
                'That is a reserved prefix already in use.')
        return argument


class GroupHelpPageSource(menus.ListPageSource):
    def __init__(self, group: Union[commands.Group, commands.Cog],
                 commands: List[commands.Command], *, prefix: str):
        super().__init__(entries=commands, per_page=6)
        self.group = group
        self.prefix = prefix
        self.title = f'{self.group.qualified_name} Commands'
        self.description = self.group.description

    async def format_page(self, menu, commands):
        embed = discord.Embed(title=self.title,
                              description=self.description,
                              colour=discord.Colour(0xA8B9CD))

        for command in commands:
            signature = f'{command.qualified_name} {command.signature}'
            embed.add_field(name=signature,
                            value=command.short_doc or 'No help given...',
                            inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(
                name=
                f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)'
            )

        embed.set_footer(
            text=f'Use "{self.prefix}help command" for more info on a command.'
        )
        return embed


class HelpSelectMenu(discord.ui.Select['HelpMenu']):
    def __init__(self, commands: Dict[commands.Cog, List[commands.Command]],
                 bot: commands.AutoShardedBot):
        super().__init__(
            placeholder='Select a category...',
            min_values=1,
            max_values=1,
            row=0,
        )
        self.commands = commands
        self.bot = bot
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label='Index',
            emoji='\N{WAVING HAND SIGN}',
            value='__index',
            description='The help page showing how to use the bot.',
        )
        for cog, command_ in self.commands.items():
            if not command_:
                continue
            description = cog.description.split('\n', 1)[0] or None
            emoji = getattr(cog, 'display_emoji', None)
            self.add_option(label=cog.qualified_name,
                            value=cog.qualified_name,
                            description=description,
                            emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        value = self.values[0]
        if value == '__index':
            await self.view.rebind(FrontPageSource(), interaction)
        else:
            cog = self.bot.get_cog(value)
            if cog is None:
                await interaction.response.send_message(
                    'Somehow this category does not exist?', ephemeral=True)
                return

            commands = self.commands[cog]
            if not commands:
                await interaction.response.send_message(
                    'This category has no commands for you', ephemeral=True)
                return

            source = GroupHelpPageSource(cog,
                                         commands,
                                         prefix=self.view.ctx.clean_prefix)
            await self.view.rebind(source, interaction)


class FrontPageSource(menus.PageSource):
    def is_paginating(self) -> bool:
        # This forces the buttons to appear even in the front page
        return True

    def get_max_pages(self) -> Optional[int]:
        # There's only one actual page in the front page
        # However we need at least 2 to show all the buttons
        return 2

    async def get_page(self, page_number: int) -> Any:
        # The front page is a dummy
        self.index = page_number
        return self

    def format_page(self, menu: HelpMenu, page):
        embed = discord.Embed(title='Bot Help',
                              colour=discord.Colour(0xA8B9CD))
        embed.description = inspect.cleandoc(f"""
            Hello! Welcome to the help page.
            Use "{menu.ctx.clean_prefix}help command" for more info on a command.
            Use "{menu.ctx.clean_prefix}help category" for more info on a category.
            Use the dropdown menu below to select a category.
        """)

        embed.add_field(
            name='Support Server',
            value=
            'For more help, consider joining the official server over at https://discord.gg/NEyJxM7G7f',
            inline=False,
        )

        created_at = format_dt(menu.ctx.bot.user.created_at, 'F')
        if self.index == 0:
            embed.add_field(
                name='Who are you?',
                value=
                ("The bot made by !! Ritik Ranjan [\*.*]#9230. Built with love and `discord.py`! Bot been running since "
                 f'{created_at}. Bot have features such as moderation, global-chat, and more. You can get more '
                 'information on my commands by using the dropdown below.\n\n'
                 "Bot is also open source. You can see the code on [GitHub](https://github.com/ritik0ranjan/Parrot)!"
                 ),
                inline=False,
            )
        elif self.index == 1:
            entries = (
                ('<argument>', 'This means the argument is __**required**__.'),
                ('[argument]', 'This means the argument is __**optional**__.'),
                ('[A|B]', 'This means that it can be __**either A or B**__.'),
                (
                    '[argument...]',
                    'This means you can have multiple arguments.\n'
                    'Now that you know the basics, it should be noted that...\n'
                    '__**You do not type in the brackets!**__',
                ),
            )

            embed.add_field(
                name='How do I use this bot?',
                value='Reading the bot signature is pretty simple.')

            for name, value in entries:
                embed.add_field(name=name, value=value, inline=False)

        return embed


class HelpMenu(RoboPages):
    def __init__(self, source: menus.PageSource, ctx: commands.Context):
        super().__init__(source, ctx=ctx, compact=True)

    def add_categories(
            self, commands: Dict[commands.Cog,
                                 List[commands.Command]]) -> None:
        self.clear_items()
        self.add_item(HelpSelectMenu(commands, self.ctx.bot))
        self.fill_items()

    async def rebind(self, source: menus.PageSource,
                     interaction: discord.Interaction) -> None:
        self.source = source
        self.current_page = 0

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


class PaginatedHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={
                'cooldown':
                commands.CooldownMapping.from_cooldown(
                    1, 3.0, commands.BucketType.member),
                'help':
                'Shows help about the bot, a command, or a category',
            })

    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            # Ignore missing permission errors
            if isinstance(
                    error.original,
                    discord.HTTPException) and error.original.code == 50013:
                return

            await ctx.send(str(error.original))

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = f'[{command.name}|{aliases}]'
            if parent:
                fmt = f'{parent} {fmt}'
            alias = fmt
        else:
            alias = command.name if not parent else f'{parent} {command.name}'
        return f'{alias} {command.signature}'

    async def send_bot_help(self, mapping):
        bot = self.context.bot

        def key(command) -> str:
            cog = command.cog
            return cog.qualified_name if cog else '\U0010ffff'

        entries: List[commands.Command] = await self.filter_commands(
            bot.commands, sort=True, key=key)

        all_commands: Dict[commands.Cog, List[commands.Command]] = {}
        for name, children in itertools.groupby(entries, key=key):
            if name == '\U0010ffff':
                continue

            cog = bot.get_cog(name)
            all_commands[cog] = sorted(children,
                                       key=lambda c: c.qualified_name)

        menu = HelpMenu(FrontPageSource(), ctx=self.context)
        menu.add_categories(all_commands)
        #await self.context.release()
        await menu.start()

    async def send_cog_help(self, cog):
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        menu = HelpMenu(GroupHelpPageSource(cog,
                                            entries,
                                            prefix=self.context.clean_prefix),
                        ctx=self.context)
        #await self.context.release()
        await menu.start()

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f'{command.description}\n\n{command.help}'
        else:
            embed_like.description = command.help or 'No help found...'

    async def send_command_help(self, command):
        # No pagination necessary for a single command.
        embed = discord.Embed(colour=discord.Colour(0xA8B9CD))
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group,
                                     entries,
                                     prefix=self.context.clean_prefix)
        self.common_command_formatting(source, group)
        menu = HelpMenu(source, ctx=self.context)
        #await self.context.release()
        await menu.start()


class Meta(commands.Cog):
    """Commands for utilities related to Discord or the Bot itself."""
    def __init__(self, bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = PaginatedHelpCommand()
        bot.help_command.cog = self

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='\N{WHITE QUESTION MARK ORNAMENT}')

    def cog_unload(self):
        self.bot.help_command = self.old_help_command

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)



def setup(bot):
    bot.add_cog(Meta(bot))
