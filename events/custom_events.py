from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import discord
from cogs.utils.method import end_giveaway
from core import Cog, Parrot
from pymongo.collection import Collection
from utilities.time import ShortTime


class FakeMessage:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class EventCustom(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        if self.bot.get_cog("Utils"):
            self.create_timer: Callable = self.bot.get_cog("Utils").create_timer  # type: ignore
        else:
            self.create_timer = None

    async def on_timer_complete(self, **kw: Any) -> None:
        await self.bot.wait_until_ready()
        if data := kw.get("mod_action"):
            await self.mod_action_parser(**data)

        if kw.get("embed"):
            embed: discord.Embed = discord.Embed.from_dict(kw.get("embed"))
        else:
            embed = discord.utils.MISSING

        if (kw.get("dm_notify") or kw.get("is_todo")) and kw.get("content"):
            user: discord.User = self.bot.get_user(kw["messageAuthor"])
            if user:
                try:
                    await user.send(
                        content=f"{user.mention} this is reminder for: **{kw['content']}**\n>>> {kw['messageURL']}",
                        embed=embed,
                    )
                except discord.Forbidden:
                    pass  # I don't know whytf user blocks the DM

        elif kw.get("content"):
            channel: discord.TextChannel = self.bot.get_channel(kw["messageChannel"])
            if channel:
                try:
                    await channel.send(
                        content=f"<@{kw['messageAuthor']}> this is reminder for: **{kw['content']}**\n>>> {kw['messageURL']}",
                        embed=embed,
                    )
                except discord.Forbidden:
                    # bot is not having permissions to send messages
                    pass

        if kw.get("extra"):
            data: Dict[str, Any] = kw.get("extra")
            if data.get("name") == "SET_TIMER_LOOP":
                return await self._parse_timer(**kw)
            await self.extra_action_parser(data.get("name"), **data.get("main"))

    async def mod_action_parser(self, **kw: Any) -> None:
        action: str = kw.get("action")
        guild: discord.Guild = self.bot.get_guild(kw.get("guild"))
        if guild is None:
            return
        target: int = kw.get("member") or kw.get("target")

        if action.upper() == "UNBAN":
            try:
                await guild.unban(discord.Object(target), reason=kw.get("reason"))
            except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                # User not found, Bot Not having permissions, Other HTTP Error
                pass

        if action.upper() == "BAN":
            try:
                await guild.ban(discord.Object(target), reason=kw.get("reason"))
            except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                pass  # User not found, Bot Not having permissions, Other HTTP Error

        if action.upper() == "KICK":
            member: discord.Member = self.bot.get_or_fetch_member(guild, target)
            if member is None:
                return
            try:
                await guild.kick(member, reason=kw.get("reason"))
            except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                pass

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

        await channel.send(f"Congrats <@{joiner}> you won {kw.get('prize')}\n" f"> {msg_link}")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(EventCustom(bot))
