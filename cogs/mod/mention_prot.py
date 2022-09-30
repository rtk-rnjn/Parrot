from __future__ import annotations

import random
from typing import TYPE_CHECKING, List, Optional

import discord
from cogs.mod.method import instant_action_parser
from core import Cog, Context
from utilities.infraction import warn

if TYPE_CHECKING:
    from core import Parrot


with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class MentionProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = bot.mongo.parrot_db["server_config"]
        self.__instant_action_parser = instant_action_parser

    async def _on_message_passive(self, message: discord.Message):
        if message.author.public_flags.verified_bot or not message.guild:
            return

        data = self.bot.server_config.get(message.guild.id)
        if not data:
            return

        try:
            ignore: List[int] = data[message.guild.id]["automod"]["mention"]["channel"]
        except KeyError:
            ignore: List[int] = []

        if message.channel.id in ignore:
            return

        try:
            ignore_roles: List[int] = data[message.guild.id]["automod"]["mention"]["role"]
        except KeyError:
            ignore_roles: List[int] = []
        
        if any(role.id in ignore_roles for role in message.author.roles):
            return

        try:
            count: Optional[int] = data[message.guild.id]["automod"]["mention"]["count"]
        except KeyError:
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

        ctx: Context = await self.bot.get_context(message, cls=Context)

        try:
            instant_action: str = data["automod"]["mention"]["autowarn"]["punish"][
                "type"
            ]
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
