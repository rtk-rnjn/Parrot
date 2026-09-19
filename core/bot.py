from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, override

import aiohttp
import discord
import jishaku
import pomice
from discord.ext import commands
from dotenv import load_dotenv
from watchfiles import awatch

from .help import Help as BotHelp
from .utils import ConfirmationLayout, DatabaseManager, DisambiguatorView, TimersManager

if TYPE_CHECKING:
    from cogs.reminder import Reminder

_ = load_dotenv()


DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

RESTRICTED_MODE = os.environ.get("RESTRICTED_MODE", "False").lower() in ("true", "1", "yes")
LAVALINK_PASSWORD = os.environ.get("LAVALINK_PASSWORD", "youshallnotpass")
OWNER_ID = os.getenv("OWNER_ID")

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

LOADABLE_COGS = [
    "cogs.afk",
    "cogs.birthday",
    "cogs.automod",
    "cogs.cc",
    "cogs.config",
    "cogs.events",
    "cogs.fun.easter",
    "cogs.fun.hanukkah",
    "cogs.fun.pride",
    "cogs.fun.love",
    "cogs.fun.fun",
    "cogs.games",
    "cogs.giveaway",
    "cogs.global_chat",
    "cogs.highlight",
    "cogs.hub",
    "cogs.leveling",
    "cogs.meta",
    "cogs.misc",
    "cogs.mod",
    "cogs.music",
    "cogs.nsfw",
    "cogs.owner",
    "cogs.reminder",
    "cogs.rtfm",
    "cogs.starboard",
    "cogs.tags",
    "cogs.todo",
    "cogs.telephone",
    "cogs.welcomer",
]

_log = logging.getLogger("bot.core")

lavalink_jar = Path("Lavalink.jar")
COGS_DIR = Path(__file__).resolve().parents[1] / "cogs"


