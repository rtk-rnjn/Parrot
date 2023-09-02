from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter
from collections.abc import Callable
from functools import wraps
from typing import Literal
from weakref import WeakValueDictionary

import discord
from core import Cog, Parrot
from utilities.time import ShortTime

OWO_BOT = 408785106942164992
SECTOR_BOT_SPAM_CHANNEL = 1022374324511985715
QUOTIENT_HQ_PLAYGROUND = 829953394499780638
QUOTIENT_HQ = 746337818388987967


log = logging.getLogger("custom_commands.listeners")

OWO_COOLDOWN = re.compile(r"(\*\*⏱ )\|( .+)(\*\*!)( Slow down and try the command again )(\*\*)((<t:)(\d+)(:R>)?)(\*\*)")


def owo_lock() -> Callable:
    def wrap(func: Callable) -> Callable | None:
        func.__locks = WeakValueDictionary()

        @wraps(func)
        async def inner(self: Callable, message: discord.Message, *args, **kwargs) -> Callable | None:
            lock = func.__locks.setdefault(message.author.id, asyncio.Lock())
            if lock.locked():
                return

            async with func.__locks.setdefault(message.author.id, asyncio.Lock()):
                return await func(self, message, *args, **kwargs)

        return inner

    return wrap


class Sector17Listeners(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.__current_owo_prefix = "o"

        self.allowed_channels = {SECTOR_BOT_SPAM_CHANNEL, QUOTIENT_HQ_PLAYGROUND}
        self.allowed_guilds = set()

        self.counter: dict[int, int] = Counter()
        # {user_id: count}
        # every user must have a count of 1 or 0

    async def cog_load(self) -> None:
        self.allowed_guilds.add(self.bot.server.id)

    async def wait_for_owo(
        self,
        invoker_message: discord.Message,
        *,
        startswith: str | tuple[str, ...] = "",
        in_channel: int | None = None,
        message_type: Literal["message", "embed"] = "message",
    ):
        count = self.counter.get(invoker_message.author.id, 0)
        if count == 1:
            return None

        def check(message: discord.Message) -> bool:
            if not message.embeds and message_type == "message":
                return (
                    message.author.id == OWO_BOT
                    and message.channel.id == (in_channel or invoker_message.channel.id)
                    and message.content.startswith(startswith)
                    and invoker_message.author.display_name in message.content
                    and not OWO_COOLDOWN.search(message.content)
                )
            elif message_type == "embed":
                if not message.embeds:
                    return False

                embed = message.embeds[0]
                return (
                    message.author.id == OWO_BOT
                    and message.channel.id == (in_channel or invoker_message.channel.id)
                    and invoker_message.author.display_name in (embed.author.name or "")
                    and "Slow down" not in message.content
                )
            return False

        try:
            return await self.bot.wait_for("message", check=check, timeout=10)
        except asyncio.TimeoutError:
            return None

    @Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if message.guild is None:
            return

        if message.guild.id == self.bot.server.id:
            self.bot.dispatch("sector_17_19_message", message)

        if message.guild.id == QUOTIENT_HQ:
            self.bot.dispatch("quotient_hq_message", message)

    @Cog.listener("on_quotient_hq_message")
    async def on_quotient_hq_message(self, message: discord.Message) -> None:
        if message.channel.id != QUOTIENT_HQ_PLAYGROUND:
            return

        if message.author.bot:
            return

        await self.__owo_parser(message)

    @Cog.listener("on_sector_17_19_message")  # why not?
    async def on_owo_message(self, message: discord.Message) -> None:
        # remove extra spaces
        await self.__owo_parser(message)

    async def __owo_parser(self, message: discord.Message) -> None:
        content = re.sub(r" +", " ", message.content.strip()).lower()

        await asyncio.gather(
            self.change_owo_prefix(message, content),
            self.owo_hunt(message, content),
            self.owo_battle(message, content),
            self.owo_hunt_bot(message, content),
            self.owo_pray_curse(message, content),
            self.owo_daily(message, content),
        )

    def _get_command_list(self, content: str, data: dict[str, list[str] | str]) -> dict[str, str] | None:
        prefixes = "|".join(list({"owo", self.__current_owo_prefix}))

        cmds = []
        for commands, aliases in data.items():
            if isinstance(aliases, list):
                cmds.extend(aliases)
            else:
                cmds.append(aliases)

            cmds.append(commands)

        cmds = "|".join(set(cmds))

        regex = rf"(?P<prefix>{prefixes})\s*(?P<command>{cmds})$"

        if match := re.search(regex, content):
            return match.groupdict()

    async def change_owo_prefix(self, message: discord.Message, content: str) -> bool | None:
        if not self._get_command_list(content, {"prefix": "prefix"}):
            return

        owo_message = await self.wait_for_owo(message, startswith="**\N{GEAR}")

        if owo_message is not None and (ls := re.findall(r"`(.+)`", owo_message.content)):
            self.__current_owo_prefix = ls[0]
            log.info("owo prefix changed to %s", self.__current_owo_prefix)
            await owo_message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            return True

        return False

    @owo_lock()
    async def owo_battle(self, message: discord.Message, content: str):
        if not self._get_command_list(content, {"battle": "b"}):
            return
        owo_message = await self.wait_for_owo(message, message_type="embed")
        if owo_message is not None:
            await asyncio.sleep(14.5)

            await message.channel.send(f"{message.author.mention} Battle", reference=owo_message)

    @owo_lock()
    async def owo_hunt(self, message: discord.Message, content: str):
        if not self._get_command_list(content, {"hunt": "h"}):
            return
        owo_message = await self.wait_for_owo(message, startswith="**\N{SEEDLING}")
        if owo_message is not None:
            await asyncio.sleep(14.5)

            await message.channel.send(f"{message.author.mention} Hunt", reference=owo_message)

    async def owo_hunt_bot(self, message: discord.Message, content: str):
        if not self._get_command_list(content, {"huntbot": ["autohunt", "hb", "ah"]}):
            return
        owo_message = await self.wait_for_owo(message)

        if (
            (owo_message is not None)
            and ("BEEP BOOP" not in owo_message.content)
            and ("YOU SPENT" not in owo_message.content)
        ):
            return

        if owo_message is not None and owo_message.embeds:
            return

        try:
            if owo_message is not None:
                main = owo_message.content.split("\n")[1].split(" ")[7]
            else:
                main = "0M"
        except IndexError:
            return

        if main == "0M":
            return

        try:
            shottime = ShortTime(main.lower())
        except ValueError:
            return

        if owo_message is not None:
            await self.bot.create_timer(
                expires_at=shottime.dt.timestamp(),
                created_at=message.created_at.timestamp(),
                content=f"{message.author.mention} your HuntBot is ready!",
                message=message,
                dm_notify=True,
            )

            await owo_message.add_reaction("\N{ALARM CLOCK}")

    @owo_lock()
    async def owo_pray_curse(self, message: discord.Message, content: str) -> None:
        if not self._get_command_list(content, {"pray": "curse"}):
            return
        owo_message = await self.wait_for_owo(message, startswith=("**\N{GHOST}", "**\N{PERSON WITH FOLDED HANDS}"))

        if owo_message is not None:
            await asyncio.sleep(300)

            await message.channel.send(f"{message.author.mention} Pray/Curse", reference=owo_message)

    async def owo_daily(self, message: discord.Message, content: str):
        if not self._get_command_list(content, {"daily": "daily"}):
            return
        owo_message = await self.wait_for_owo(message, startswith="\N{MONEY BAG}")
        if owo_message is not None:
            lines = owo_message.content.split("\n")
            time_string = lines[-1].split(":")[1].lower().replace(" ", "")
            try:
                timestamp = ShortTime(time_string).dt.timestamp()
            except ValueError:
                timestamp = owo_message.created_at.timestamp() + 60 * 60 * 24

            await self.bot.create_timer(
                expires_at=timestamp,
                created_at=message.created_at.timestamp(),
                content=f"{message.author.mention} your Daily is ready!",
                message=message,
                dm_notify=False,
            )

            await owo_message.add_reaction("\N{ALARM CLOCK}")
