from __future__ import annotations

from typing import Collection

from core import Parrot, Cog
from discord.ext import tasks
import discord
import typing

from utilities.database import parrot_db

collection = parrot_db["server_config"]


class OneWordStory(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cache = {}
        self.clear_cache.start()

    async def get_last_message(
        self, channel: discord.TextChannel
    ) -> typing.Optional[discord.Message]:
        if channel.last_message:
            return channel.last_message
        async for msg in channel.history(limit=1, oldest_first=False):
            return msg

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        data = await collection.find_one(
            {"_id": message.guild.id, "oneword": message.channel.id}
        )
        if not data:
            return

        channel = self.bot.get_channel(
            data["oneword"]
        )
        if not channel:
            return

        msg = self.get_last_message(message.channel)

        if msg and (message.author.id == msg.author.id):
            try:
                return await message.delete(reason="Can't post more than once in a row")
            except Exception:
                return await message.channel.send(
                    "Bot need manage message permission to work properly"
                )

        if message.content.split(" ") > 2:
            try:
                return await message.delete()
            except Exception:
                return await message.channel.send(
                    "Bot need manage message permission to work properly"
                )

    @tasks.loop(hours=1)
    async def clear_cache(self):
        self.cache = {}
