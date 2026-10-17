from __future__ import annotations

import calendar
import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Self

import discord
from discord.ext import commands

from core.utils import BaseLayoutView, as_utc, clip, get_user_tz, make_button, make_select
from core.utils.database.models import TodoStatus

if TYPE_CHECKING:
    from core import Bot

    from . import Todo


_log = logging.getLogger(__name__)

WEEKDAYS = ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa")
MAX_AGENDA_LINES = 12
MAX_SELECT_OPTIONS = 25


@dataclass(frozen=True, slots=True)
class AgendaEntry:
    when: datetime.datetime
    icon: str
    text: str


def month_grid(year: int, month: int, *, today: datetime.date, marked_days: set[int]) -> str:
    """Render a Sunday-first month as a code block.

    Today is wrapped in brackets and days with tasks or reminders carry a dot.
    """
    title = f"{calendar.month_name[month]} {year}".center(len(WEEKDAYS) * 4).rstrip()
    header = "".join(f" {name} " for name in WEEKDAYS)

    def cell(day: int) -> str:
        if day == 0:
            return "    "
        if today == datetime.date(year, month, day):
            return f"[{day:>2}]"
        return f" {day:>2}{'\N{BULLET}' if day in marked_days else ' '}"

    weeks = ["".join(cell(day) for day in week).rstrip() for week in calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)]
    return "```\n" + "\n".join([title, header, *weeks]) + "\n```"


