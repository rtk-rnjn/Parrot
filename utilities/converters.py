from __future__ import annotations

from utilities.regex import TIME_REGEX
from discord.ext.commands import clean_content
from typing import Optional


def convert_bool(text: str) -> Optional[bool]:
    if text.lower() in ('yes', 'y', 'true', 't', '1', 'enable', 'on', 'o'):
        return True
    elif text.lower() in ('no', 'n', 'false', 'f', '0', 'disable', 'off', 'x'):
        return False
    else:
        return None


def reason_convert(text: clean_content) -> str:
    return text[:450:]
