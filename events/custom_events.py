from __future__ import annotations

import contextlib
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection

import discord
from cogs.utils.method import end_giveaway
from core import Cog, Parrot
from utilities.time import ShortTime


class FakeMessage:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class EventCustom(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ON_TESTING = False
        
    @Cog.listener("on_timer_complete")
    async def mod_parser(
        self,
        *,
        mod_action: Dict[str, Any] = None,
        **kwargs: Any,
    ) -> None:
        if mod_action is None:
            return

        kw = mod_action

        action: str = kw.get("action")
        guild: discord.Guild = self.bot.get_guild(kw.get("guild"))
        if guild is None:
            return

        target: int = kw.get("member") or kw.get("target")

        if action.upper() == "UNBAN":
            with contextlib.suppress(
                discord.NotFound, discord.HTTPException, discord.Forbidden
            ):
                await guild.unban(discord.Object(target), reason=kw.get("reason"))
        if action.upper() == "BAN":
            with contextlib.suppress(
                discord.NotFound, discord.HTTPException, discord.Forbidden
            ):
                await guild.ban(discord.Object(target), reason=kw.get("reason"))
        if action.upper() == "KICK":
            member: discord.Member = self.bot.get_or_fetch_member(guild, target)
            if member is None:
                return
            with contextlib.suppress(
                discord.NotFound, discord.HTTPException, discord.Forbidden
            ):
                await guild.kick(member, reason=kw.get("reason"))

    @Cog.listener("on_timer_complete")
    async def normal_parser(
        self,
        *,
        embed: Dict[str, Any] = None,
        content: str = None,
        dm_notify: bool = False,
        is_todo: bool = False,
        messageChannel: int = None,
        messageAuthor: int = None,
        messageURL: str = None,
        **kwargs: Any,
    ):
        if not content:
            return
        if embed is None:
            embed = {}
        embed = discord.Embed.from_dict(embed) if embed else discord.utils.MISSING

        if (dm_notify or is_todo) and (user := self.bot.get_user(messageAuthor)):
            with contextlib.suppress(discord.Forbidden):
                await user.send(
                    content=f"{user.mention} this is reminder for: **{content}**\n>>> {messageURL}",
                    embed=embed,
                )
            return

        if channel := self.bot.get_channel(messageChannel):
            with contextlib.suppress(discord.Forbidden):
                await channel.send(
                    content=f"<@{messageAuthor}> this is reminder for: **{content}**\n>>> {messageURL}",
                    embed=embed,
                )
            return

    @Cog.listener("on_timer_complete")
    async def extra_parser(self, extra: Dict[str, Any] = None, **kw: Any) -> None:
        if extra is None:
            return

        name = extra.get("name")
        if name == "SET_TIMER_LOOP":
            return await self._parse_timer(**kw)

        main = extra.get("main")

        await self.extra_action_parser(name, **main)

    async def extra_action_parser(self, name: str, **kw: Any) -> None:
        if name.upper() == "REMOVE_AFK":
            await self.bot.mongo.parrot_db.afk.delete_one(kw)
            self.bot.afk.remove(kw.get("messageAuthor"))

        if name.upper() == "SET_AFK":
            await self.bot.mongo.parrot_db.afk.insert_one(kw)
            self.bot.afk.add(kw.get("messageAuthor"))

        if name.upper() == "SET_TIMER":
            await self.bot.mongo.parrot_db.timers.insert_one(kw)

        if name.upper() == "SET_TIMER_LOOP":
            await self._parse_timer(**kw)

        if name.upper() == "GIVEAWAY_END":
            await self._parse_giveaway(**kw)

        if name.upper() == "DB_EXECUTE":
            await self._parse_db_execute(**kw)

    async def _parse_db_execute(self, **kw: Any) -> None:
        collection: Collection = self.bot.mongo[kw["database"]][kw["collection"]]
        if kw.get("action") == "delete_one":
            await collection.delete_one(kw["filter"])

    async def _parse_timer(self, **kw: Any):
        age: str = kw["extra"]["main"].get("age")
        if age is None:
            return
        age: ShortTime = ShortTime(age)
        post = kw.copy()
        post["extra"] = {"name": "SET_TIMER_LOOP", "main": {"age": str(age)}}
        post["expires_at"] = age.dt.timestamp()
        await self.bot.mongo.parrot_db.timers.insert_one(post)

    async def _parse_giveaway(self, **kw: Any) -> None:
        data: Dict[str, Any] = await self.bot.mongo.parrot_db.giveaway.find_one(
            {
                "message_id": kw.get("message_id"),
                "guild_id": kw.get("guild_id"),
                "status": "ONGOING",
            }
        )
        member_ids: List[int] = await end_giveaway(self.bot, **data)
        channel: Optional[discord.TextChannel] = await self.bot.getch(
            self.bot.get_channel, self.bot.fetch_channel, kw.get("giveaway_channel")
        )
        await self.bot.mongo.parrot_db.giveaway.find_one_and_update(
            {"message_id": kw.get("message_id"), "status": "ONGOING"},
            {"$set": {"status": "END"}},
        )
        if not channel:
            return
        msg_link = f"https://discord.com/channels/{kw.get('guild_id')}/{kw.get('giveaway_channel')}/{kw.get('message_id')}"
        if not member_ids:
            return await channel.send(f"No winners!\n> {msg_link}")

        joiner = ">, <@".join([str(i) for i in member_ids])

        await channel.send(
            f"Congrats <@{joiner}> you won {kw.get('prize')}\n" f"> {msg_link}"
        )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(EventCustom(bot))
