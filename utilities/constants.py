from __future__ import annotations

import enum
from typing import List, Tuple

from .emotes import EMOJIS


class Colours:
    blue: int = 0x0279FD
    bright_green: int = 0x01D277
    dark_green: int = 0x1F8B4C
    orange: int = 0xE67E22
    pink: int = 0xCF84E0
    purple: int = 0xB734EB
    soft_green: int = 0x68C290
    soft_orange: int = 0xF9CB54
    soft_red: int = 0xCD6D6D
    yellow: int = 0xF9F586
    python_blue: int = 0x4B8BBE
    python_yellow: int = 0xFFD43B
    grass_green: int = 0x66FF00
    gold: int = 0xE6C200

    easter_like_colours: List[Tuple[int, int, int]] = [
        (255, 247, 0),
        (255, 255, 224),
        (0, 255, 127),
        (189, 252, 201),
        (255, 192, 203),
        (255, 160, 122),
        (181, 115, 220),
        (221, 160, 221),
        (200, 162, 200),
        (238, 130, 238),
        (135, 206, 235),
        (0, 204, 204),
        (64, 224, 208),
    ]


class Month(enum.IntEnum):
    JANUARY = 1
    FEBRUARY = 2
    MARCH = 3
    APRIL = 4
    MAY = 5
    JUNE = 6
    JULY = 7
    AUGUST = 8
    SEPTEMBER = 9
    OCTOBER = 10
    NOVEMBER = 11
    DECEMBER = 12

    def __str__(self) -> str:
        return self.name.title()


class Day(enum.IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    ELEVEN = 11
    TWELVE = 12
    THIRTHEEN = 13
    FOURTEEN = 14
    FIFTEEN = 15
    SIXTEEN = 16
    SEVENTEEN = 17
    EIGHTEEN = 18
    NINETEEN = 19
    TWENTY = 20
    TWENTY_ONE = 21
    TWENTY_TWO = 22
    TWENTY_THREE = 23
    TWENTY_FOUR = 24
    TWENTY_FIVE = 25
    TWENTY_SIX = 26
    TWENTY_SEVEN = 27
    TWENTY_EIGHT = 28
    TWENTY_NINE = 29
    THIRTY = 30
    THIRTY_ONE = 31

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


ERROR_REPLIES: List[str] = [
    "Please don't do that.",
    "You have to stop.",
    "Do you mind?",
    "In the future, don't do that.",
    "That was a mistake.",
    "You blew it.",
    "You're bad at computers.",
    "Are you trying to kill me?",
    "Noooooo!!",
    "I can't believe you've done this",
]

NEGATIVE_REPLIES: List[str] = [
    "Noooooo!!",
    "Nope.",
    "I'm sorry Dave, I'm afraid I can't do that.",
    "I don't think so.",
    "Not gonna happen.",
    "Out of the question.",
    "Huh? No.",
    "Nah.",
    "Naw.",
    "Not likely.",
    "No way, José.",
    "Not in a million years.",
    "Fat chance.",
    "Certainly not.",
    "NEGATORY.",
    "Nuh-uh.",
    "Not in my house!",
]

POSITIVE_REPLIES: List[str] = [
    "Yep.",
    "Absolutely!",
    "Can do!",
    "Affirmative!",
    "Yeah okay.",
    "Sure.",
    "Sure thing!",
    "You're the boss!",
    "Okay.",
    "No problem.",
    "I got you.",
    "Alright.",
    "You got it!",
    "ROGER THAT",
    "Of course!",
    "Aye aye, cap'n!",
    "I'll allow it.",
]


class _Emoji:
    def __init__(self) -> None:
        for key in EMOJIS:
            setattr(self, key, EMOJIS[key])

    def __repr__(self) -> str:
        return f"Total: {len(EMOJIS)}"


Emoji = _Emoji()

EmbeddedActivity = {
    "awkword": 879863881349087252,
    "betrayal": 773336526917861400,
    "checkers_in_the_park": 832013003968348200,
    "checkers_in_the_park_dev": 832012682520428625,
    "checkers_in_the_park_staging": 832012938398400562,
    "checkers_in_the_park_qa": 832012894068801636,
    "chess_in_the_park": 832012774040141894,
    "chess_in_the_park_dev": 832012586023256104,
    "chest_in_the_park_staging": 832012730599735326,
    "chest_in_the_park_qa": 832012815819604009,
    "decoders_dev": 891001866073296967,
    "doodle_crew": 878067389634314250,
    "doodle_crew_dev": 878067427668275241,
    "fishington": 814288819477020702,
    "letter_tile": 879863686565621790,
    "ocho": 832025144389533716,
    "ocho_dev": 832013108234289153,
    "ocho_staging": 832025061657280566,
    "ocho_qa": 832025114077298718,
    "poker_night": 755827207812677713,
    "poker_night_staging": 763116274876022855,
    "poker_night_qa": 801133024841957428,
    "putts": 832012854282158180,
    "sketchy_artist": 879864070101172255,
    "sketchy_artist_dev": 879864104980979792,
    "spell_cast": 852509694341283871,
    "watch_together": 880218394199220334,
    "watch_together_dev": 880218832743055411,
    "word_snacks": 879863976006127627,
    "word_snacks_dev": 879864010126786570,
    "youtube_together": 755600276941176913,
}
