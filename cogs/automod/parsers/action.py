from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from core import Parrot

import arrow
from tabulate import tabulate

from discord import Forbidden, Member, Message, Object, PermissionOverwrite
from discord.abc import GuildChannel
from discord.utils import MISSING, maybe_coroutine, utcnow

reason_init = """AutoMod: {reason}
Sent from {guild.name} ({guild.id})
"""


class AutomodWarnings:
    def __init__(self, *, bot: Parrot, raw_data: dict) -> None:
        self.bot = bot
        self._raw_data = raw_data

    @property
    def guild_id(self) -> int:
        return self._raw_data["guild_id"]

    @guild_id.setter
    def guild_id(self, value: int) -> None:
        self._raw_data["guild_id"] = value

    def __repr__(self) -> str:
        return f"<AutomodWarnings guild_id={self.guild_id}>"

    async def warn(
        self,
        *,
        member_id: int,
        warning_name: str = "global",
        reason: str = None,
        moderator_id: int | None = None,
    ) -> None:
        query = {"guild_id": self.guild_id}
        update = {
            "$addToSet": {
                "warnings": {
                    "timestamp": utcnow().timestamp(),
                    "user_id": member_id,
                    "warning_name": warning_name,
                    "reason": reason,
                    "moderator_id": moderator_id,
                },
            },
        }
        await self.bot.automod_voilations.update_one(query, update, upsert=True)

    async def delete_warn(
        self,
        *,
        member_id: int,
        moderator_id: int | None = MISSING,
        timestamp: float | None = MISSING,
        warning_name: str | None = MISSING,
    ) -> None:
        payload = {}
        if moderator_id is not MISSING:
            payload["moderator_id"] = moderator_id
        if timestamp is not MISSING:
            payload["timestamp"] = timestamp
        if warning_name is not MISSING:
            payload["warning_name"] = warning_name

        query = {"guild_id": self.guild_id}
        update = {
            "$pull": {
                "warnings": {
                    "user_id": member_id,
                    **payload,
                },
            },
        }
        await self.bot.automod_voilations.update_one(query, update)

    async def count(self, *, member_id: int, warning_name: str = "global") -> int:
        query = {
            "guild_id": self.guild_id,
            "warnings.warning_name": warning_name,
            "warnings.user_id": member_id,
        }
        return await self.bot.automod_voilations.count_documents(query)

    async def count_during(self, *, before: datetime | None = None, after: datetime) -> int:
        if before is None:
            before = utcnow()

        query = {
            "guild_id": self.guild_id,
            "warnings.timestamp": {"$gte": after.timestamp(), "$lte": before.timestamp()},
        }
        return await self.bot.automod_voilations.count_documents(query)

    async def tabulate(self, user_id: int) -> str:
        query = {"guild_id": self.guild_id, "warnings.user_id": user_id}
        projection = {"warnings": 1, "_id": 0}
        data = await self.bot.automod_voilations.find_one(query, projection)

        if data is None:
            return "No warnings found."

        return tabulate(
            [
                (
                    i + 1,
                    arrow.get(warning["timestamp"]).humanize(),
                    warning["warning_name"],
                    warning["reason"],
                    self._get_name(warning["moderator_id"]),
                )
                for i, warning in enumerate(data["warnings"])
            ],
            headers=["#", "Timestamp", "Warning Name", "Reason", "Moderator"],
            tablefmt="outline",
        )

    def _get_name(self, user_id: int) -> str:
        guild = self.bot.get_guild(self.guild_id)
        if guild is None:
            return f"Unknown User {user_id}"

        member = guild.get_member(user_id)
        return f"Unknown User {user_id}" if member is None else str(member)


