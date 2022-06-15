from __future__ import annotations

from typing import List

from core import Parrot, Cog, Context

from discord.ext import commands
import discord
import random

from utilities.infraction import warn
from utilities.time import ShortTime

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class SpamProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.member
        )

    async def delete(self, message: discord.Message) -> None:
        def check(m: discord.Message) -> bool:
            return m.author.id == message.author.id

        try:
            await message.channel.purge(limit=5, check=check)
        except discord.Forbidden:  # this is faster than `if` `else`
            pass

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        # perms = message.author.guild_permissions

        # if perms.administrator or perms.manage_messages or perms.manage_channels:
        #     return

        bucket = self.cd_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            if data := self.bot.server_config.get(message.guild.id):
                if not data["automod"]["spam"]["enable"]:
                    return
                try:
                    ignore: List[int] = data["automod"]["spam"]["channel"]
                except KeyError:
                    ignore: List[int] = []

                if message.channel.id in ignore:
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
                    instant_action: str = data["automod"]["spam"]["autowarn"]["punish"][
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
                        "Automod: Spammed 5 messages in 5 seconds",
                        moderator=self.bot.user,
                        message=message,
                        at=message.created_at,
                        ctx=ctx,
                    )
                    await self.bot.get_cog("Moderator").warn_task(
                        target=message.author, ctx=ctx
                    )

                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Spam Protection] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )

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
                await ctx.guild.ban(message.author, reason="Auto mod: Spam protection")
            except (discord.Forbidden, discord.NotFound):
                pass

        if name == "tempban":
            try:
                await ctx.guild.ban(message.author, reason="Auto mod: Spam protection")
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
                await message.author.kick(reason="Auto mod: Spam protection")
            except (discord.Forbidden, discord.NotFound):
                pass

        if name in ("timeout", "mute"):
            try:
                if duration:
                    await message.author.edit(
                        timed_out_until=duration.dt,
                        reason="Auto mod: Spam protection",
                    )
                else:
                    muted = await ctx.muterole()
                    if not muted:
                        return
                    await message.author.add_roles(
                        muted,
                        reason="Auto mod: Spam protection",
                    )
            except (discord.Forbidden, discord.NotFound):
                pass
