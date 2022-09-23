from __future__ import annotations

import random
from typing import List, Optional

import discord
from cogs.mod.method import instant_action_parser
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.infraction import warn

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class SpamProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.member
        )
        self.__instant_action_parser = instant_action_parser

    async def delete(self, message: discord.Message) -> None:
        def check(m: discord.Message) -> bool:
            return m.author.id == message.author.id

        try:
            await message.channel.purge(limit=5, check=check)
        except discord.Forbidden:  # this is faster than `if` `else`
            pass

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.public_flags.verified_bot or not message.guild:
            return

        bucket = self.cd_mapping.get_bucket(message)
        if bucket.update_rate_limit() and (
            data := self.bot.server_config.get(message.guild.id)
        ):
            if not data["automod"]["spam"]["enable"]:
                return
            try:
                ignore: Optional[List[int]] = data["automod"]["spam"]["channel"]
            except KeyError:
                ignore: List[int] = []

            if message.channel.id in (ignore or []):
                return
            try:
                to_delete: bool = data["automod"]["spam"]["autowarn"]["to_delete"]
            except KeyError:
                to_delete: bool = True

            if to_delete:
                await self.delete(message)

            try:
                to_warn: bool = data["automod"]["spam"]["autowarn"]["enable"]
            except KeyError:
                to_warn: bool = False

            ctx: Context = await self.bot.get_context(message, cls=Context)

            try:
                instant_action: Optional[str] = data["automod"]["spam"]["autowarn"][
                    "punish"
                ]["type"]
            except KeyError:
                instant_action: bool = False
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
                    "Automod: Spammed 5 messages in 5 seconds",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                    ctx=ctx,
                )
                if mod_cog := self.bot.get_cog("Moderator"):
                    await mod_cog.warn_task(target=message.author, ctx=ctx)

            await message.channel.send(
                f"{message.author.mention} *{random.choice(quotes)}* **[Spam Protection] {'[Warning]' if to_warn else ''}**",
                delete_after=10,
            )
