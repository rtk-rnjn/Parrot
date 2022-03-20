from __future__ import annotations
from typing import List, Optional
import discord

from utilities.infraction import warn
import re
import random

import emojis
from core import Parrot, Cog, Context
from utilities.time import ShortTime

with open("extra/duke_nekum.txt") as f:
    quotes = f.read().split("\n")


class EmojiCapsProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    async def delete(self, message: discord.Message) -> None:
        await message.delete(delay=0)

    def get_emoji_count(self, message_content: str) -> int:
        str_count = emojis.count(message_content)
        dis_count = len(
            re.findall(
                r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
                message_content,
            )
        )
        return int(str_count + dis_count)

    def get_caps_count(self, message_content: str) -> int:
        caps_count = len(re.findall(r"[A-Z]", message_content))
        return int(caps_count)

    def is_caps_infilterated(self, message: discord.Message) -> Optional[bool]:
        if data_c := self.bot.server_config.get(message.guild.id):
            if not data_c["automod"]["caps"]["enable"]:
                return False
            try:
                ignore: List[int] = data_c["automod"]["caps"]["channel"]
            except KeyError:
                ignore = []
            if message.channel.id in ignore:
                return False
            try:
                limit: int = data_c["automod"]["caps"]["limit"]
            except KeyError:
                return False
            if limit <= (self.get_caps_count(message.content)):
                return True

    def is_emoji_infilterated(self, message: discord.Message) -> Optional[bool]:
        if data_c := self.bot.server_config.get(message.guild.id):
            if not data_c["automod"]["emoji"]["enable"]:
                return False
            try:
                ignore: List[int] = data_c["automod"]["emoji"]["channel"]
            except KeyError:
                ignore = []
            if message.channel.id in ignore:
                return False
            try:
                limit: int = data_c["automod"]["emoji"]["limit"]
            except KeyError:
                return False
            if limit <= (self.get_emoji_count(message.content)):
                return True

    async def _on_message_passive(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        # perms = message.author.guild_permissions

        # if perms.administrator or perms.manage_messages or perms.manage_channels:
        #     return

        caps_: bool = self.is_caps_infilterated(message)
        emoj_: bool = self.is_emoji_infilterated(message)
        ctx: Context = await self.bot.get_context(message, cls=Context)
        if data := self.bot.server_config.get(message.guild.id):
            if emoj_:
                try:
                    to_delete: bool = data["automod"]["emoji"]["autowarn"]["to_delete"]
                except KeyError:
                    to_delete: bool = True

                if to_delete:
                    await message.delete(delay=0)

                try:
                    to_warn: bool = data["automod"]["emoji"]["autowarn"]["enable"]
                except KeyError:
                    to_warn: bool = False

                try:
                    instant_action: str = data["automod"]["emoji"]["autowarn"][
                        "punish"
                    ]["type"]
                except KeyError:
                    pass
                else:
                    await self.__instant_action_parser(
                        name=instant_action,
                        ctx=ctx,
                        message=message,
                        **data["automod"]["emoji"]["autowarn"]["punish"],
                    )

                if to_warn:
                    await warn(
                        message.guild,
                        message.author,
                        "Automod: Mass Emoji",
                        moderator=self.bot.user,
                        message=message,
                        at=message.created_at,
                        ctx=ctx,
                    )
                    await self.bot.get_cog("Moderator").warn_task(
                        target=message.author, ctx=ctx
                    )

                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Excess Emoji] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )
        if data := self.bot.server_config.get(message.guild.id):
            if caps_:
                try:
                    to_delete: bool = data["automod"]["caps"]["autowarn"]["to_delete"]
                except KeyError:
                    to_delete: bool = True

                if to_delete:
                    await message.delete(delay=0)

                try:
                    to_warn = data["automod"]["caps"]["autowarn"]["enable"]
                except KeyError:
                    to_warn = False

                try:
                    instant_action: str = data["automod"]["caps"]["autowarn"]["punish"][
                        "type"
                    ]
                except KeyError:
                    pass
                else:
                    await self.__instant_action_parser(
                        name=instant_action,
                        ctx=ctx,
                        message=message,
                        **data["automod"]["caps"]["autowarn"]["punish"],
                    )

                if to_warn:
                    await warn(
                        message.guild,
                        message.author,
                        "Automod: Excess Caps",
                        moderator=self.bot.user,
                        message=message,
                        at=message.created_at,
                        ctx=ctx,
                    )

                    await self.bot.get_cog("Moderator").warn_task(
                        target=message.author, ctx=ctx
                    )

                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Excess Caps] {'[Warning]' if to_warn else ''}**",
                    delete_after=10,
                )

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self._on_message_passive(message)

    @Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
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
                    message.author, reason=f"Auto mod: Emoji/Caps protection"
                )
            except (discord.Forbidden, discord.NotFound):
                pass

        if name == "tempban":
            try:
                await ctx.guild.ban(
                    message.author, reason=f"Auto mod: Emoji/Caps protection"
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
                await message.author.kick(reason="Auto mod: Emoji/Caps protection")
            except (discord.Forbidden, discord.NotFound):
                pass

        if name in ("timeout", "mute"):
            try:
                if duration:
                    await message.author.edit(
                        timed_out_until=duration.dt,
                        reason=f"Auto mod: Emoji/Caps protection",
                    )
                else:
                    muted = await ctx.muterole()
                    if not muted:
                        return
                    await message.author.add_roles(
                        muted,
                        reason=f"Auto mod: Emoji/Caps protection",
                    )
            except (discord.Forbidden, discord.NotFound):
                pass
