from __future__ import annotations

from . import db


def get_emoji_aliases():
    """
    Returns all Emojis as a dict (key = alias, value = unicode).
    :rtype: dict
    """
    emoji_aliases = {}

    for emoji in db.EMOJI_DB:
        for alias in emoji.aliases:
            alias = ":{0}:".format(alias)
            emoji_aliases[alias] = emoji.emoji

    return emoji_aliases


def get_emoji_by_code(code):
    """
    Returns Emoji by Unicode code.
    :param code: Emoji Unicode code.
    :rtype: emojis.db.Emoji
    """
    try:
        return next(filter(lambda emoji: code == emoji.emoji, db.EMOJI_DB))
    except StopIteration:
        return None


def get_emoji_by_alias(alias):
    """
    Returns Emoji by alias.
    :param alias: Emoji alias.
    :rtype: emojis.db.Emoji
    """
    try:
        return next(filter(lambda emoji: alias in emoji.aliases, db.EMOJI_DB))
    except StopIteration:
        return None


def get_emojis_by_tag(tag):
    """
    Returns all Emojis from selected tag.
    :param tag: Tag name to filter (case-insensitive).
    :rtype: iter
    """
    return filter(lambda emoji: tag.lower() in emoji.tags, db.EMOJI_DB)


def get_emojis_by_category(category):
    """
    Returns all Emojis from selected category.
    :param tag: Category name to filter (case-insensitive).
    :rtype: iter
    """
    return filter(lambda emoji: category.lower() == emoji.category.lower(), db.EMOJI_DB)


def get_tags():
    """
    Returns all tags available.
    :rtype: set
    """
    return {tag for emoji in db.EMOJI_DB for tag in emoji.tags}


def get_categories():
    """
    Returns all categories available.
    :rtype: set
    """
    return {emoji.category for emoji in db.EMOJI_DB}
