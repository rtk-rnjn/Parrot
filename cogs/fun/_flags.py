from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from discord.ext import commands


class TriviaFlag(  # type: ignore
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    token: Optional[str] = None
    number: Optional[int] = commands.flag(name="number", default=10, aliases=["amount"])
    category: Optional[str] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    _type: Optional[Literal["multiple", "boolean"]] = commands.flag(
        default="multiple", name="type"
    )


class Category(Enum):
    General = 9
    Books = 10
    Film = 11
    Music = 12
    Musicals_Theatres = 13
    Tv = 14
    Video_Games = 15
    Board_Games = 16
    Nature = 17
    Computers = 18
    Maths = 19
    Mythology = 20
    Sports = 21
    Geography = 22
    History = 23
    Politics = 24
    Art = 25
    Celebrities = 26
    Animals = 27
    Vehicles = 28
    Comics = 29
    Gadgets = 30
    Anime_Manga = 31
    Cartoon = 32
