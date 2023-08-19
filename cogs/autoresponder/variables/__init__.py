from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot

import discord


class _discord:
    Embed = discord.Embed
    Permisisons = discord.Permissions
    Colour = discord.Colour
    PermissionOverwrite = discord.PermissionOverwrite
    AllowedMentions = discord.AllowedMentions


class Variables:
    __class__ = None  # type: ignore

    def __init__(self, *, message: discord.Message, bot: Parrot) -> None:
        self.__message = message
        self.__bot = bot

    def build_base(self) -> dict:
        from .channel import JinjaChannel
        from .guild import JinjaGuild
        from .member import JinjaMember
        from .message import JinjaMessage

        return {
            "channel": JinjaChannel(channel=self.__message.channel),  # type: ignore
            "guild": JinjaGuild(guild=self.__message.guild),  # type: ignore
            "member": JinjaMember(member=self.__message.author),
            "message": JinjaMessage(message=self.__message),
            "discord": _discord(),
        }

    def multiply(self, a: int, b: int):
        if max(a, b) > 100000:
            msg = "The number is too big"
            raise ValueError(msg)
        return a * b
