from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot

from discord.abc import GuildChannel
from discord.utils import maybe_coroutine, utcnow

from discord import Forbidden, Member, Message, Object, PermissionOverwrite

reason_init = """AutoMod: {reason}
Sent from {guild.name} ({guild.id})
"""


class Action:
    def __init__(self, bot: Parrot, data: list[dict]) -> None:
        self.bot = bot
        self.data = data

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
        if not name_of_voilation:
            name_of_voilation = "global"
        await self.bot.automod_voilations.update_one(
            {"guild_id": member.guild.id},
            {
                "$inc": {
                    f"u_{member.id}.{name_of_voilation}": 1,
                },
            },
            upsert=True,
        )

    async def minus_voilation(self, *, member: Member, name_of_voilation: str = None, **kw) -> None:
        if not name_of_voilation:
            name_of_voilation = "global"
        await self.bot.automod_voilations.update_one(
            {"guild_id": member.guild.id},
            {
                "$inc": {
                    f"u_{member.id}.{name_of_voilation}": -1,
                },
            },
            upsert=True,
        )

    async def total_voilations(self, *, member: Member, **kw) -> int:
        data = await self.bot.automod_voilations.find_one({"guild_id": member.guild.id})
        if not data:
            return 0

        u_id = f"u_{member.id}"
        data = data.get(u_id) or {}
        return sum(data.values())

    async def reset_voilations(self, *, member: Member, **kw) -> None:
        await self.bot.automod_voilations.update_one(
            {"guild_id": member.guild.id},
            {
                "$set": {
                    f"u_{member.id}": {},
                },
            },
            upsert=True,
        )

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
