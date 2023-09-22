from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot

from discord.abc import GuildChannel
from discord.utils import maybe_coroutine, utcnow

from discord import Member, Message


class Condition:
    def __init__(self, bot: Parrot, data: list[dict]) -> None:
        self.bot = bot
        self.data = data

    def __repr__(self) -> str:
        return f"<Condition data={self.data}>"

    async def check(self, **kw) -> bool:
        if not self.data:
            return True

        for condition in self.data:
            func = getattr(self, condition["type"])
            if not await maybe_coroutine(func, **kw, **condition):
                return False
        return True

    def ignore_roles(self, *, member: Member, roles: list[int], **kw) -> bool:
        return any(role.id in roles for role in member.roles)

    def require_roles(self, *, member: Member, roles: list[int], **kw) -> bool:
        return all(role.id in roles for role in member.roles)

    def ignore_channel(self, *, message: Message | None = None, channels: list[int], **kw) -> bool:
        return message.channel.id in channels if message else False

    def require_channel(self, *, message: Message | None = None, channels: list[int], **kw) -> bool:
        return message.channel.id not in channels if message else False

    def ignore_bots(self, *, member: Member, **kw) -> bool:
        return not member.bot

    def require_bots(self, *, member: Member, **kw) -> bool:
        return member.bot

    def ignore_categories(self, *, message: Message | None = None, categories: list[int], **kw) -> bool:
        if not message:
            return False
        assert isinstance(message.channel, GuildChannel)
        return message.channel.category.id in categories if message.channel.category else False

    def require_categories(self, *, message: Message | None = None, categories: list[int], **kw) -> bool:
        if not message:
            return False
        assert isinstance(message.channel, GuildChannel)
        return message.channel.category.id not in categories if message.channel.category else False

    def new_message(self, *, message: Message | None = None, **kw) -> bool:
        return not bool(message.edited_at) and not message.is_system() if message else False

    def edited_message(self, *, message: Message | None = None, **kw) -> bool:
        return bool(message.edited_at) and not message.is_system() if message else False

    def account_age_below(self, *, member: Member, age_in_min: int, **kw) -> bool:
        return ((utcnow() - member.created_at).total_seconds() / 60) < age_in_min

    def account_age_above(self, *, member: Member, age_in_min: int, **kw) -> bool:
        return ((utcnow() - member.created_at).total_seconds() / 60) > age_in_min

    def server_member_duration_below(self, *, member: Member, duration_in_min: int, **kw) -> bool:
        return (((utcnow() - member.joined_at).total_seconds() / 60) < duration_in_min) if member.joined_at else False

    def server_member_duration_above(self, *, member: Member, duration_in_min: int, **kw) -> bool:
        return (((utcnow() - member.joined_at).total_seconds() / 60) > duration_in_min) if member.joined_at else False

    def all_true(self, **kw) -> bool:
        return True
