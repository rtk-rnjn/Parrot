from __future__ import annotations

from typing import List, Optional

from core import Parrot, Cog, Context

from utilities.infraction import warn
from utilities.time import ShortTime
import discord
import random

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class MentionProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = bot.mongo.parrot_db["server_config"]

    async def _on_message_passive(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return

        perms = message.author.guild_permissions

        if perms.administrator or perms.manage_messages or perms.manage_channels:
            return

        if data := self.bot.server_config.get(message.guild.id):
            try:
                ignore: List[int] = data[message.guild.id]["automod"]["mention"][
                    "channel"
                ]
            except KeyError:
                ignore: List[int] = []

            if message.channel.id in ignore:
                return

            try:
                count: Optional[int] = data[message.guild.id]["automod"]["mention"][
                    "count"
                ]
            except KeyError:
                count = None

            if not count:
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
                pass
            else:
                if instant_action and to_warn:
                    await self.__instant_action_parser(
                        name=instant_action,
                        ctx=ctx,
                        message=message,
                        **data["automod"]["mention"]["autowarn"]["punish"],
                    )
                    return

            if to_warn:
                await warn(
                    message.guild,
                    message.author,
                    "Automod: Mass Mention",
                    moderator=self.bot.user,
                    message=message,
                    at=message.created_at,
                    ctx=ctx,
                )

                await self.bot.get_cog("Moderator").warn_task(
                    target=message.author, ctx=ctx
                )

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
                    message.author, reason="Auto mod: Mention protection"
                )
            except (discord.Forbidden, discord.NotFound):
                pass

        if name == "tempban":
            try:
                await ctx.guild.ban(
                    message.author, reason="Auto mod: Mention protection"
                )
            except (discord.Forbidden, discord.NotFound):
                pass
            else:
                mod_action = {
                    "action": "UNBAN",
                    "member": message.author.id,
                    "reason": "Auto mod: Automatic tempban action",
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
                await message.author.kick(reason="Auto mod: Mention protection")
            except (discord.Forbidden, discord.NotFound):
                pass

        if name in ("timeout", "mute"):
            try:
                if duration:
                    await message.author.edit(
                        timed_out_until=duration.dt,
                        reason="Auto mod: Mention protection",
                    )
                else:
                    muted = await ctx.muterole()
                    if not muted:
                        return
                    await message.author.add_roles(
                        muted,
                        reason="Auto mod: Mention protection",
                    )
            except (discord.Forbidden, discord.NotFound):
                pass
