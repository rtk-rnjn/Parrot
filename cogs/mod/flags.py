from __future__ import annotations

import typing

import discord
from discord.ext import commands


class reasonFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    reason: typing.Optional[str] = None


class WarnFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    message: typing.Optional[int] = None
    warn_id: typing.Optional[int] = None
    moderator: typing.Union[discord.Member, discord.User] = None
    target: typing.Union[discord.Member, discord.User] = None
    channel: typing.Union[discord.TextChannel, discord.Thread] = None
