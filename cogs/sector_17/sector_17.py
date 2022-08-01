from __future__ import annotations

import asyncio
import unicodedata
from time import time
from typing import TYPE_CHECKING, Dict, Optional

import discord
from core import Cog

if TYPE_CHECKING:
    from core import Parrot, Context

from utilities.config import SUPPORT_SERVER_ID

EMOJI = "\N{WASTEBASKET}"
MESSAGE_ID = 1003600244098998283


class Sector1729(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._cache: Dict[int, int] = {}

    async def cog_check(self, ctx: Context) -> bool:
        return ctx.guild is not None and ctx.guild.id == getattr(
            ctx.bot.server, "id", SUPPORT_SERVER_ID
        )

    @Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.message_id == MESSAGE_ID and (
            str(payload.emoji) == EMOJI or unicodedata.name(str(payload.emoji)) == "WASTEBASKET"
        ):
            user_id: int = payload.user_id
            user: Optional[discord.User] = await self.bot.getch(
                self.bot.get_user, self.bot.fetch_user, user_id
            )

            channel: Optional[discord.TextChannel] = self.bot.get_channel(payload.channel_id)

            if channel is None:
                return

            msg: discord.Message = await self.bot.get_or_fetch_message(channel, MESSAGE_ID)

            async def __remove_reaction(msg: discord.Message) -> None:
                for reaction in msg.reactions:
                    if unicodedata.name(reaction.emoji) == "WASTEBASKET":
                        try:
                            await msg.remove_reaction(reaction.emoji, user)
                        except discord.HTTPException:
                            pass

            if then := self._cache.get(payload.user_id):
                if abs(time() - then) < 60:
                    await channel.send(
                        f"<@{payload.user_id}> You can only use the emoji once every minute.",
                        delete_after=7,
                    )
                    await __remove_reaction(msg)
                    return

            self._cache[payload.user_id] = time() + 60

            _msg: discord.Message = await channel.send(
                f"<@{payload.user_id}> deleting messages - 0/100"
            )

            if user is None or user.bot:
                return

            dm: discord.DMChannel = await user.create_dm()

            i = 1
            async for msg in dm.history(limit=100):
                if msg.author.id == self.bot.user.id:
                    await msg.delete()
                if i % 10 == 0:
                    await _msg.edit(content=f"<@{payload.user_id}> deleting messages - {i}/100")
                i += 1

            await __remove_reaction(msg)
            await _msg.edit(content=f"<@{payload.user_id}> done!", delete_after=7)
