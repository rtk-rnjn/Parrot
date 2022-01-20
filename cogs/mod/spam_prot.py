from __future__ import annotations

from core import Parrot, Cog

from discord.ext import commands
import discord
import random

from utilities.database import parrot_db
from utilities.infraction import warn

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class SpamProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db["server_config"]
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.member
        )

    async def delete(self, message: discord.Message) -> None:
        def check(m: discord.Message):
            return m.author.id == message.author.id

        try:
            await message.channel.purge(5, check=check)
        except discord.Forbidden:  # this is faster than `if` `else`
            pass

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        perms = message.author.guild_permissions

        if perms.administrator or perms.manage_messages or perms.manage_channels:
            return

        bucket = self.cd_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            if data := await self.collection.find_one(
                {"_id": message.guild.id, "automod.spam.enable": {"$exists": True}}
            ):
                if not data["automod"]["spam"]["enable"]:
                    return
                try:
                    ignore = data["automod"]["spam"]["channel"]
                except KeyError:
                    ignore = []

                if message.channel.id in ignore:
                    return
                try:
                    to_delete = data["automod"]["spam"]["autowarn"]["to_delete"]
                except KeyError:
                    to_delete = True

                if to_delete:
                    await self.delete(message)

                try:
                    to_warn = data["automod"]["spam"]["autowarn"]["enable"]
                except KeyError:
                    to_warn = False

                if to_warn:
                    await warn(
                        message.guild,
                        message.author,
                        "Automod: Spammed 5 messages in 5 seconds",
                        moderator=self.bot.user,
                        message=message,
                        at=message.created_at,
                    )

                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Spam Protection] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )
