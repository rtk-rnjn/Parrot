from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot

from discord.abc import GuildChannel
from discord.utils import utcnow

from discord import Member, Message, Object, PermissionOverwrite

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
            await getattr(self, action["type"])(**kw)

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
        await member.guild.kick(member, reason="Automod")
        try:
            await member.send(reason_init.format(reason=msg or "Kicked", guild=member.guild))
        except Exception:
            pass

    async def ban_user(self, *, member: Member, msg: str, **kw) -> None:
        await member.guild.ban(member, reason="Automod")

        try:
            await member.send(reason_init.format(reason=msg or "Banned", guild=member.guild))
        except Exception:
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
        await member.edit(nick=nickname)

    async def delete_multiple_messages(self, *, message: Message, count: int, max_age: int, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)

        def check(m: Message) -> bool:
            return m.author == message.author and (utcnow() - m.created_at).total_seconds() < max_age

        await message.channel.purge(limit=count, check=check, bulk=True)

    async def enable_slowmode(self, *, message: Message, duration: int, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)
        await message.channel.edit(slowmode_delay=duration)

    async def lock_channel(self, *, message: Message, msg: str, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)
        overwrite = message.channel.overwrites
        overwrite.update({message.guild.default_role: PermissionOverwrite(send_messages=False)})

        await message.channel.edit(overwrites=overwrite)
        await message.channel.send(msg)

    async def give_role(self, *, member: Member, role: int, **kw) -> None:
        await member.add_roles(Object(id=role), reason="Automod")

    async def remove_role(self, *, member: Member, role: int, **kw) -> None:
        await member.remove_roles(Object(id=role), reason="Automod")

    async def send_message(self, *, message: Message, msg: str, delete_after: int, channel: int, **kw) -> None:
        assert message.guild is not None and isinstance(message.channel, GuildChannel)
        ch = message.guild.get_channel(channel) or message.channel
        await ch.send(msg, delete_after=delete_after)  # type: ignore
