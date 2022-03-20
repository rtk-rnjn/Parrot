from __future__ import annotations
import asyncio
from typing import Any, List, Optional

from discord.ext import tasks
import discord
import random
import re
from utilities.infraction import warn
from core import Parrot, Cog, Context
from utilities.time import ShortTime

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class Profanity(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    def get_bad_words(self, message) -> List[str]:
        try:
            return self.bot.server_config[message.guild.id]["automod"]["profanity"][
                "words"
            ]
        except KeyError:
            return []

    def isin(self, phrase: str, sentence: str) -> bool:
        word = re.escape(phrase)
        pattern = rf"\b{word}\b"
        return re.search(pattern, sentence) is not None

    async def _one_message_passive(self, message: discord.Message) -> Any:
        if message.author.bot or (not message.guild):
            return

        perms = message.author.guild_permissions

        if perms.administrator or perms.manage_messages or perms.manage_channels:
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
                pass
            else:
                await self.__instant_action_parser(
                    name=instant_action,
                    ctx=ctx,
                    message=message,
                    **data["automod"]["profanity"]["autowarn"]["punish"],
                )

            if to_warn:
                await warn(
                    message.guild,
                    message.author,
                    "Automod: Bad words usage",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                    ctx=ctx,
                )

                await self.bot.get_cog("Moderator").warn_task(
                    target=message.author, ctx=ctx
                )

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

    async def __instant_action_parser(
        self, *, name: str, ctx: Context, message: discord.Message, **kw
    ):
        PUNISH = [
            "ban",
            "tempban",
            "kick",
            "timeout",
            "mute",
        ]

        if name not in PUNISH:
            return

        if kw.get("duration"):
            try:
                duration = ShortTime(kw["duration"])
            except Exception:
                duration = None
        else:
            duration = None

        if name == "ban":
            try:
                await ctx.guild.ban(
                    message.author, reason=f"Auto mod: Profanity protection"
                )
            except (discord.Forbidden, discord.NotFound):
                pass

        if name == "tempban":
            try:
                await ctx.guild.ban(
                    message.author, reason=f"Auto mod: Profanity protection"
                )
            except (discord.Forbidden, discord.NotFound):
                pass
            else:
                mod_action = {
                    "action": "UNBAN",
                    "member": message.author.id,
                    "reason": f"Auto mod: Automatic tempban action",
                    "guild": ctx.guild.id,
                }
                cog = self.bot.get_cog("Utils")
                await cog.create_timer(
                    expires_at=duration.dt.timestamp(),
                    created_at=discord.utils.utcnow().timestamp(),
                    message=ctx.message,
                    mod_action=mod_action,
                )

        if name == "kick":
            try:
                await message.author.kick(reason="Auto mod: Profanity protection")
            except (discord.Forbidden, discord.NotFound):
                pass

        if name in ("timeout", "mute"):
            try:
                if duration:
                    await message.author.edit(
                        timed_out_until=duration.dt,
                        reason=f"Auto mod: Profanity protection",
                    )
                else:
                    muted = await ctx.muterole()
                    if not muted:
                        return
                    await message.author.add_roles(
                        muted,
                        reason=f"Auto mod: Profanity protection",
                    )
            except (discord.Forbidden, discord.NotFound):
                pass
