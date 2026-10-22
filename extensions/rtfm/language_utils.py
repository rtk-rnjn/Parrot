from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

import arrow
import discord

from core.utils import truncate


def safe(text_value: str | None, limit: int = 200) -> str:
    """One escaped, mention-free line of user-provided text."""
    flat = " ".join((text_value or "").split())
    return truncate(discord.utils.escape_markdown(discord.utils.escape_mentions(flat)), limit)


def code(text_value: str, limit: int = 60) -> str:
    return f"`{truncate(text_value.replace('`', chr(39)), limit)}`"


def parse_time(iso: str | None) -> datetime | None:
    if not iso or not isinstance(iso, str):
        return None
    try:
        return arrow.get(iso).datetime
    except ValueError, TypeError:
        return None


def when(iso: str | None, style: Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"] = "R") -> str | None:
    moment = parse_time(iso)
    return discord.utils.format_dt(moment, style) if moment else None


def dated(iso: str | None) -> str | None:
    return f"{when(iso, 'D')} ({when(iso)})" if parse_time(iso) else None


def collect(*items: discord.ui.Item | None) -> list[discord.ui.Item]:
    return [item for item in items if item is not None]


def text(content: str) -> discord.ui.TextDisplay:
    return discord.ui.TextDisplay(content)


def facts(*pairs: tuple[str, str | None]) -> discord.ui.TextDisplay | None:
    lines = [f"**{label}**: {value}" for label, value in pairs if value]
    return text("\n".join(lines)) if lines else None


def valid_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("http://", "https://")) and len(url) <= 512


def header(title: str, subtitle: str | None = None, *extra: str, thumbnail: str | None = None) -> discord.ui.Item:
    """Title block, with an optional thumbnail on the right."""
    parts = [text(f"## {title}" + (f"\n-# {subtitle}" if subtitle else ""))]
    parts.extend(text(line) for line in extra if line)
    if thumbnail and valid_url(thumbnail):
        return discord.ui.Section(*parts, accessory=discord.ui.Thumbnail(thumbnail))
    return text("\n".join(part.content for part in parts))


def pack(entries: Sequence[str], limit: int = 900) -> str:
    """Inline-code chips that fit in ``limit`` characters, followed by how many were left out."""
    shown: list[str] = []
    used = 0
    for entry in entries:
        piece = f"`{entry.replace('`', chr(39))}`"
        if used + len(piece) + 1 > limit:
            break
        shown.append(piece)
        used += len(piece) + 1
    left = len(entries) - len(shown)
    return " ".join(shown) + (f" *+{left} more*" if left else "")
