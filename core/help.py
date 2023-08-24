from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands, old_menus as menus  # type: ignore
from utilities.config import PRIVACY_POLICY
from utilities.robopages import RoboPages

if TYPE_CHECKING:
    from . import Cog, Context, Parrot

__all__ = (
    "GroupHelpPageSource",
    "HelpSelectMenu",
    "FrontPageSource",
    "HelpMenu",
    "PaginatedHelpCommand",
)

DISPLAY_COG = (
    "AUTORESPONDERS",
    "CONFIGURATION",
    "AUTOMATICMODERATION",
    "DEFENSIVECONDITION",
    "FUN",
    "GAMES",
    "GIVEAWAYS",
    "HIGHLIGHT",
    "LINTER",
    "LOVE",
    "META",
    "MISC",
    "MODERATOR",
    "NASA",
    "REMINDERS",
    "RTFM",
    "SUGGESTIONS",
    "TAGS",
    "TODOS",
    "UTILS",
)


class GroupHelpPageSource(menus.ListPageSource):
    def __init__(
        self,
        group: commands.Group | Cog,
        commands_list: list[commands.Command],
        *,
        prefix: str,
    ) -> None:
        super().__init__(entries=commands_list, per_page=6)
        self.group = group
        self.prefix = prefix
        self.title = f"{self.group.qualified_name} Commands"
        self.description = self.group.description

    async def format_page(self, menu, commands_list: list[commands.Command]):
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            colour=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        for command in commands_list:
            signature = f"{command.qualified_name} {command.signature}"
            embed.add_field(
                name=f"\N{BULLET} {command.qualified_name}",
                value=f"> `{signature}`\n{command.short_doc or 'No help given for the time being...'}",
                inline=False,
            )
        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_footer(text=f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)")

        return embed


class HelpSelectMenu(discord.ui.Select["HelpMenu"]):
    def __init__(self, commands_list: dict[Cog, list[commands.Command]], bot: Parrot) -> None:
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            row=0,
        )
        self.commands = commands_list
        self.bot = bot
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label="Index",
            emoji="\N{WAVING HAND SIGN}",
            value="__index",
            description="The help page showing how to use the bot.",
        )
        for cog, command_ in self.commands.items():
            if cog.qualified_name.upper() in DISPLAY_COG and command_ and len(cog.get_commands()) != 0:
                description = cog.description.split("\n", 1)[0] or None
                emoji = getattr(cog, "display_emoji", None)
                self.add_option(
                    label=cog.qualified_name,
                    value=cog.qualified_name,
                    description=description,
                    emoji=emoji,
                )

    async def callback(self, interaction: discord.Interaction):
        if self.view is None:
            raise AssertionError
        value = self.values[0]
        if value == "__index":
            await self.view.rebind(FrontPageSource(self.bot), interaction)
        else:
            cog: Cog = self.bot.get_cog(value)  # type: ignore
            if cog is None:
                await interaction.response.send_message("Somehow this category does not exist?", ephemeral=True)
                return

            commands = self.commands[cog]
            if not commands:
                await interaction.response.send_message("This category has no commands for you", ephemeral=True)
                return

            source = GroupHelpPageSource(cog, commands, prefix=self.view.ctx.clean_prefix)
            await self.view.rebind(source, interaction)


