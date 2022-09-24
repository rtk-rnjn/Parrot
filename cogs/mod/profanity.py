from __future__ import annotations

import random
import re
from typing import Any, List

import discord
from cogs.mod.method import instant_action_parser
from core import Cog, Context, Parrot
from utilities.infraction import warn

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class Profanity(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.__instant_action_parser = instant_action_parser

    def get_bad_words(self, message) -> List[str]:
        try:
            return self.bot.server_config[message.guild.id]["automod"]["profanity"][
                "words"
            ]
        except KeyError:
            return []

    def isin(self, phrase: str, sentence: str) -> bool:
        try:
            word = re.escape(phrase)
            return re.search(rf"\b{word}\b", sentence) is not None
        except ValueError:
            return phrase in sentence

    async def _one_message_passive(self, message: discord.Message) -> Any:
        # sourcery skip: low-code-quality
        if message.author.public_flags.verified_bot or not message.guild:
            return

        bad_words = self.get_bad_words(message)

        if data := self.bot.server_config.get(message.guild.id):
            try:
                profanity: bool = data["automod"]["profanity"]["enable"]
            except KeyError:
                profanity: bool = False

            try:
                ignore: List[int] = data["automod"]["profanity"]["channel"]
            except KeyError:
                ignore: List[int] = []

            if message.channel.id in ignore:
                return

            if (not bad_words) and profanity:
                try:
                    bad_words = data["automod"]["profanity"]["words"]
                except KeyError:
                    return

            if not bad_words:
                return

            try:
                to_delete: bool = data["automod"]["profanity"]["autowarn"]["to_delete"]
            except KeyError:
                to_delete: bool = True

            if to_delete:
                await message.delete(delay=0)

            try:
                to_warn: bool = data["automod"]["profanity"]["autowarn"]["enable"]
            except KeyError:
                to_warn: bool = False

            ctx: Context = await self.bot.get_context(message, cls=Context)

            try:
                instant_action: str = data["automod"]["profanity"]["autowarn"][
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
                    "Automod: Bad words usage",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                    ctx=ctx,
                )

                if mod_cog := self.bot.get_cog("Moderator"):
                    await mod_cog.warn_task(target=message.author, ctx=ctx)

            if any(self.isin(word, message.content.lower()) for word in bad_words):
                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Blacklisted Word] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._one_message_passive(message)

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content:
            await self._one_message_passive(after)
