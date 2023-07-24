from __future__ import annotations

import logging
from asyncio import sleep

import discord
from core import Cog, Parrot

# fmt: off
CAPTURE_CODES = {
    -999: "EMERGENCY_REVOKE_TOKEN",
    999 : "EMERGENCY_SHUTDOWN",
    1   : "EMERGENCY_UNLOAD_ALL_COGS",
    2   : "EMERGENCY_FORCE_MAINTAINCE_ON",
    3   : "EMERGENCY_ADD_OWNER",
}
# fmt: on

INVOCATION_PREFIX = ">>EMERGENCY>>"
log = logging.getLogger("cogs.owner.listener")


class OwnerListener(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @Cog.listener("on_message")
    async def on_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        owner = self.bot.owner_id
        owner_ids = self.bot.owner_ids

        author_id = message.author.id

        if (owner and author_id == owner) or (owner_ids and author_id in owner_ids):
            self.bot.dispatch("owner_message", message)

    @Cog.listener("on_owner_message")
    async def owner_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if message.content.startswith(INVOCATION_PREFIX):
            code, *args = message.content[13:].split(" ")
            func_name = CAPTURE_CODES.get(int(code), "").lower()

            try:
                await message.channel.send(f"Initiating {func_name.upper()} in **10 seconds**. This action can not undone")
            except Exception:
                pass

            await sleep(10.1)

            func = getattr(self, func_name)
            if args:
                await func(args[0])
            else:
                await func()

            try:
                await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            except Exception:
                pass

    async def emergency_shutdown(self):
        log.critical("closing due to emergency")
        await self.bot.close()

    async def emergency_unload_all_cogs(self):
        log.critical("removing due to emergency")
        for name, _cog in self.bot.cogs.items():
            await self.bot.remove_cog(name)

    async def emergency_force_maintaince_on(self):
        log.critical("forced under maintainance")
        self.bot.UNDER_MAINTENANCE = True

    async def emergency_add_owner(self, owner_id: int):
        log.critical("adding %s to owner_id", owner_id)
        if isinstance(self.bot.owner_ids, set):
            self.bot.owner_ids.add(owner_id)