class FrontPageSource(menus.PageSource):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    def is_paginating(self) -> bool:
        # This forces the buttons to appear even in the front page
        return True

    def get_max_pages(self) -> int | None:
        # There's only one actual page in the front page
        # However we need at least 2 to show all the buttons
        return 2

    async def get_page(self, page_number: int) -> Any:
        # The front page is a dummy
        self.index = page_number
        return self

    def format_page(self, menu: HelpMenu, page):
        embed = discord.Embed(
            title="Bot Help",
            colour=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.description = inspect.cleandoc(
            f"""
            Hello! Welcome to the help page.
            Use "`{menu.ctx.clean_prefix}help command`" for more info on a command.
            Use "`{menu.ctx.clean_prefix}help category`" for more info on a category.
            Use the dropdown menu below to select a category.

            Full documentation is available [here](https://github.com/rtk-rnjn/Parrot/wiki/Getting-Started)
            """,
        )

        embed.add_field(
            name="Support Server",
            value=f"For more help, consider joining the [official server]({self.bot.support_server})",
            inline=False,
        )

        embed.add_field(
            name="Privacy Policy",
            value=f"For the privacy policy of the bot: visit [Privacy Policy]({PRIVACY_POLICY})",
            inline=False,
        )

        created_at = discord.utils.format_dt(menu.ctx.bot.user.created_at, "F")
        if self.index == 0:
            embed.add_field(
                name="Who are you?",
                value=(
                    r"The bot made by `@ritik.ranjan` (ritik) formerly know as `!! Ritik Ranjan [*.*]#9230`. Built with love and `discord.py`! Bot been running since "
                    f"{created_at}. Bot have features such as moderation, global-chat, and more. You can get more "
                    "information on my commands by using the dropdown below.\n\n"
                    f"Bot is also open source. You can see the code on [GitHub]({self.bot.github})!"
                ),
                inline=False,
            )
        elif self.index == 1:
            entries = (
                ("<argument>", "This means the argument is __**required**__."),
                ("[argument]", "This means the argument is __**optional**__."),
                ("[A|B]", "This means that it can be __**either A or B**__."),
                (
                    "[argument...]",
                    "This means you can have multiple arguments.\n"
                    "Now that you know the basics, it should be noted that...\n"
                    "__**You do not type in the brackets!**__",
                ),
                (
                    "[--arg ]",
                    "This means you can pass flags in with `--` prefix and `arg` argument.\n"
                    "Space after `arg ` means you need to put the space. It's not specific.\n",
                ),
            )

            embed.add_field(
                name="How do I use this bot?",
                value="Reading the bot signature is pretty simple.",
            )

            for name, value in entries:
                embed.add_field(name=name, value=value, inline=False)

        return embed


class HelpMenu(RoboPages):
    def __init__(self, source: menus.PageSource, ctx: Context) -> None:
        super().__init__(source, ctx=ctx, compact=True)

    def add_categories(self, commands_list: dict[Cog, list[commands.Command]]) -> None:
        self.clear_items()
        self.add_item(HelpSelectMenu(commands_list, self.ctx.bot))
        self.fill_items()

    async def rebind(self, source: menus.PageSource, interaction: discord.Interaction) -> None:
        self.source = source
        self.current_page = 0

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


class PaginatedHelpCommand(commands.HelpCommand):
    bot: Parrot
    context: Context

    def __init__(self) -> None:
        super().__init__(
            command_attrs={
                "cooldown": commands.CooldownMapping.from_cooldown(1, 3.0, commands.BucketType.member),
                "help": "Shows help about the bot, a command, or a category",
            },
        )
        self.__all_commands: dict[Cog, list[commands.Command]] = {}

    async def on_help_command_error(self, ctx: Context, error: commands.CommandError):
        if isinstance(error, commands.CommandInvokeError):
            # Ignore missing permission errors
            if isinstance(error.original, discord.HTTPException) and error.original.code == 50013:
                return

            await ctx.send(f"Well this is embarrassing. Please tell this to developer {error.original}")

    def get_command_signature(self, command: commands.Command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = "|".join(command.aliases)
            fmt = f"[{command.name}|{aliases}]"
            if parent:
                fmt = f"{parent} {fmt}"
            alias = fmt
        else:
            alias = f"{parent} {command.name}" if parent else command.name
        return f"{alias} {command.signature}"

    async def send_bot_help(self, mapping):
        await self.context.typing()
        bot = self.context.bot

        def key(command: commands.Command) -> str:
            cog: Cog = command.cog
            return cog.qualified_name if cog else "\U0010ffff"

        # entries: List[commands.Command] = await self.filter_commands(
        #     bot.commands, sort=True, key=key
        # )
        if not self.__all_commands:
            entries = bot.cogs
            all_commands: dict[Cog, list[commands.Command]] = {}
            for real_cog in entries:
                cog: Cog = bot.get_cog(real_cog)  # type: ignore
                if cog:
                    _cmds = [c for c in cog.get_commands() if not c.hidden]
                    if cog is not None and _cmds:
                        all_commands[cog] = self.__get_all_commands(cog)

            self.__all_commands = all_commands

        menu = HelpMenu(FrontPageSource(bot), ctx=self.context)
        menu.add_categories(self.__all_commands)
        await menu.start()

    def __get_all_commands(self, group: commands.Group | Cog) -> list[commands.Command]:
        # recursive function to get all commands from a group
        all_commands = []
        if isinstance(group, commands.Cog):
            cmds = group.get_commands()
            for cmd in cmds:
                if cmd.hidden:
                    continue

                all_commands.append(cmd)

                if isinstance(cmd, commands.Group):
                    all_commands.extend(self.__get_all_commands(cmd))
        else:
            for command in group.commands:
                if command.hidden:
                    continue

                all_commands.append(command)

                if isinstance(command, commands.Group):
                    all_commands.extend(self.__get_all_commands(command))

        return sorted(all_commands, key=lambda c: c.qualified_name)

    async def send_cog_help(self, cog: Cog):
        await self.context.typing()
        # entries = await self.filter_commands(cog.get_commands(), sort=True)
        entries = self.__get_all_commands(cog)
        menu = HelpMenu(
            GroupHelpPageSource(cog, entries, prefix=self.context.clean_prefix),
            ctx=self.context,
        )

        await menu.start()

    def common_command_formatting(self, embed_like, command: commands.Command, *, message: discord.Message):
        embed_like.title = command.qualified_name.upper()
        if isinstance(embed_like, discord.Embed):
            if signature := self.get_command_signature(command):
                embed_like.add_field(
                    name="Syntax",
                    value=f"`{signature}`",
                    inline=False,
                )
            if command.aliases:
                embed_like.add_field(
                    name="Aliases",
                    value=f"`{', '.join(command.aliases)}`",
                    inline=False,
                )

        if command.description:
            embed_like.description = f"{command.description}\n\n*{command.help}*"
        else:
            embed_like.description = f'{command.help or "No help found..."}'

    async def send_command_help(self, command: commands.Command):
        await self.context.typing()
        # No pagination necessary for a single command.
        embed = discord.Embed(colour=discord.Color.blue(), timestamp=discord.utils.utcnow())
        self.common_command_formatting(embed, command, message=self.context.message)
        await self.context.send(embed=embed)

    async def send_group_help(self, group: commands.Group):
        try:
            await self.context.typing()
        except discord.Forbidden:
            await self.context.reply(f"{self.context.author.mention} preparing help menu...")
        subcommands = self.__get_all_commands(group)
        if not subcommands:
            return await self.send_command_help(group)
        entries = subcommands
        # entries = await self.filter_commands(subcommands, sort=True)
        if not entries:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group, entries, prefix=self.context.clean_prefix)
        self.common_command_formatting(source, group, message=self.context.message)
        menu = HelpMenu(source, ctx=self.context)

        await menu.start()
