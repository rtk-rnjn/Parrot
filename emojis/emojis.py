import re

from . import db

ALIAS_TO_EMOJI = db.get_emoji_aliases()
EMOJI_TO_ALIAS = {v: k for k, v in ALIAS_TO_EMOJI.items()}
EMOJI_TO_ALIAS_SORTED = sorted(ALIAS_TO_EMOJI.values(), key=len, reverse=True)

RE_TEXT_TO_EMOJI_GROUP = "({0})".format(
    "|".join([re.escape(emoji) for emoji in ALIAS_TO_EMOJI])
)
RE_TEXT_TO_EMOJI = re.compile(RE_TEXT_TO_EMOJI_GROUP)

RE_EMOJI_TO_TEXT_GROUP = "({0})".format(
    "|".join([re.escape(emoji) for emoji in EMOJI_TO_ALIAS_SORTED])
)
RE_EMOJI_TO_TEXT = re.compile(RE_EMOJI_TO_TEXT_GROUP)


def encode(msg) -> str:
    """
    Encode Emoji aliases into unicode Emoji values.
    :param msg: String to encode.
    :rtype: str
    Usage::
        >>> import emojis
        >>> emojis.encode('This is a message with emojis :smile: :snake:')
        'This is a message with emojis 😄 🐍'
    """
    msg = RE_TEXT_TO_EMOJI.sub(lambda match: ALIAS_TO_EMOJI[match.group(0)], msg)
    return msg


def decode(msg) -> str:
    """
    Decode unicode Emoji values into Emoji aliases.
    :param msg: String to decode.
    :rtype: str
    Usage::
        >>> import emojis
        >>> emojis.decode('This is a message with emojis 😄 🐍')
        'This is a message with emojis :smile: :snake:'
    """
    msg = RE_EMOJI_TO_TEXT.sub(lambda match: EMOJI_TO_ALIAS[match.group(0)], msg)
    return msg


def get(msg) -> set:
    """
    Returns unique Emojis in the given string.
    :param msg: String to search for Emojis.
    :rtype: set
    """
    return {match.group() for match in RE_EMOJI_TO_TEXT.finditer(msg)}


def iter(msg):
    """
    Iterates over all Emojis found in the message.
    :param msg: String to search for Emojis.
    :rtype: iterator
    """
    return (match.group() for match in RE_EMOJI_TO_TEXT.finditer(msg))


def count(msg, unique=False):
    """
    Returns Emoji count in the given string.
    :param msg: String to search for Emojis.
    :param unique: (optional) Boolean, return unique values only.
    :rtype: int
    """
    if unique:
        return len({match.group() for match in RE_EMOJI_TO_TEXT.finditer(msg)})
    return len([match.group() for match in RE_EMOJI_TO_TEXT.finditer(msg)])
