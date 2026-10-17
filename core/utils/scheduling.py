"""Shared helpers for the to-do, reminder and agenda extensions.

Provides timezone-aware parsing, due-date presets and small component factories
so views stay declarative.
"""

from __future__ import annotations

import datetime
from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .time import FutureTime

if TYPE_CHECKING:
    from core import Bot

__all__ = (
    "DUE_PRESETS",
    "WhenModal",
    "as_utc",
    "clip",
    "format_due",
    "get_user_tz",
    "local_text",
    "make_button",
    "make_select",
    "parse_future",
    "preset_due",
)

Handler = Callable[[discord.Interaction], Awaitable[None]]
ValuesHandler = Callable[[discord.Interaction, list[str]], Awaitable[None]]

DUE_PRESETS: dict[str, str] = {
    "today": "Today evening",
    "tomorrow": "Tomorrow morning",
    "weekend": "This weekend",
    "next_week": "Next week",
    "custom": "Pick date and time...",
    "none": "No due date",
}


def clip(text: str, limit: int) -> str:
    """Collapse whitespace and truncate ``text`` to ``limit`` characters."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "\N{HORIZONTAL ELLIPSIS}"


def as_utc(value: datetime.datetime) -> datetime.datetime:
    """Treat naive datetimes (as returned by MongoDB) as UTC."""
    return value.replace(tzinfo=datetime.UTC) if value.tzinfo is None else value


def local_text(value: datetime.datetime, tz: datetime.tzinfo) -> str:
    """Format ``value`` in ``tz`` using a string the time parsers accept."""
    return as_utc(value).astimezone(tz).strftime("%Y-%m-%d %H:%M")


def format_due(value: datetime.datetime) -> str:
    """Render a Discord timestamp as ``relative (full date)``."""
    value = as_utc(value)
    return f"{discord.utils.format_dt(value, 'R')} ({discord.utils.format_dt(value, 'f')})"


async def get_user_tz(bot: Bot, user_id: int) -> datetime.tzinfo:
    """Return the user's configured timezone, defaulting to UTC."""
    reminder = bot.reminder
    return await reminder.get_tzinfo(user_id) if reminder is not None else datetime.UTC


async def parse_future(interaction: discord.Interaction[Bot], text: str) -> datetime.datetime:
    """Parse ``text`` as a future time in the invoking user's timezone.

    Raises
    ------
    commands.BadArgument
        If the text cannot be parsed or lies in the past.
    """
    tz = await get_user_tz(interaction.client, interaction.user.id)
    return FutureTime(text.strip(), now=interaction.created_at, tzinfo=tz).dt


def preset_due(key: str, tz: datetime.tzinfo) -> datetime.datetime | None:
    """Resolve a :data:`DUE_PRESETS` key to a concrete datetime in ``tz``."""
    now = datetime.datetime.now(tz)

    def at(day: datetime.datetime, hour: int) -> datetime.datetime:
        return day.replace(hour=hour, minute=0, second=0, microsecond=0)

    match key:
        case "today":
            return max(at(now, 18), now + datetime.timedelta(hours=1))
        case "tomorrow":
            return at(now + datetime.timedelta(days=1), 9)
        case "weekend":
            return at(now + datetime.timedelta(days=(5 - now.weekday()) % 7 or 7), 9)
        case "next_week":
            return at(now + datetime.timedelta(days=7 - now.weekday()), 9)
    return None


def make_button(
    handler: Handler,
    *,
    label: str | None = None,
    emoji: str | None = None,
    style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    disabled: bool = False,
) -> discord.ui.Button:
    button = discord.ui.Button(label=label, emoji=emoji, style=style, disabled=disabled)
    button.callback = handler  # pyright: ignore[reportAttributeAccessIssue]
    return button


def make_select(
    placeholder: str,
    options: Sequence[discord.SelectOption],
    handler: ValuesHandler,
    *,
    max_values: int = 1,
) -> discord.ui.Select:
    select = discord.ui.Select(placeholder=placeholder, options=list(options), max_values=max_values)

    async def callback(interaction: discord.Interaction) -> None:
        await handler(interaction, list(select.values))

    select.callback = callback
    return select


class WhenModal(discord.ui.Modal):
    """Ask for a single future time and pass the parsed datetime to ``on_pick``."""

    def __init__(
        self,
        *,
        heading: str,
        on_pick: Callable[[discord.Interaction, datetime.datetime], Awaitable[None]],
        default: str = "",
    ) -> None:
        super().__init__(title=heading)
        self.on_pick = on_pick
        self.when_input = discord.ui.TextInput(
            placeholder="in 2 hours, tomorrow 9am, 2026-12-01 18:00",
            default=default or None,
            max_length=60,
        )
        self.add_item(discord.ui.Label(text="When?", component=self.when_input))

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        try:
            when = await parse_future(interaction, self.when_input.value)
        except commands.BadArgument as error:
            await interaction.response.send_message(f"\N{WARNING SIGN} {error}", ephemeral=True)
            return
        await self.on_pick(interaction, when)
