from __future__ import annotations

from discord.ext import commands
import typing
import discord
from utilities.converters import convert_bool


class purgeFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    member: typing.Optional[discord.Member] = None
    regex: typing.Optional[str] = None
    attachment: typing.Optional[convert_bool] = False
    links: typing.Optional[convert_bool] = False


class reasonFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    reason: typing.Optional[str] = None


class warnFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    message: typing.Optional[int] = None
    warn_id: typing.Optional[int] = None
    moderator: typing.Union[discord.Member, discord.User] = None
    target: typing.Union[discord.Member, discord.User] = None
    channel: typing.Union[discord.TextChannel, discord.Thread] = None