class Action:
    def __init__(self, bot: Parrot, data: list[dict]) -> None:
        self.bot = bot
        self.data = data
        self._automod_warnings = AutomodWarnings(bot=bot, raw_data={})

    def __repr__(self) -> str:
        return f"<Action data={self.data}>"

    async def execute(self, **kw) -> None:
        for action in self.data:
            func = getattr(self, action["type"], None)
            if func is None:
                continue

            await maybe_coroutine(func, **kw, **action)

    async def delete_message(self, *, message: Message, **kw) -> None:
        await message.delete(delay=0)

    async def plus_voilation(self, *, member: Member, name_of_voilation: str = None, **kw) -> None:
        self._automod_warnings.guild_id = member.guild.id
        await self._automod_warnings.warn(member_id=member.id, warning_name=name_of_voilation or "global")

    async def minus_voilation(self, *, member: Member, name_of_voilation: str = MISSING, **kw) -> None:
        self._automod_warnings.guild_id = member.guild.id
        await self._automod_warnings.delete_warn(member_id=member.id, warning_name=name_of_voilation)

    async def total_voilations(self, *, member: Member, **kw) -> int:
        self._automod_warnings.guild_id = member.guild.id
        return await self._automod_warnings.count(member_id=member.id)

    async def reset_voilations(self, *, member: Member, **kw) -> None:
        self._automod_warnings.guild_id = member.guild.id
        await self._automod_warnings.delete_warn(member_id=member.id)

    async def kick_user(self, *, member: Member, msg: str = None, **kw) -> None:
        if member.guild.me.guild_permissions.kick_members and member.top_role < member.guild.me.top_role:
            await member.guild.kick(member, reason="Automod")
        try:
            await member.send(reason_init.format(reason=msg or "Kicked", guild=member.guild))
        except Forbidden:
            pass

    async def ban_user(self, *, member: Member, msg: str, **kw) -> None:
        if member.guild.me.guild_permissions.ban_members and member.top_role < member.guild.me.top_role:
            await member.guild.ban(member, reason="Automod")

        try:
            await member.send(reason_init.format(reason=msg or "Banned", guild=member.guild))
        except Forbidden:
            pass

    async def mute_user(self, *, member: Member, **kw) -> None:
        from cogs.mod.method import _mute

        # since the `silence` is true, passing None to command_name, destination is fine
        await _mute(
            guild=member.guild,
            command_name="",
            ctx=None,  # type: ignore
            member=member,
            reason="Automod",
            silent=True,
            destination=None,  # type: ignore
        )

    async def set_nickname(self, *, member: Member, nickname: str, **kw) -> None:
        if member.guild.me.guild_permissions.manage_nicknames and member.top_role < member.guild.me.top_role:
            await member.edit(nick=nickname)

    async def delete_multiple_messages(self, *, message: Message, count: int, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)

        def check(m: Message) -> bool:
            return m.author == message.author and (utcnow() - m.created_at).total_seconds() < 7 * 24 * 60 * 60

        if message.channel.permissions_for(message.guild.me).manage_messages:
            await message.channel.purge(limit=count, check=check, bulk=True)

    async def enable_slowmode(self, *, message: Message, duration: int, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)

        if message.channel.permissions_for(message.guild.me).manage_channels:
            await message.channel.edit(slowmode_delay=duration)

    async def lock_channel(self, *, message: Message, msg: str = None, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)
        overwrite = message.channel.overwrites
        overwrite.update({message.guild.default_role: PermissionOverwrite(send_messages=False)})

        await message.channel.edit(overwrites=overwrite)
        if msg is not None:
            await message.channel.send(msg)

    async def give_role(self, *, member: Member, role: int, **kw) -> None:
        await member.add_roles(Object(id=role), reason="Automod")

    async def remove_role(self, *, member: Member, role: int, **kw) -> None:
        await member.remove_roles(Object(id=role), reason="Automod")

    async def send_message(self, *, message: Message, msg: str, delete_after: int, channel: int, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)
        ch = message.guild.get_channel(channel) or message.channel
        await ch.send(msg, delete_after=delete_after)  # type: ignore
