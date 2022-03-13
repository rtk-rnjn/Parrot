from __future__ import annotations
import discord
import random

from utilities.database import parrot_db
from utilities.infraction import warn
from utilities.regex import LINKS_NO_PROTOCOLS, LINKS_RE

from core import Parrot, Cog, Context

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class LinkProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db["server_config"]

    async def has_links(self, message_content: str) -> bool:
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
            prot = data["automod"]["antilinks"]["enable"]

            if not prot:
                return

            try:
                whitelist = data["automod"]["antilinks"]["whitelist"]
            except KeyError:
                pass

            try:
                ignore = data["automod"]["antilinks"]["channel"]
            except KeyError:
                pass

            if message.channel.id in ignore:
                return

            if any(temp in message.content for temp in whitelist):
                return
            try:
                to_delete = data["automod"]["antilinks"]["autowarn"]["to_delete"]
            except KeyError:
                to_delete = True

            if to_delete:
                await message.delete(delay=0)

            try:
                to_warn = data["automod"]["antilinks"]["autowarn"]["enable"]
            except KeyError:
                to_warn = False

            if to_warn:
                await warn(
                    message.guild,
                    message.author,
                    "Automod: Mass Mention",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                )
                ctx = await self.bot.get_context(message, cls=Context)
                await self.bot.get_cog("Moderator").warn(target=message.author, cls=ctx)
            has_links = await self.has_links(message.content)

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
