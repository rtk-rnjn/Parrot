from __future__ import annotations

from typing import Collection
import typing

from discord.ext import tasks
import discord
import random
import re
from utilities.database import parrot_db
from utilities.infraction import warn
from core import Parrot, Cog

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class Profanity(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db["server_config"]
        self.data = {}
        self.update_data.start()

    async def get_bad_words(self, message) -> typing.Optional[list]:
        try:
            return self.data[message.guild.id]
        except KeyError:
            return None

    def isin(self, phrase: str, sentence: str) -> bool:
        word = re.escape(phrase)
        pattern = rf"\b{word}\b"
        return re.search(pattern, sentence) is not None

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        perms = message.author.guild_permissions

        if perms.administrator or perms.manage_messages or perms.manage_channels:
            return
        bad_words = await self.get_bad_words(message)

        if data := await self.collection.find_one(
            {"_id": message.guild.id, "automod.profanity.enable": {"$exists": True}}
        ):
            try:
                profanity = data["automod"]["profanity"]["enable"]
            except KeyError:
                return
            try:
                ignore = data["automod"]["profanity"]["channel"]
            except KeyError:
                ignore = []

            if ignore and (message.channel.id in ignore):
                return

            if (not bad_words) and profanity:
                try:
                    bad_words = data["automod"]["profanity"]["words"]
                except KeyError:
                    return

            if not bad_words:
                return

            try:
                to_delete = data["automod"]["profanity"]["autowarn"]["to_delete"]
            except KeyError:
                to_delete = True

            if to_delete:
                await message.delete(delay=0)

            try:
                to_warn = data["automod"]["profanity"]["autowarn"]["enable"]
            except KeyError:
                to_warn = False

            if to_warn:
                await warn(
                    message.guild,
                    message.author,
                    "Automod: Bad words usage",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                )

            if any(self.isin(word, message.content.lower()) for word in bad_words):
                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Blacklisted Word] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )

    @tasks.loop(seconds=5)
    async def update_data(self):
        async for data in self.collection.find({}):
            try:
                bad_words = data["automod"]["profanity"]["words"]
            except KeyError:
                return
            self.data[data["_id"]] = bad_words
