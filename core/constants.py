import enum
import re

ERROR_REPLIES = [
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

NEGATIVE_REPLIES = [
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

POSITIVE_REPLIES = [
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


LINKS_RE = re.compile(
    r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*",
    flags=re.IGNORECASE,
)

INVITE_RE = re.compile(
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
