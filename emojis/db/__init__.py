"""
Emoji database.
"""

__all__ = [
    "Emoji",
    "get_emoji_aliases",
    "get_emoji_by_code",
    "get_emoji_by_alias",
    "get_emojis_by_tag",
    "get_emojis_by_category",
    "get_tags",
    "get_categories",
]

from .db import Emoji
from .utils import (
    get_emoji_aliases,
    get_emoji_by_code,
    get_emoji_by_alias,
    get_emojis_by_tag,
    get_emojis_by_category,
    get_tags,
    get_categories,
)
