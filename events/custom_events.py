from __future__ import annotations

import contextlib
from typing import Any

import discord
from cogs.giveaway.method import end_giveaway
from core import Cog, Parrot
from utilities.time import ShortTime


class EventCustom(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ON_TESTING = False

    @Cog.listener("on_mod_action_timer_complete")
    async def mod_parser(
        self,
        *,
        mod_action: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if mod_action is None:
            return

        kw = mod_action

        action: str = kw.get("action")  # type: ignore
        guild: discord.Guild | None = self.bot.get_guild(kw.get("guild", 0))
        if guild is None:
            return

        target: int = kw.get("member") or kw.get("target") or kw.get("user")  # type: ignore

        if action.upper() == "UNBAN":
            with contextlib.suppress(discord.NotFound, discord.HTTPException, discord.Forbidden):
                await guild.unban(discord.Object(target), reason=kw.get("reason"))
        if action.upper() == "BAN":
            with contextlib.suppress(discord.NotFound, discord.HTTPException, discord.Forbidden):
                await guild.ban(discord.Object(target), reason=kw.get("reason"))
        if action.upper() == "KICK":
            member: discord.Member | None = await self.bot.get_or_fetch_member(guild, target)
            if member is None:
                return
            with contextlib.suppress(discord.NotFound, discord.HTTPException, discord.Forbidden):
                await guild.kick(member, reason=kw.get("reason"))
        if action.upper() == "REMOVE_ROLE":
            role_id: int | None = kw.get("role_id")
            member: discord.Member | None = await self.bot.get_or_fetch_member(guild, target)

            if member is None or role_id is None:
                return

            with contextlib.suppress(discord.NotFound, discord.HTTPException, discord.Forbidden):
                await member.remove_roles(discord.Object(role_id), reason=kw.get("reason"))

    @Cog.listener("on_timer_complete")
    async def normal_parser(
        self,
        *,
        embed: dict[str, Any] | None = None,  # type: ignore
        content: str | None = None,
        dm_notify: bool = False,
        is_todo: bool = False,
        messageChannel: int | None = None,
        messageAuthor: int | None = None,
        messageURL: str | None = None,
        **kwargs: Any,
    ) -> None:
        if not content:
            return
        if embed is None:
            embed = discord.utils.MISSING
        else:
            embed: discord.Embed = discord.Embed.from_dict(embed) if embed else discord.utils.MISSING

        if (dm_notify or is_todo) and (user := self.bot.get_user(messageAuthor or 0)):
            with contextlib.suppress(discord.Forbidden):
                await user.send(
                    content=f"{user.mention} this is reminder for: **{content}**"
                    + (f"\n>>> {messageURL}" if messageURL else ""),
                    embed=embed,
                )
            return

        if channel := self.bot.get_channel(messageChannel or 0):
            assert isinstance(channel, discord.abc.Messageable)
            with contextlib.suppress(discord.Forbidden):
                await channel.send(
                    content=f"<@{messageAuthor}> this is reminder for: **{content}**"
                    + (f"\n>>> {messageURL}" if messageURL else ""),
                    embed=embed,
                )
            return

    @Cog.listener("on_timer_complete")
    async def extra_parser(self, *, extra: dict[str, Any] | None = None, **kw: Any) -> None:
        if not extra:
            return

        name: str = extra.get("name")  # type: ignore
        if name == "SET_TIMER_LOOP":
            return await self._parse_timer(**kw, extra=extra)

        if main := extra.get("main"):
            await self.extra_action_parser(name, **main)

    @Cog.listener("on_set_afk_timer_complete")
    async def extra_parser_set_afk(self, *, extra: dict[str, Any] | None = None, **kw: Any) -> None:
        if not extra:
            return

        name = extra.get("name")
        if name == "SET_AFK":
            await self.bot.afk_collection.insert_one(kw)
            self.bot.afk_users.add(kw.get("messageAuthor", 0))

    @Cog.listener("on_remove_afk_timer_complete")
    async def extra_parser_remove_afk(self, *, extra: dict[str, Any] | None = None, **kw: Any) -> None:
        if not extra:
            return

        name = extra.get("name")
        if name == "REMOVE_AFK":
            await self.bot.afk_collection.delete_one(kw)
            self.bot.afk_users.remove(kw.get("messageAuthor", 0))

    @Cog.listener("on_giveaway_timer_complete")
    async def extra_parser_giveaway(self, **kw: Any) -> None:
        extra = kw.get("extra")
        if not extra:
            return

        name = extra.get("name")
        if name == "GIVEAWAY_END" and (main := extra.get("main")):
            await self._parse_giveaway(**main)

    @Cog.listener("on_message_delete_timer_complete")
    async def extra_parser_message_delete(self, **kw: Any) -> None:
        extra = kw.get("extra")
        if not extra:
            return

        name = extra.get("name")
        if name == "MESSAGE_DELETE":
            main = extra.get("main")
            channel_id = int(main["channel_id"])
            message_id = int(main["message_id"])

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            message: discord.PartialMessage = await self.bot.get_or_fetch_message(channel, message_id, partial=True)
            if message:
                await message.delete(delay=0.0)

    async def extra_action_parser(self, name: str, **kw: Any) -> None:
        if name.upper() == "SET_TIMER":
            await self.bot.create_timer(**kw)

        if name.upper() == "SET_TIMER_LOOP":
            await self._parse_timer(**kw)

        if name.upper() == "DB_EXECUTE":
            await self._parse_db_execute(**kw)

    async def _parse_db_execute(self, **kw: Any) -> None:
        collection = self.bot.mongo[kw["database"]][kw["collection"]]
        if kw.get("action") == "delete_one" and kw.get("filter"):
            await collection.delete_one(kw["filter"])

    async def _parse_timer(self, **kw: Any):
        age: str = kw["extra"]["main"].get("age")  # type: ignore
        if age is None:
            return
        age: ShortTime = ShortTime(age)
        post = kw.copy()
        post["extra"] = {"name": "SET_TIMER_LOOP", "main": {"age": age._argument}}
        post["expires_at"] = age.dt.timestamp()
        await self.bot.create_timer(**post)

    async def _parse_giveaway(self, **kw: Any) -> None:
        data: dict[str, Any] = await self.bot.giveaways.find_one(
            {
                "message_id": kw.get("message_id"),
                "guild_id": kw.get("guild_id"),
                "status": "ONGOING",
            },
        )
        member_ids: list[int] = await end_giveaway(self.bot, **data)
        channel: discord.TextChannel | None = await self.bot.getch(
            self.bot.get_channel,
            self.bot.fetch_channel,
            kw.get("giveaway_channel"),
        )
        await self.bot.giveaways.find_one_and_update(
            {"message_id": kw.get("message_id"), "status": "ONGOING"},
            {"$set": {"status": "END"}},
        )
        if not channel:
            return
        msg_link = f"https://discord.com/channels/{kw.get('guild_id')}/{kw.get('giveaway_channel')}/{kw.get('message_id')}"
        if not member_ids:
            await channel.send(f"No winners!\n> {msg_link}")
            return

        joiner = ">, <@".join([str(i) for i in member_ids])

        await channel.send(f"Congrats <@{joiner}> you won {kw.get('prize')}\n" f"> {msg_link}")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(EventCustom(bot))
