from __future__ import annotations
from typing import List
import discord
import random

from utilities.infraction import warn
from utilities.regex import LINKS_NO_PROTOCOLS, LINKS_RE

from core import Parrot, Cog, Context

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class LinkProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = bot.mongo.parrot_db["server_config"]

    def has_links(self, message_content: str) -> bool:
        url1 = LINKS_NO_PROTOCOLS.search(message_content)
        url2 = LINKS_RE.search(message_content)
        return bool(url1 or url2)

    async def _message_passive(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return

        perms = message.author.guild_permissions

        if perms.administrator or perms.manage_messages or perms.manage_channels:
            return
        if data := self.bot.server_config.get(message.guild.id):
            prot: bool = data["automod"]["antilinks"]["enable"]

            if not prot:
                return

            try:
                whitelist: List[str] = data["automod"]["antilinks"]["whitelist"]
            except KeyError:
                pass

            try:
                ignore: List[int] = data["automod"]["antilinks"]["channel"]
            except KeyError:
                pass

            if message.channel.id in ignore:
                return

            if any(temp in message.content for temp in whitelist):
                return
            try:
                to_delete: bool = data["automod"]["antilinks"]["autowarn"]["to_delete"]
            except KeyError:
                to_delete: bool = True

            if to_delete:
                await message.delete(delay=0)

            try:
                to_warn: bool = data["automod"]["antilinks"]["autowarn"]["enable"]
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
                await self.bot.get_cog("Moderator").warn_task(target=message.author, ctx=ctx)
            has_links = self.has_links(message.content)

            if has_links:
                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Links Protection] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._message_passive(message)

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content:
            await self._message_passive(after)