class SpamSeverity(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Parrot(commands.Bot):
    DEFAULT_PREFIX = os.environ.get("DEFAULT_PREFIX", "$")

    if TYPE_CHECKING:
        user: discord.ClientUser

    def __init__(self, **kwargs) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        # intents.presences = True

        super().__init__(
            command_prefix=self.get_prefix,  # type: ignore
            intents=intents,
            chunk_guilds_at_startup=False,
            case_insensitive=True,
            activity=discord.Activity(type=discord.ActivityType.listening),
            status=discord.Status.idle,
            allowed_mentions=discord.AllowedMentions(everyone=False, replied_user=False, roles=False),
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            strip_after_prefix=True,
            shard_id=1,
            max_messages=2**12,
            owner_ids={int(OWNER_ID)} if OWNER_ID else None,
            help_command=BotHelp(),
            **kwargs,
        )
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        self.database = DatabaseManager(self)
        self.event_scheduler = TimersManager(self)

        self._started_at: datetime | None = None

        self.before_invoke(self.__before_invoke)
        self.check_once(self.__check_once)

        self._http_session: aiohttp.ClientSession | None = None

        self.lavalink_node_pool = pomice.NodePool()
        self.default_lavalink_node: pomice.Node | None = None

        self.message_cache: dict[int, discord.Message] = {}
        self._cog_autoreload_task: asyncio.Task[None] | None = None

        self.spam_control = commands.CooldownMapping.from_cooldown(3, 6, commands.BucketType.user)
        self.spam_counter = Counter[int]()
        self.temporary_ban_list: dict[int, float] = {}  # user_id -> timestamp of when the ban expires

    @staticmethod
    async def start_lavalink() -> asyncio.subprocess.Process | None:
        java = shutil.which("java")
        if java is None:
            _log.warning("Java executable not found in PATH. Lavalink will not be started.")
            return

        if not await asyncio.to_thread(lavalink_jar.exists):
            _log.warning("Lavalink.jar not found. Lavalink will not be started.")
            return

        try:
            process = await asyncio.create_subprocess_shell(
                " ".join([java, "-jar", str(lavalink_jar)]),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return process
        except Exception:
            _log.exception("Failed to start Lavalink process.")

    @override
    async def setup_hook(self) -> None:
        await self.load_extension(jishaku.__name__)

        for extention in LOADABLE_COGS:
            await self.load_extension(extention)

        self.event_scheduler.timer_task = self.loop.create_task(self.event_scheduler.dispatch_timers())
        self._cog_autoreload_task = self.loop.create_task(self._autoreload_cogs())

    @staticmethod
    def _cog_extension_paths() -> dict[Path, str]:
        paths: dict[Path, str] = {}
        for extension in LOADABLE_COGS:
            spec = importlib.util.find_spec(extension)
            if spec is None:
                _log.warning("Could not find loaded cog extension: %s", extension)
                continue

            if spec.submodule_search_locations:
                path = Path(next(iter(spec.submodule_search_locations)))
            elif spec.origin:
                path = Path(spec.origin)
            else:
                _log.warning("Could not resolve source path for loaded cog extension: %s", extension)
                continue

            paths[path.resolve()] = extension

        return paths

    async def _autoreload_cogs(self) -> None:
        extension_paths = self._cog_extension_paths()

        async for changes in awatch(COGS_DIR, debounce=3200):
            if not changes:
                continue

            extensions: set[str] = set()
            for _, changed_path in changes:
                path = await asyncio.to_thread(Path(changed_path).resolve)
                if path.suffix != ".py":
                    continue

                matches = [(root, extension) for root, extension in extension_paths.items() if path == root or root.is_dir() and root in path.parents]
                if matches:
                    extensions.add(max(matches, key=lambda match: len(match[0].parts))[1])

            for extension in extensions:
                try:
                    await self.reload_extension(extension)
                except Exception:
                    _log.exception("Could not autoreload cog extension: %s", extension)
                else:
                    _log.info("Autoreloaded cog extension: %s", extension)

    async def on_ready(self) -> None:
        _log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        if self._started_at is None:
            self._started_at = discord.utils.utcnow()
            try:
                node = await self.lavalink_node_pool.create_node(
                    bot=self,
                    host="localhost",
                    port=2333,
                    password=LAVALINK_PASSWORD,
                    identifier="MAIN",
                    loop=self.loop,
                    spotify_client_id=SPOTIFY_CLIENT_ID,
                    spotify_client_secret=SPOTIFY_CLIENT_SECRET,
                    session=self.http_session,
                )

                self.default_lavalink_node = node
            except pomice.exceptions.NodeConnectionFailure:
                pass

    @override
    async def get_prefix(self, message: discord.Message, /) -> list[str]:
        if message.guild is not None:
            prefix = await self.database.get_command_prefix(guild_id=message.guild.id)
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
                prefix = await self.database.get_command_prefix(guild_id=message.guild.id) or Parrot.DEFAULT_PREFIX
                await message.channel.send(
                    f"Prefix: `{prefix}`",
                    reference=message,
                )

            return

        await self.process_commands(message)

    async def process_commands(self, message: discord.Message, /) -> None:
        ctx: commands.Context[Parrot] = await self.get_context(message, cls=commands.Context)

        if ctx.command is None:
            return

        if ctx.author.id in self.temporary_ban_list:
            return

        spam_severity = self._check_for_spam(message)
        match spam_severity:
            case SpamSeverity.HIGH:
                self.loop.create_task(self._temporarily_ban_user(ctx.author, duration=60))
                return

            case SpamSeverity.MEDIUM:
                await ctx.reply("You are sending commands too quickly. Please slow down.", delete_after=5)
                return

            case SpamSeverity.LOW:
                await ctx.reply("You are sending commands too quickly. Please slow down.", delete_after=5)
                return

            case SpamSeverity.NONE:
                pass

        await self.invoke(ctx)

    def _check_for_spam(self, message: discord.Message) -> SpamSeverity:
        bucket = self.spam_control.get_bucket(message)
        retry_after = bucket.update_rate_limit(message.created_at.timestamp()) if bucket else None
        if retry_after is not None:
            self.spam_counter[message.author.id] += 1
            if self.spam_counter[message.author.id] >= 5:
                return SpamSeverity.HIGH

            if self.spam_counter[message.author.id] >= 3:
                return SpamSeverity.MEDIUM

            return SpamSeverity.LOW

        return SpamSeverity.NONE

    async def _temporarily_ban_user(self, user: discord.User | discord.Member, /, *, duration: float) -> None:
        if user.id in self.temporary_ban_list:
            return

        self.temporary_ban_list[user.id] = discord.utils.utcnow().timestamp() + duration
        user_id = await asyncio.sleep(duration, result=user.id)
        self.temporary_ban_list.pop(user_id, None)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.author.bot:
            return

        if before.content != after.content and await self.is_owner(after.author):
            await self.process_commands(after)

    async def __before_invoke(self, ctx: commands.Context[Parrot]) -> None:
        if ctx.guild is not None and not ctx.guild.chunked:
            await ctx.bot.wait_until_ready()
            self.loop.create_task(ctx.guild.chunk())

            await self.database.register_guild(ctx.guild.id)
            await self.database.register_user(ctx.author.id)

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

    async def confirm(
        self,
        ctx: commands.Context[Parrot],
        prompt: str = "Are you sure?",
        *,
        timeout: float = 30,
    ) -> bool:
        """Ask the command author to confirm an action in the current channel."""
        result = asyncio.get_running_loop().create_future()
        view = ConfirmationLayout(ctx.author, prompt, result)
        message = await ctx.reply(view=view)
        view.message = message

        try:
            return await asyncio.wait_for(result, timeout)
        except TimeoutError:
            await message.edit(content="Confirmation timed out.", view=None)
            return False

    @property
    def started_at(self) -> datetime:
        if self._started_at is None:
            raise RuntimeError("Bot has not started yet.")
        return self._started_at

    @property
    def reminder(self) -> Reminder:
        return self.get_cog("Reminder")  # type: ignore[return-value]

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
        entry: Callable[[T], str] = str,
        ephemeral: bool = False,
    ) -> T:
        if len(matches) == 0:
            raise ValueError("No results found.")

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 25:
            raise ValueError("Too many results... sorry.")

        view = DisambiguatorView(context, matches, entry)
        embed = discord.Embed(
            title="Found multiple choices. Please choose the correct one.",
        )
        embed.set_author(name=context.author.display_name, icon_url=context.author.display_avatar.url)

        view.message = await context.reply(
            embed=embed,
            view=view,
            ephemeral=ephemeral,
        )
        await view.wait()
        return view.selected

    async def close(self) -> None:
        if self._cog_autoreload_task is not None:
            self._cog_autoreload_task.cancel()
            try:
                await self._cog_autoreload_task
            except asyncio.CancelledError:
                pass

        await super().close()

        if self._http_session is not None:
            await self._http_session.close()

        await self.database.invalidate_redis()
        await self.database.close()
        await self.lavalink_node_pool.disconnect()

    async def __check_once(self, ctx: commands.Context[Parrot]) -> bool:
        if RESTRICTED_MODE:
            return await self.is_owner(ctx.author)
        return True

    async def get_or_fetch_message(self, channel: discord.abc.Messageable, message_id: int) -> discord.Message:
        try:
            return self.message_cache[message_id]
        except KeyError:
            message = await channel.fetch_message(message_id)
            self.message_cache[message_id] = message
            return message
