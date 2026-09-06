import enum
import re
from typing import Final

import discord

ERROR_REPLIES: Final[list[str]] = [
    "Please don't do that.",
    "Action prohibited.",
    "Request denied.",
    "Do not repeat that action.",
    "Invalid action detected.",
    "Operation failed.",
    "Application bot.exe will be closed.",
    "Kernel Panic! *Kernel runs around in panic*",
    "Error 418. Bot is a teapot.",
    "System error.",
    "Unacceptable input detected.",
]

NEGATIVE_REPLIES: Final[list[str]] = [
    "Noooooo!!",
    "Nope.",
    "Request denied.",
    "Negative.",
    "Operation not permitted.",
    "Out of the question.",
    "Huh? No.",
    "Nah.",
    "Naw.",
    "Not likely.",
    "No way, José.",
    "Not in a million years.",
    "Request cannot be fulfilled.",
    "Certainly not.",
    "NEGATORY.",
    "Nuh-uh.",
    "Not in this system.",
]

POSITIVE_REPLIES: Final[list[str]] = [
    "Yep.",
    "Absolutely!",
    "Can do!",
    "Affirmative!",
    "Yeah okay.",
    "Sure.",
    "Sure thing!",
    "Request approved.",
    "Okay.",
    "No problem.",
    "Acknowledged.",
    "Alright.",
    "Confirmed!",
    "ROGER THAT",
    "Of course!",
    "Aye aye, cap'n!",
    "Permission granted.",
]


LINKS_RE: Final[re.Pattern[str]] = re.compile(
    r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*",
    flags=re.IGNORECASE,
)

INVITE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?",
    flags=re.IGNORECASE,
)


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


# fmt: off
BLACK_JACK_CARDS: Final[dict[str, discord.PartialEmoji]] = {
    "0C": discord.PartialEmoji(name="0C", id=1137283528640434196),
    "0D": discord.PartialEmoji(name="0D", id=1137283545224724531),
    "0H": discord.PartialEmoji(name="0H", id=1137283484742852628),
    "0S": discord.PartialEmoji(name="0S", id=1137283517777186848),
    "2C": discord.PartialEmoji(name="2C", id=1137283494985334785),
    "2D": discord.PartialEmoji(name="2D", id=1137283504590295060),
    "2H": discord.PartialEmoji(name="2H", id=1137283540053143572),
    "2S": discord.PartialEmoji(name="2S", id=1137283532427898991),
    "3C": discord.PartialEmoji(name="3C", id=1137283515994603570),
    "3D": discord.PartialEmoji(name="3D", id=1137283482129813644),
    "3H": discord.PartialEmoji(name="3H", id=1137283535116451880),
    "3S": discord.PartialEmoji(name="3S", id=1137283559200129065),
    "4C": discord.PartialEmoji(name="4C", id=1137283487179739196),
    "4D": discord.PartialEmoji(name="4D", id=1137283542586503198),
    "4H": discord.PartialEmoji(name="4H", id=1137283578267455621),
    "4S": discord.PartialEmoji(name="4S", id=1137283530049736824),
    "5C": discord.PartialEmoji(name="5C", id=1137283523468865576),
    "5D": discord.PartialEmoji(name="5D", id=1137283556331237457),
    "5H": discord.PartialEmoji(name="5H", id=1137283462399799336),
    "5S": discord.PartialEmoji(name="5S", id=1137283554938736761),
    "6C": discord.PartialEmoji(name="6C", id=1137283450253082654),
    "6D": discord.PartialEmoji(name="6D", id=1137283477000167454),
    "6H": discord.PartialEmoji(name="6H", id=1137283489557913681),
    "6S": discord.PartialEmoji(name="6S", id=1137283464870248469),
    "7C": discord.PartialEmoji(name="7C", id=1137283575318843425),
    "7D": discord.PartialEmoji(name="7D", id=1137283474269687878),
    "7H": discord.PartialEmoji(name="7H", id=1137283510114193419),
    "7S": discord.PartialEmoji(name="7S", id=1137283478879211531),
    "8C": discord.PartialEmoji(name="8C", id=1137283459774161006),
    "8D": discord.PartialEmoji(name="8D", id=1137283566527594538),
    "8H": discord.PartialEmoji(name="8H", id=1137283507752800306),
    "8S": discord.PartialEmoji(name="8S", id=1137283521166180422),
    "9C": discord.PartialEmoji(name="9C", id=1137283565172838490),
    "9H": discord.PartialEmoji(name="9H", id=1137402224507617340),
    "9D": discord.PartialEmoji(name="9D", id=1137283471753084978),
    "9S": discord.PartialEmoji(name="9S", id=1137283569425842246),
    "AC": discord.PartialEmoji(name="AC", id=1137283549721014273),
    "AD": discord.PartialEmoji(name="AD", id=1137283537750462568),
    "AH": discord.PartialEmoji(name="AH", id=1137283453080051742),
    "AS": discord.PartialEmoji(name="AS", id=1137403003918372884),
    "JC": discord.PartialEmoji(name="JC", id=1137283581262188564),
    "JD": discord.PartialEmoji(name="JD", id=1137283526711058443),
    "JH": discord.PartialEmoji(name="JH", id=1137283562417160192),
    "JS": discord.PartialEmoji(name="JS", id=1137283468494127114),
    "KC": discord.PartialEmoji(name="KC", id=1137283513259937863),
    "KD": discord.PartialEmoji(name="KD", id=1137283573569818694),
    "KH": discord.PartialEmoji(name="KH", id=1137283456825557032),
    "KS": discord.PartialEmoji(name="KS", id=1137283552577327205),
    "QC": discord.PartialEmoji(name="QC", id=1137283502178566146),
    "QD": discord.PartialEmoji(name="QD", id=1137283498495971442),
    "QH": discord.PartialEmoji(name="QH", id=1137283548622106775),
    "QS": discord.PartialEmoji(name="QS", id=1137283492619767818),
}
CARD_BACK: Final[discord.PartialEmoji] = discord.PartialEmoji(name="CARD_BACK", id=1143090855910051851)
# fmt: off
