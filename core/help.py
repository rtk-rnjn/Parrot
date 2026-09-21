from __future__ import annotations

import inspect
import itertools
import os
from typing import TYPE_CHECKING

import arrow
import discord
import psutil
import pygit2
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

if TYPE_CHECKING:
    from .bot import Parrot


__all__ = ("Help",)

BASIC_USAGE = """
1. <foo> - This argument is mandatory
2. <foos...> - This argument is mandatory and can take multiple values
3. [foo] - This argument is optional
4. [foos...] - This argument is optional and can take multiple values
5. [foo=bar] - This argument is optional and has a default value of `bar`
6. [foo|bar] - This argument is optional so you can either use foo or bar, or don't specify it at all

Additionally, the bot uses converters which makes specifying roles, members, channels etc, easy and fool-proof. When asked to specify a member, you can provide it a mention, an id, a name or a nickname.

Note: Do not literally type out `<` `>` `[` `]` `|` etc.
"""

BOT_OWNER_ID = os.environ["OWNER_ID"]


class Help(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__(
            command_attrs={
                "help": "Shows this message.",
                "description": "Shows this message.",
                "aliases": ["h", "welp", "commands"],
            },
        )

    def format_commit(self, commit: pygit2.Commit) -> str:
        short, _, _ = commit.message.partition("\n")
        short_sha = str(commit.id)[:6]

        commit_tz = arrow.now().to("local").tzinfo
        commit_time = arrow.Arrow.fromtimestamp(commit.commit_time).to("local").astimezone(commit_tz)

        offset = discord.utils.format_dt(commit_time, "R")

        capped_short = short[:50] + "..." if len(short) > 50 else short

        return f"[`{short_sha}`](https://github.com/rtk-rnjn/Parrot/commit/{commit.id}) {capped_short} ({offset})"

    def get_last_commits(self, count: int = 3) -> str | None:
        if not os.path.isdir(".git"):
            return None

        repo = pygit2.Repository(".git")
        commits = itertools.islice(repo.walk(repo.head.target), count)

        return "\n".join(self.format_commit(commit) for commit in commits)

    def get_command_signature(self, command: commands.Command) -> str:
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}".strip()

    def make_command_embed(self, command: commands.Command) -> discord.Embed:
        signature = self.get_command_signature(command)

        embed = discord.Embed(
            title=f"{self.clean_prefix}{command.qualified_name}",
            description=self.command_description(command),
            colour=discord.Colour.blurple(),
        )

        embed.add_field(
            name="Usage",
            value=f"```text\n{signature}\n```",
            inline=False,
        )

        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{self.clean_prefix}{alias}`" for alias in command.aliases),
                inline=False,
            )

        if isinstance(command, commands.Group):
            subcommands = [child for child in command.commands if not child.hidden]

            if subcommands:
                embed.add_field(
                    name="Subcommands",
                    value="\n".join(f"`{child.name}` — {self.command_description(child)}" for child in subcommands),
                    inline=False,
                )

        return embed

    async def send_bot_help(self, mapping: dict[commands.Cog | None, list[commands.Command]]) -> None:
        context: commands.Context[Parrot] = self.context  # pyright: ignore[reportAssignmentType]
        prefix = context.clean_prefix

        owner = await context.bot.fetch_user(int(BOT_OWNER_ID))
        revision = self.get_last_commits()

        process = psutil.Process()
        memory_usage = process.memory_full_info().uss / 1024**2
        cpu_usage = process.cpu_percent() / (psutil.cpu_count() or 1)

        text_channels = 0
        voice_channels = 0
        guilds = 0
        total_members = 0

        for guild in context.bot.guilds:
            guilds += 1

            if guild.unavailable:
                continue

            total_members += guild.member_count or 0

            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text_channels += 1
                elif isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    voice_channels += 1

        embed = (
            discord.Embed(
                title=f"{context.bot.user.name} Help",
                description=inspect.cleandoc(
                    f"""
                Use `{prefix}help <command>` for more information on a command.
                Use `{prefix}help <category>` for more information on a category.
                """,
                ),
                colour=discord.Colour.blurple(),
            )
            .add_field(name="Bot Version", value=context.bot.VERSION)
            .add_field(name="Uptime", value=discord.utils.format_dt(context.bot.started_at, "R"))
            .add_field(name="Members", value=f"{total_members:,} total\n{len(context.bot.users):,} cached")
            .add_field(name="Channels", value=(f"{text_channels + voice_channels:,} total\n{text_channels:,} text\n{voice_channels:,} voice"))
            .add_field(name="Guilds", value=f"{guilds:,}")
            .add_field(name="Process", value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU")
        )

        if revision:
            embed.add_field(
                name="Recent Commits",
                value=revision,
                inline=False,
            )

        await context.reply(embed=embed)

    async def send_command_help(
        self,
        command: commands.Command,
    ) -> None:
        embed = discord.Embed(
            title=f"{self.clean_prefix}{command.qualified_name}",
            description=self.command_description(command),
            colour=discord.Colour.blurple(),
        )

        embed.add_field(
            name="Usage",
            value=f"```text\n{self.get_command_signature(command)}\n```",
            inline=False,
        )

        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{self.clean_prefix}{alias}`" for alias in command.aliases),
                inline=False,
            )

        examples = command.extras.get("examples")
        if examples is not None and isinstance(examples, list) and examples:
            embed.add_field(
                name="Examples",
                value="\n".join(f"`{self.clean_prefix}{example}`" for example in examples),
                inline=False,
            )

        usage_demo_gif = command.extras.get("usage_demo")
        if usage_demo_gif is not None and isinstance(usage_demo_gif, str) and usage_demo_gif:
            embed.set_image(url=usage_demo_gif)

        await self.context.reply(embed=embed)

    async def send_group_help(
        self,
        group: commands.Group,
    ) -> None:
        embed = discord.Embed(
            title=f"{self.clean_prefix}{group.qualified_name}",
            description=self.command_description(group),
            colour=discord.Colour.blurple(),
        )

        embed.add_field(
            name="Usage",
            value=f"```text\n{self.get_command_signature(group)}\n```",
            inline=False,
        )

        commands_list = await self.filter_commands(
            group.commands,
            sort=True,
        )

        if commands_list:
            embed.add_field(
                name="Subcommands",
                value="\n".join(f"`{command.name}` — {self.command_description(command)}" for command in commands_list if not command.hidden),
                inline=False,
            )

        if group.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{self.clean_prefix}{alias}`" for alias in group.aliases),
                inline=False,
            )

        await self.context.reply(embed=embed)

    async def send_cog_help(
        self,
        cog: commands.Cog,
    ) -> None:
        commands_list = await self.filter_commands(
            cog.get_commands(),
            sort=True,
        )

        embed = discord.Embed(
            title=cog.qualified_name,
            description=cog.description or "No description provided.",
            colour=discord.Colour.blurple(),
        )

        if commands_list:
            embed.add_field(
                name="Commands",
                value="\n".join(f"`{command.name}` — {self.command_description(command)}" for command in commands_list if not command.hidden),
                inline=False,
            )

        await self.context.reply(embed=embed)

    async def send_error(self, error: str) -> None:
        embed = discord.Embed(
            title="Help",
            description=error,
            colour=discord.Colour.red(),
        )

        await self.context.reply(embed=embed)

    @property
    def clean_prefix(self) -> str:
        return self.context.clean_prefix if self.context else self.clean_prefix