class AgendaPanel(BaseLayoutView):
    """Month calendar combining to-do due dates and reminders, with a day agenda."""

    def __init__(self, *, cog: Agenda, author: discord.User | discord.Member) -> None:
        super().__init__(author=author)
        self.cog = cog
        self.author = author
        self.tz: datetime.tzinfo = datetime.UTC
        self.entries: dict[datetime.date, list[AgendaEntry]] = defaultdict(list)
        today = datetime.datetime.now(self.tz).date()
        self.year, self.month, self.day = today.year, today.month, today.day

    @classmethod
    async def open(cls, cog: Agenda, author: discord.User | discord.Member) -> Self:
        panel = cls(cog=cog, author=author)
        await panel.reload()
        panel.year, panel.month = panel.today.year, panel.today.month
        panel.day = panel.default_day()
        panel.render()
        return panel

    @property
    def today(self) -> datetime.date:
        return datetime.datetime.now(self.tz).date()

    @property
    def selected_date(self) -> datetime.date:
        return datetime.date(self.year, self.month, self.day)

    def marked_days(self) -> set[int]:
        return {date.day for date in self.entries if (date.year, date.month) == (self.year, self.month)}

    def default_day(self) -> int:
        today = self.today
        if (today.year, today.month) == (self.year, self.month):
            return today.day
        return min(self.marked_days(), default=1)

    async def reload(self) -> None:
        bot = self.cog.bot
        self.tz = await get_user_tz(bot, self.author.id)
        self.entries = defaultdict(list)

        for item in await bot.database.get_user_todo_items(user_id=self.author.id):
            if item["due"]:
                done = item["status"] == TodoStatus.COMPLETED
                self._add(item["due"], "\N{WHITE HEAVY CHECK MARK}" if done else "\N{WHITE LARGE SQUARE}", item["title"])

        reminders = await bot.event_scheduler.search(event_name="reminder", metadata_filter={"user_id": self.author.id})
        for timer in reminders:
            self._add(timer["expires_at"], "\N{ALARM CLOCK}", str(timer["metadata"]["reminder_text"]))

    def _add(self, when: datetime.datetime, icon: str, text: str) -> None:
        local = as_utc(when).astimezone(self.tz)
        self.entries[local.date()].append(AgendaEntry(when=local, icon=icon, text=clip(text, 70)))

    async def refresh(self, interaction: discord.Interaction) -> None:
        await self.reload()
        self.render()
        await interaction.response.edit_message(view=self)

    async def redraw(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(view=self)

    def agenda_text(self) -> str:
        date = self.selected_date
        entries = sorted(self.entries.get(date, []), key=lambda entry: entry.when)
        heading = f"### {date:%A, %d %B}"
        if not entries:
            return f"{heading}\n*Nothing scheduled.*"

        lines = [f"{entry.icon} `{entry.when:%I:%M %p}` {entry.text}" for entry in entries[:MAX_AGENDA_LINES]]
        if len(entries) > MAX_AGENDA_LINES:
            lines.append(f"-# \N{HORIZONTAL ELLIPSIS}and {len(entries) - MAX_AGENDA_LINES} more")
        return f"{heading}\n" + "\n".join(lines)

    def render(self) -> None:
        self.clear_items()
        marked = self.marked_days()

        children: list[discord.ui.Item[Any]] = [
            discord.ui.TextDisplay("## \N{CALENDAR} Calendar"),
            discord.ui.TextDisplay(month_grid(self.year, self.month, today=self.today, marked_days=marked)),
            discord.ui.Separator(),
            discord.ui.TextDisplay(self.agenda_text()),
            discord.ui.Separator(visible=False),
        ]

        if marked:
            options = [
                discord.SelectOption(
                    label=f"{datetime.date(self.year, self.month, day):%a} {day}",
                    description=f"{len(self.entries[datetime.date(self.year, self.month, day)])} item(s)",
                    value=str(day),
                    default=day == self.day,
                )
                for day in sorted(marked)[:MAX_SELECT_OPTIONS]
            ]
            children.append(discord.ui.ActionRow(make_select("Jump to a day with plans\N{HORIZONTAL ELLIPSIS}", options, self._on_day)))

        children.append(
            discord.ui.ActionRow(
                make_button(partial(self._shift, -1), emoji="\N{BLACK LEFT-POINTING TRIANGLE}"),
                make_button(self._go_today, label="Today"),
                make_button(partial(self._shift, 1), emoji="\N{BLACK RIGHT-POINTING TRIANGLE}"),
                make_button(
                    self._new_task,
                    label="Task",
                    emoji="\N{HEAVY PLUS SIGN}",
                    style=discord.ButtonStyle.primary,
                ),
                make_button(
                    self._new_reminder,
                    label="Reminder",
                    emoji="\N{ALARM CLOCK}",
                    style=discord.ButtonStyle.primary,
                ),
            )
        )
        self.add_item(discord.ui.Container(*children, accent_colour=discord.Colour.blurple()))

    def _prefill(self) -> str:
        date = self.selected_date
        return f"{date:%Y-%m-%d} 09:00" if date > self.today else ""

    async def _on_day(self, interaction: discord.Interaction, values: list[str]) -> None:
        self.day = int(values[0])
        await self.redraw(interaction)

    async def _shift(self, delta: int, interaction: discord.Interaction) -> None:
        index = self.year * 12 + (self.month - 1) + delta
        self.year, self.month = divmod(index, 12)
        self.month += 1
        self.day = self.default_day()
        await self.redraw(interaction)

    async def _go_today(self, interaction: discord.Interaction) -> None:
        today = self.today
        self.year, self.month, self.day = today.year, today.month, today.day
        await self.refresh(interaction)

    async def _new_task(self, interaction: discord.Interaction) -> None:
        todo: Todo | None = self.cog.bot.get_cog("Todo")  # pyright: ignore[reportAssignmentType]
        if todo is None:
            await interaction.response.send_message("The to-do module isn't loaded.", ephemeral=True)
            return
        await todo.prompt_new_task(interaction, due_text=self._prefill(), refresh=self.refresh)

    async def _new_reminder(self, interaction: discord.Interaction) -> None:
        reminder = self.cog.bot.reminder
        if reminder is None:
            await interaction.response.send_message("The reminder module isn't loaded.", ephemeral=True)
            return
        await reminder.prompt_new_reminder(interaction, when_text=self._prefill(), refresh=self.refresh)


class Agenda(commands.Cog):
    """Month calendar of tasks and reminders."""

    help_category = "Todo"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    @commands.command(name="calendar", aliases=["cal", "agenda"])
    async def calendar(self, ctx: commands.Context[Bot]) -> None:
        """Browse your tasks and reminders on a month calendar.

        Days with plans are marked with a dot. Jump to a day to see its
        agenda, and add tasks or reminders for it without leaving the view.
        """
        panel = await AgendaPanel.open(self, ctx.author)
        await ctx.reply(view=panel)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Agenda(bot))
