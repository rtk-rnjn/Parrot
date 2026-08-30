from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, overload, override

import aiohttp
import discord
import jishaku
from discord.ext import commands
from dotenv import load_dotenv
from jishaku.paginators import PaginatorEmbedInterface, PaginatorInterface

from .utils import DatabaseManager, TimersManager

if TYPE_CHECKING:
    from cogs.reminder import Reminder

_ = load_dotenv()


DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

LOADABLE_COGS = [
    "cogs.meta",
    "cogs.reminder",
    "cogs.mod",
    "cogs.config",
    "cogs.events",
    "cogs.games",
    "cogs.rtfm",
    "cogs.fun.love",
    "cogs.fun.fun",
    "cogs.misc",
]

_log = logging.getLogger("bot.core")


class Parrot(commands.Bot):
    DEFAULT_PREFIX = os.environ.get("DEFAULT_PREFIX", "$")

    def __init__(self, **kwargs) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=self.get_prefix,  # type: ignore
            intents=intents,
            chunk_guilds_at_startup=False,
            case_insensitive=True,
            activity=discord.Activity(type=discord.ActivityType.listening),
            status=discord.Status.idle,
            allowed_mentions=discord.AllowedMentions(everyone=False, replied_user=False),
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            strip_after_prefix=True,
            shard_id=1,
            max_messages=2**10,
            **kwargs,
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.database_manager = DatabaseManager(self)
        self.timer_manager = TimersManager(self)

        self.started_at: datetime | None = None

        self.before_invoke(self.__before_invoke)
        self._http_session: aiohttp.ClientSession | None = None

    @override
    async def setup_hook(self) -> None:
        await self.load_extension(jishaku.__name__)

        for extention in LOADABLE_COGS:
            await self.load_extension(extention)

        self.timer_manager.timer_task = self.loop.create_task(self.timer_manager.dispatch_timers())

    async def on_ready(self) -> None:
        if self.started_at is None:
            self.started_at = discord.utils.utcnow()

        assert self.user is not None

        _log.info("Logged in as %s (ID: %s)", self.user, self.user.id)

    @override
    async def get_prefix(self, message: discord.Message, /) -> list[str]:
        if message.guild is not None:
            prefix = await self.database_manager.get_command_prefix(guild_id=message.guild.id)
        else:
            prefix = Parrot.DEFAULT_PREFIX

        prefix = prefix or Parrot.DEFAULT_PREFIX

        return commands.when_mentioned_or(prefix)(self, message)

    @override
    async def start(self, token: str = DISCORD_BOT_TOKEN, *, reconnect: bool = True) -> None:
        await super().start(token, reconnect=reconnect)

    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or self.user is None:
            return

        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):
            if message.channel.permissions_for(message.guild.me).send_messages:
                await message.channel.send(
                    f"Prefix: `{await self.database_manager.get_command_prefix(guild_id=message.guild.id)}`",
                    reference=message,
                )

            return

        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.author.bot:
            return

        if before.content != after.content and await self.is_owner(after.author):
            await self.process_commands(after)

    async def __before_invoke(self, ctx: commands.Context[Parrot]) -> None:
        if ctx.guild is not None and not ctx.guild.chunked:
            await ctx.bot.wait_until_ready()
            self.loop.create_task(ctx.guild.chunk())

    async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> discord.Member | None:
        member = guild.get_member(member_id)
        if member is not None:
            return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    async def get_or_fetch_user(self, user_id: int) -> discord.User | None:
        user = self.get_user(user_id)
        if user is not None:
            return user

        try:
            return await self.fetch_user(user_id)
        except discord.NotFound:
            return None

    @property
    def reminder(self) -> Reminder:
        return self.get_cog("Reminder")  # type: ignore

    @property
    def http_session(self) -> aiohttp.ClientSession:
        if self._http_session is None:
            raise RuntimeError("HTTP session is not initialized")

        return self._http_session

    async def disambiguate[T](
        self,
        context: commands.Context[Parrot],
        /,
        *,
        matches: list[T],
        entry: Callable[[T], Any],
        ephemeral: bool = False,
    ) -> T:
        if len(matches) == 0:
            raise ValueError("No results found.")

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 25:
            raise ValueError("Too many results... sorry.")

        view = DisambiguatorView(context, matches, entry)
        view.message = await context.reply(
            "There are too many matches... Which one did you mean?",
            view=view,
            ephemeral=ephemeral,
        )
        await view.wait()
        return view.selected

    async def close(self) -> None:
        if self._http_session is not None:
            await self._http_session.close()

        await self.database_manager.invalidate_redis()
        await self.database_manager.close()
        await super().close()

    @overload
    @staticmethod
    async def paginate(
        ctx: commands.Context[Parrot],
        *,
        embed: bool = True,
        pages: list[str],
        suffix: str = "",
        prefix: str = "",
        max_size: int = 1900,
        linspec: str = "\n",
    ) -> PaginatorEmbedInterface: ...

    @overload
    @staticmethod
    async def paginate(
        ctx: commands.Context[Parrot],
        *,
        embed: bool = False,
        pages: list[str],
        suffix: str = "",
        prefix: str = "",
        max_size: int = 1900,
        linspec: str = "\n",
    ) -> PaginatorInterface: ...

    @staticmethod
    async def paginate(  # noqa: PLR0913
        ctx: commands.Context[Parrot],
        *,
        embed: bool = True,
        pages: list[str],
        suffix: str = "",
        prefix: str = "",
        max_size: int = 1900,
        linspec: str = "\n",
    ) -> PaginatorEmbedInterface | PaginatorInterface:
        paginator = commands.Paginator(suffix=suffix, prefix=prefix, max_size=max_size, linesep=linspec)
        for line in pages:
            paginator.add_line(line)

        if embed:
            interface = PaginatorEmbedInterface(ctx.bot, paginator, owner=ctx.author)
        else:
            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interface.send_to(ctx)
        return interface


class DisambiguatorView[T](discord.ui.View):
    message: discord.Message
    selected: T

    def __init__(self, ctx: commands.Context[Parrot], data: list[T], entry: Callable[[T], Any]):
        super().__init__()
        self.ctx = ctx
        self.data: list[T] = data

        options = []
        for i, x in enumerate(data):
            opt = entry(x)
            if not isinstance(opt, discord.SelectOption):
                opt = discord.SelectOption(label=str(opt))
            opt.value = str(i)
            options.append(opt)

        select = discord.ui.Select(options=options)

        select.callback = self.on_select_submit
        self.select = select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This select menu is not meant for you, sorry.", ephemeral=True)
            return False
        return True

    async def on_select_submit(self, interaction: discord.Interaction):
        index = int(self.select.values[0])
        self.selected = self.data[index]
        await interaction.response.defer()
        if not self.message.flags.ephemeral:
            await self.message.delete()

        self.stop()
