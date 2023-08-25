from __future__ import annotations

import discord
from discord.ext import commands


class reasonFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    reason: str | None = None


class WarnFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    message: int | None = None
    warn_id: int | None = None
    moderator: discord.Member | discord.User | None = None
    target: discord.Member | discord.User | None = None
    channel: discord.TextChannel | discord.Thread | None = None
