from __future__ import annotations
from typing import List, Optional

from core import Parrot, Cog, Context

from utilities.database import parrot_db
from utilities.infraction import warn

from discord.ext import tasks
import discord
import random

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class MentionProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db["server_config"]

    async def _on_message_passive(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return

        perms = message.author.guild_permissions

        if perms.administrator or perms.manage_messages or perms.manage_channels:
            return

        if data := self.bot.server_config.get(message.guild.id):
            try:
                ignore: List[int] = data[message.guild.id]["automod"]["mention"]["channel"]
            except KeyError:
                ignore: List[int] = []

            if message.channel.id in ignore:
                return

            try:
                count: Optional[int] = data[message.guild.id]["automod"]["mention"]["count"]
            except KeyError:
                count = None

            if not count:
                return
            try:
                to_delete: bool = data["automod"]["mention"]["autowarn"]["to_delete"]
            except KeyError:
                to_delete: bool = True

            if to_delete:
                await message.delete(delay=0)

            try:
                to_warn: bool = data["automod"]["mention"]["autowarn"]["enable"]
            except KeyError:
                to_warn: bool = False

            if to_warn:
                await warn(
                    message.guild,
                    message.author,
                    "Automod: Mass Mention",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                )
                ctx: Context = await self.bot.get_context(message, cls=Context)
                await self.bot.get_cog("Moderator").warn_task(
                    target=message.author, ctx=ctx
                )

            if len(message.mentions) >= count:
                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Mass Mention] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._on_message_passive(message)

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content:
            await self._on_message_passive(after)
