from __future__ import annotations
import discord

from utilities.database import parrot_db
from utilities.infraction import warn
import re
import random
import typing
from core import Parrot, Cog

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class EmojiCapsProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.data = {}  # TODO: Make cache system
        self.collection = parrot_db["server_config"]

    async def delete(self, message: discord.Message) -> None:
        try:
            await message.delete()
        except Exception:
            return

    async def get_emoji_count(self, message_content: str) -> int:
        str_count = len(re.findall(r"[\U0001f600-\U0001f650]", message_content))
        dis_count = len(
            re.findall(
                r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
                message_content,
            )
        )
        return int(str_count + dis_count)

    async def get_caps_count(self, message_content: str) -> int:
        caps_count = len(re.findall(r"[A-Z]", message_content))
        return int(caps_count)

    async def is_caps_infilterated(
        self, message: discord.Message
    ) -> typing.Optional[bool]:
        if data_c := await self.collection.find_one(
            {"_id": message.guild.id, "automod.caps.enable": {"$exists": True}}
        ):
            if not data_c["automod"]["caps"]["enable"]:
                return False
            try:
                ignore = data_c["automod"]["caps"]["channel"]
            except KeyError:
                ignore = []
            if message.channel.id in ignore:
                return False
            try:
                limit = data_c["automod"]["caps"]["limit"]
            except KeyError:
                return False
            if limit <= (await self.get_caps_count(message.content)):
                return True

    async def is_emoji_infilterated(
        self, message: discord.Message
    ) -> typing.Optional[bool]:
        if data_c := await self.collection.find_one(
            {"_id": message.guild.id, "automod.emoji.enable": {"$exists": True}}
        ):
            if not data_c["automod"]["emoji"]["enable"]:
                return False
            try:
                ignore = data_c["automod"]["emoji"]["channel"]
            except KeyError:
                ignore = []
            if message.channel.id in ignore:
                return False
            try:
                limit = data_c["automod"]["emoji"]["limit"]
            except KeyError:
                return False
            if limit <= (await self.get_emoji_count(message.content)):
                return True

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        perms = message.author.guild_permissions

        if perms.administrator or perms.manage_messages or perms.manage_channels:
            return
        caps_ = await self.is_caps_infilterated(message)
        emoj_ = await self.is_emoji_infilterated(message)
        if data := await self.collection.find_one(
            {"_id": message.guild.id, "automod.emoji.enable": {"$exists": True}}
        ):
            if emoj_:
                try:
                    to_delete = data["automod"]["emoji"]["autowarn"]["to_delete"]
                except KeyError:
                    to_delete = True

                if to_delete:
                    await message.delete(delay=0)

                try:
                    to_warn = data["automod"]["emoji"]["autowarn"]["enable"]
                except KeyError:
                    to_warn = False

                if to_warn:
                    await warn(
                        message.guild,
                        message.author,
                        "Automod: Mass Emoji",
                        moderator=self.bot.user,
                        message=message,
                        at=message.created_at,
                    )

                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Excess Emoji] [Warning]**",
                    delete_after=10,
                )
        if data := await self.collection.find_one(
            {"_id": message.guild.id, "automod.caps.enable": {"$exists": True}}
        ):
            if caps_:
                try:
                    to_delete = data["automod"]["caps"]["autowarn"]["to_delete"]
                except KeyError:
                    to_delete = True

                if to_delete:
                    await message.delete(delay=0)

                try:
                    to_warn = data["automod"]["caps"]["autowarn"]["enable"]
                except KeyError:
                    to_warn = False

                if to_warn:
                    await warn(
                        message.guild,
                        message.author,
                        "Automod: Excess Caps",
                        moderator=self.bot.user,
                        message=message,
                        at=message.created_at,
                    )

                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Excess Caps] [Warning]**",
                    delete_after=10,
                )
