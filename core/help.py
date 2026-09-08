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

if TYPE_CHECKING:
    from .bot import Parrot

BASIC_USAGE = """
1. <foo> - This argument is mandatory
2. <foos...> - This argument is mandatory and can take multiple values
3. [foo] - This argument is optional
4. [foos...] - This argument is optional and can take multiple values
5. [foo=bar] - This argument is optional and has a default value of `bar`
6. [foo|bar] - This argument is optional so you can either use foo or bar, or don't specify it at all

Additionally, the bot uses converters which makes specifying roles, members, channels etc, easy and fool-proof. When asked to specify a member, you can provide it a mention, an id, a name or a nickname. This principle works for every single command where applicable.

Note: Do not literally type out `<` `>` `[` `]` `|` etc.
"""

BOT_OWNER_ID = os.environ["OWNER_ID"]


class Help(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__(command_attrs={"help": "Shows this message.", "description": "Shows this message.", "aliases": ["h", "welp", "commands"]})

    def format_commit(self, commit: pygit2.Commit):
        short, _, _ = commit.message.partition("\n")
        short_sha2 = str(commit.id)[:6]
        commit_tz = arrow.now().to("local").tzinfo
        commit_time = arrow.Arrow.fromtimestamp(commit.commit_time).to("local").astimezone(commit_tz)
        offset = discord.utils.format_dt(commit_time, "R")

        return f"[`{short_sha2}`](https://github.com/rtk-rnjn/Parrot/commit/{str(commit.id)}) {short} ({offset})"

    def get_last_commits(self, count=3) -> str | None:
        if not os.path.isdir(".git"):
            return
        repo = pygit2.Repository(".git")
        commits = list(itertools.islice(repo.walk(repo.head.target), count))
        return "\n".join(self.format_commit(c) for c in commits)

    async def send_bot_help(self, mapping: dict[commands.Cog | None, list[commands.Command]]) -> None:
        context: commands.Context[Parrot] = self.context  # pyright: ignore[reportAssignmentType]
        prefix = context.clean_prefix
        owner = await context.bot.fetch_user(int(BOT_OWNER_ID))
        revision = self.get_last_commits(3)
        process = psutil.Process()
        memory_usage = process.memory_full_info().uss / 1024**2
        cpu_usage = process.cpu_percent() / psutil.cpu_count()

        text = 0
        voice = 0
        guilds = 0
        total_members = 0
        for guild in context.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count or 0
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel | discord.StageChannel):
                    voice += 1

        embed = (
            discord.Embed(
                title=f"{context.bot.user.name} Help",
                description=inspect.cleandoc(
                    f"""
                    Use {prefix}help <command> for more information on a command.
                    Use {prefix}help <category> for more information on a category.
                    """,
                ),
            )
            .set_author(name=str(owner), icon_url=owner.display_avatar.url)
            .add_field(name="Members", value=f"{total_members} total")
            .add_field(
                name="Channels",
                value=f"{text + voice} total\n{text} text\n{voice} voice",
            )
            .add_field(name="Process", value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU")
            .add_field(name="Guilds", value=guilds)
            .add_field(name="Bot Version", value="1.0 - rewrite")
            .add_field(name="Uptime", value=discord.utils.format_dt(context.bot.started_at, "R"))
        )

        await context.reply(embed=embed)
