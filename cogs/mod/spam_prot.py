from __future__ import annotations

import random
from typing import List, Optional

import discord
from cogs.mod.method import instant_action_parser
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.infraction import warn

with open("extra/duke_nekum.txt", encoding="utf-8", errors="ignore") as f:
    quotes = f.read().split("\n")


class SpamProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.member
        )
        self.__instant_action_parser = instant_action_parser
        self.ON_TESTING = False

    async def delete(self, message: discord.Message) -> None:
        # sourcery skip: use-contextlib-suppress
        def check(m: discord.Message) -> bool:
            return m.author.id == message.author.id

        try:
            await message.channel.purge(limit=5, check=check)
        except discord.Forbidden:  # this is faster than `if` `else`
            pass

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        # sourcery skip: low-code-quality
        if message.author.public_flags.verified_bot or not message.guild:
            return
        
        if isinstance(message.author, discord.User):
            return

        bucket = self.cd_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if not retry_after:
            return

        data = self.bot.guild_configurations_cache[message.guild.id]
        if not data["automod"]["spam"]["enable"]:
            return
        ignore: Optional[List[int]] = data["automod"]["spam"]["channel"]

        if message.channel.id in (ignore or []):
            return
        to_delete: bool = data["automod"]["spam"]["autowarn"]["to_delete"]
        ignored_roles: List[int] = data["automod"]["spam"]["role"]

        if any(role.id in ignored_roles for role in message.author.roles):
            return

        if to_delete:
            await self.delete(message)

        to_warn: bool = data["automod"]["spam"]["autowarn"]["enable"]

        ctx: Context = await self.bot.get_context(message, cls=Context)

        instant_action: Optional[str] = data["automod"]["spam"]["autowarn"]["punish"][
            "type"
        ]

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
