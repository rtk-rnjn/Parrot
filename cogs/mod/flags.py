from __future__ import annotations

from discord.ext import commands
import typing
import discord
from utilities.converters import convert_bool


class purgeFlag(commands.FlagConverter,
                case_insensitive=True,
                prefix="--",
                delimiter=' '):
    member: typing.Optional[discord.Member]
    regex: typing.Optional[str]
    attachment: typing.Optional[convert_bool] = False
    links: typing.Optional[convert_bool] = False


class reasonFlag(commands.FlagConverter,
                 case_insensitive=True,
                 prefix='--',
                 delimiter=' '):
    reason: typing.Optional[str]
