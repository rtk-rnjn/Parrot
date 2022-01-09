from __future__ import annotations

from typing import Collection

from core import Parrot, Cog
from discord.ext import tasks
import discord
import typing

from utilities.database import parrot_db

collection = parrot_db["server_config"]


class Counting(Cog):
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
            if not msg:
                return None
            return msg

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        data = await collection.find_one(
            {"_id": message.guild.id, "counting": message.channel.id}
        )
        if not data:
            return

        channel = self.bot.get_channel(
            data["counting"]
        )
        if not channel:
            return

        msg = self.get_last_message(message.channel)

        if msg and (message.author.id == msg.author.id):
            try:
                return await message.delete()
            except Exception:
                return await message.channel.send(
                    "Bot need manage message permission to work properly"
                )
        try:
            number = int(msg.content)
        except ValueError:
            return await message.channel.send(
                "One of the recent message was either edited or the message was sent want a number. Requesting the Admin to set the counter as to work properly"
            )

        try:
            new_number = int(message.content)
        except ValueError:
            try:
                await message.delete()
            except Exception:
                return await message.channel.send(
                    "Bot need manage message permission to work properly"
                )

        if new_number - 1 != number:
            try:
                return await message.delete()
            except Exception:
                return await message.channel.send(
                    "Bot need manage message permission to work properly"
                )

    @tasks.loop(hours=1)
    async def clear_cache(self):
        self.cache = {}
