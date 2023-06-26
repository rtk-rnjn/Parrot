from __future__ import annotations

import typing

import discord
from discord.ext import commands
from utilities.converters import convert_bool
from utilities.time import ShortTime


class AuditFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    guild: typing.Optional[discord.Guild] = None
    limit: typing.Optional[int] = 100
    action: typing.Optional[str] = None
    before: typing.Optional[ShortTime] = None
    after: typing.Optional[ShortTime] = None
    oldest_first: typing.Union[convert_bool, bool] = False  # type: ignore
    user: typing.Union[discord.User, discord.Member, None] = None


class BanFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    reason: typing.Optional[str] = None
    _global: typing.Union[convert_bool, bool] = commands.flag(name="global", default=False)  # type: ignore
    command: typing.Union[convert_bool, bool] = False  # type: ignore


class SubscriptionFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    code: typing.Optional[str] = None
    expiry: typing.Optional[ShortTime] = None
    guild: typing.Optional[discord.Guild] = None
    uses: typing.Optional[int] = 0
    limit: typing.Optional[int] = 1
