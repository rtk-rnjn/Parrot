from __future__ import annotations

import random
import re
from typing import List, Optional

import discord
from cogs.mod.method import instant_action_parser
from core import Cog, Context, Parrot
from utilities.infraction import warn
from utilities.regex import LINKS_NO_PROTOCOLS, LINKS_RE

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class LinkProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = bot.mongo.parrot_db["server_config"]
        self.__instant_action_parser = instant_action_parser

    def has_links(self, message_content: str) -> List:
        return LINKS_RE.findall(message_content)

    async def _message_passive(self, message: discord.Message):
        # sourcery skip: low-code-quality
        if message.author.public_flags.verified_bot or not message.guild:
            return

        if (data := self.bot.server_config.get(message.guild.id)) and (
            _links := self.has_links(message.content)
        ):
            prot: Optional[bool] = data["automod"]["antilinks"]["enable"]

            if not prot:
                return

            try:
                whitelist: List[str] = data["automod"]["antilinks"]["whitelist"]
            except KeyError:
                whitelist = []

            try:
                ignore: List[int] = data["automod"]["antilinks"]["channel"]
            except KeyError:
                ignore = []

            if message.channel.id in ignore:
                return

            for link in _links:
                if not whitelist:
                    break

                for temp in whitelist:
                    if re.match(temp, link):
                        return

            try:
                to_delete: Optional[bool] = data["automod"]["antilinks"]["autowarn"][
                    "to_delete"
                ]
            except KeyError:
                to_delete: bool = True

            if to_delete:
                await message.delete(delay=0)

            try:
                to_warn: Optional[bool] = data["automod"]["antilinks"]["autowarn"][
                    "enable"
                ]
            except KeyError:
                to_warn: bool = False

            ctx: Context[Parrot] = await self.bot.get_context(message, cls=Context)

            try:
                instant_action: str = data["automod"]["antilinks"]["autowarn"][
                    "punish"
                ]["type"]
            except KeyError:
                instant_action = False
            else:
                if instant_action and to_warn:
                    await self.__instant_action_parser(
                        name=instant_action,
                        ctx=ctx,
                        message=message,
                        **data["automod"]["mention"]["autowarn"]["punish"],
                    )

            if to_warn and not instant_action:
                await warn(
                    message.guild,
                    message.author,
                    "Automod: Mass Mention",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                    ctx=ctx,
                )

                if mod_cog := self.bot.get_cog("Moderator"):
                    await mod_cog.warn_task(target=message.author, ctx=ctx)

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
