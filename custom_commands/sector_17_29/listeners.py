from __future__ import annotations

import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple, Union

import discord
from core import Cog, Parrot
from utilities.time import ShortTime

OWO_BOT = 408785106942164992
BOT_SPAM_CHANNEL = 1022374324511985715

log = logging.getLogger("custom_commands.sector_17_29.listeners")


class Sector17Listeners(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.__current_owo_prefix = "owo"

        self.allowed_channels = {BOT_SPAM_CHANNEL}
        self.allowed_guilds = set()

    async def cog_load(self) -> None:
        self.allowed_guilds.add(self.bot.server.id)  # type: ignore

    async def wait_for_owo(
        self,
        invoker_message: discord.Message,
        *,
        startswith: Union[str, Tuple[str, ...]] = "",
        in_channel: Optional[int] = None,
    ):
        def check(message: discord.Message) -> bool:
            if not message.embeds:
                return (
                    message.author.id == OWO_BOT
                    and message.channel.id == (in_channel or invoker_message.channel.id)
                    and message.content.startswith(startswith)
                    and invoker_message.author.display_name in message.content
                    and "Slow down" not in message.content
                )

            embed = message.embeds[0]
            return (
                message.author.id == OWO_BOT
                and message.channel.id == (in_channel or invoker_message.channel.id)
                and invoker_message.author.display_name in getattr(embed.author, "name")
                and "Slow down" not in message.content
            )

        try:
            return await self.bot.wait_for("message", check=check, timeout=10)
        except asyncio.TimeoutError:
            return None

    @Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        if message.guild and message.guild.id == self.bot.server.id:  # type: ignore
            log.info("Dispatching sector_17_19_message %s", message)
            self.bot.dispatch("sector_17_19_message", message)

    @Cog.listener("on_sector_17_19_message")  # why not?
    async def on_owo_message(self, message: discord.Message) -> None:
        # remove extra spaces
        content = re.sub(r" +", " ", message.content.strip()).lower()

        await asyncio.gather(
            self.change_owo_prefix(message, content),
            self.owo_hunt(message, content),
            self.owo_battle(message, content),
            self.owo_hunt_bot(message, content),
            self.owo_pray_curse(message, content),
        )

    def _get_command_list(
        self, data: Dict[str, Union[List[str], str]]
    ) -> Tuple[str, ...]:
        ls = []

        for key, value in data.items():
            if isinstance(value, list):
                for v in value:
                    ls.extend(
                        (
                            f"{self.__current_owo_prefix}{v}",
                            f"{self.__current_owo_prefix} {v}",
                            f"owo{v}",
                            f"owo {v}",
                        )
                    )
            else:
                ls.extend(
                    (
                        f"{self.__current_owo_prefix}{value}",
                        f"{self.__current_owo_prefix} {value}",
                        f"owo{value}",
                        f"owo {value}",
                    )
                )
            ls.extend(
                (
                    f"{self.__current_owo_prefix}{key}",
                    f"{self.__current_owo_prefix} {key}",
                    f"owo{key}",
                    f"owo {key}",
                )
            )

        log.debug("Command list: %s", ls)
        return tuple(set(ls))

    async def change_owo_prefix(self, message: discord.Message, content: str) -> bool:
        if content.startswith(self._get_command_list({"prefix": "prefix"})):
            owo_message = await self.wait_for_owo(message, startswith="**\N{GEAR}")

            if owo_message is not None and (
                ls := re.findall(r"`(.+)`", owo_message.content)
            ):
                self.__current_owo_prefix = ls[0]
                log.info("owo prefix changed to %s", self.__current_owo_prefix)
                await owo_message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
                return True

        return False

    async def owo_battle(self, message: discord.Message, content: str):
        if content.startswith(self._get_command_list({"battle": "b"})):
            owo_message = await self.wait_for_owo(message)
            log.info("owo battle message: %s", owo_message)
            if owo_message is not None:
                await asyncio.sleep(14.5)

                await message.channel.send(
                    f"{message.author.mention} Battle", reference=owo_message
                )

    async def owo_hunt(self, message: discord.Message, content: str):
        if content.startswith(self._get_command_list({"hunt": "h"})):
            owo_message = await self.wait_for_owo(message, startswith="**\N{SEEDLING}")
            log.info("owo hunt message: %s", owo_message)
            if owo_message is not None:
                await asyncio.sleep(14.5)

                await message.channel.send(
                    f"{message.author.mention} Hunt", reference=owo_message
                )

    async def owo_hunt_bot(self, message: discord.Message, content: str):
        if content.startswith(
            self._get_command_list({"huntbot": ["autohunt", "hb", "ah"]})
        ):
            owo_message = await self.wait_for_owo(message)

            if owo_message is not None and "BEEP BOOP" not in owo_message.content:
                return

            main = content.split("\n")[1].split(" ")[
                7
            ]  # get time # TODO: fix this temp solution
            if main == "0M":
                return
            shottime = ShortTime(main.lower())

            if owo_message is not None:
                await self.bot.create_timer(
                    expires_at=shottime.dt.timestamp(),
                    created_at=message.created_at.timestamp(),
                    content=f"{message.author.mention} your HuntBot is ready!",
                    message=message,
                    dm_notify=True,
                )

                await owo_message.add_reaction("\N{ALARM CLOCK}")

    async def owo_pray_curse(self, message: discord.Message, content: str):
        if content.startswith(self._get_command_list({"pray": "curse"})):
            owo_message = await self.wait_for_owo(
                message, startswith=("**\N{GHOST}", "**\N{PERSON WITH FOLDED HANDS}")
            )

            if owo_message is not None:
                await asyncio.sleep(300)

                await message.channel.send(
                    f"{message.author.mention} Pray/Curse", reference=owo_message
                )
