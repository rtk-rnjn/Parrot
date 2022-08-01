from __future__ import annotations

import asyncio
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

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.message_id == MESSAGE_ID and str(payload.emoji) == EMOJI:
            msg: discord.Message = await self.bot.get_or_fetch_message(channel, MESSAGE_ID)

            async def __remove_reaction(msg: discord.Message) -> None:
                try:
                    await msg.remove_reaction(EMOJI, user)
                except discord.HTTPException:
                    pass

            channel: Optional[discord.TextChannel] = self.bot.get_channel(payload.channel_id)

            if channel is None:
                return

            if then := self._cache.get(payload.user_id):
                if abs(time() - then) < 60:
                    await channel.send(
                        f"<@{payload.user_id}> You can only use the emoji once every minute.",
                        delete_after=7,
                    )
                    await __remove_reaction(msg)
                    return

            self._cache[payload.user_id] = time()

            user_id: int = payload.user_id
            user: Optional[discord.User] = await self.bot.getch(
                self.bot.get_user, self.bot.fetch_user, user_id
            )
            if user is None or user.bot:
                return

            dm: discord.DMChannel = await user.create_dm()

            async for msg in dm.history(limit=100):
                if msg.author.id == self.bot.user.id:
                    await msg.delete()

            await __remove_reaction(msg)
