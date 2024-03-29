import re

INVITE_RE = re.compile(
    r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?",
    flags=re.IGNORECASE,
)

TIME_REGEX = re.compile(r"(?:\d{1,5}[h|s|m|d])+?", flags=re.IGNORECASE)

LINKS_RE = re.compile(
    r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*",
    flags=re.IGNORECASE,
)
LINKS_NO_PROTOCOLS = re.compile(
    r"[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
    flags=re.IGNORECASE,
)

CALANDER_RE = re.compile(
    r"^(?:(?:31(\/|-|\.)(?:0?[13578]|1[02]|(?:Jan|Mar|May|Jul|Aug|Oct|Dec)))\1|(?:(?:29|30)(\/|-|\.)(?:0?[1,3-9]|1[0-2]|(?:Jan|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\2))(?:(?:1[6-9]|[2-9]\d)?\d{2})$|^(?:29(\/|-|\.)(?:0?2|(?:Feb))\3(?:(?:(?:1[6-9]|[2-9]\d)?(?:0[48]|[2468][048]|[13579][26])|(?:(?:16|[2468][048]|[3579][26])00))))$|^(?:0?[1-9]|1\d|2[0-8])(\/|-|\.)(?:(?:0?[1-9]|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep))|(?:1[0-2]|(?:Oct|Nov|Dec)))\4(?:(?:1[6-9]|[2-9]\d)?\d{2})$",
    flags=re.IGNORECASE,
)

EQUATION_REGEX = re.compile(
    r"((?:(?:((?:(?:[ \t]+))))|(?:((?:(?:\/\/.*?$))))|(?:((?:(?:(?<![\d.])[0-9]+(?![\d.])))))|(?:((?:(?:[0-9]+\.(?:[0-9]+\b)?|\.[0-9]+))))|(?:((?:(?:(?:\+)))))|(?:((?:(?:(?:\-)))))|(?:((?:(?:(?:\*)))))|(?:((?:(?:(?:\/)))))|(?:((?:(?:(?:%)))))|(?:((?:(?:(?:\()))))|(?:((?:(?:(?:\))))))))+",
)

TENOR_PAGE_REGEX = re.compile(r"https?://(www\.)?tenor\.com/view/\S+/?")

TENOR_GIF_REGEX = re.compile(r"https?://(www\.)?c\.tenor\.com/\S+/\S+\.gif/?")

IMGUR_PAGE_REGEX = re.compile(r"https?://(www\.)?imgur.com/(\S+)/?")

CUSTOM_EMOJI_REGEX = re.compile(r"<(a)?:([a-zA-Z0-9_]{2,32}):([0-9]{18,22})>")
