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
