from __future__ import annotations

from typing import Literal, Optional

from discord.ext import commands
from utilities.converters import convert_bool


class SokobanStatsFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):

    sort_by: Literal["level", "time", "moves"] = "time"
    sort: Literal[1, -1] = 1
    limit: int = 100


class TwentyFortyEightStatsFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    me: Optional[convert_bool] = True
    _global: Optional[convert_bool] = commands.flag(name="global", default=False, aliases=["g", "all"])
    sort_by: Literal["moves", "games", "games_played"] = "games_played"
    sort: Literal[1, 0] = 1


class CountryGuessStatsFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    me: Optional[convert_bool] = True
    _global: Optional[convert_bool] = commands.flag(name="global", default=False, aliases=["g", "all"])
    sort_by: Literal["win", "games", "games_won", "games_played"] = "games_played"
    sort: Literal[1, 0] = 1

class ChessStatsFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):

    sort_by: Literal["winner", "draw"] = "winner"
    sort: Literal[1, -1] = 1
    limit: int = 100