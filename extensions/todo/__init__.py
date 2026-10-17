from __future__ import annotations

import datetime
import logging
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Any, Self

import discord
from bson import ObjectId
from discord.ext import commands

from core.utils import (
    DUE_PRESETS,
    BaseLayoutView,
    NoticeLayout,
    WhenModal,
    clip,
    format_due,
    get_user_tz,
    local_text,
    make_button,
    make_select,
    parse_future,
    preset_due,
)
from core.utils.database.models import TodoItem, TodoPriority, TodoStatus

from .agenda import Agenda

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 120

STATUS_LABELS = {
    TodoStatus.PENDING: "To do",
    TodoStatus.IN_PROGRESS: "In progress",
    TodoStatus.COMPLETED: "Completed",
}
STATUS_EMOJI = {
    TodoStatus.PENDING: "\N{WHITE LARGE SQUARE}",
    TodoStatus.IN_PROGRESS: "\N{LARGE BLUE DIAMOND}",
    TodoStatus.COMPLETED: "\N{WHITE HEAVY CHECK MARK}",
}
PRIORITY_LABELS = {
    TodoPriority.NONE: "No priority",
    TodoPriority.LOW: "Low",
    TodoPriority.MEDIUM: "Medium",
    TodoPriority.HIGH: "High",
}
PRIORITY_EMOJI = {
    TodoPriority.NONE: "\N{MEDIUM WHITE CIRCLE}",
    TodoPriority.LOW: "\N{LARGE GREEN CIRCLE}",
    TodoPriority.MEDIUM: "\N{LARGE YELLOW CIRCLE}",
    TodoPriority.HIGH: "\N{LARGE RED CIRCLE}",
}
PRIORITY_COLOURS = {
    TodoPriority.NONE: discord.Colour.blurple(),
    TodoPriority.LOW: discord.Colour.green(),
    TodoPriority.MEDIUM: discord.Colour.gold(),
    TodoPriority.HIGH: discord.Colour.red(),
}


class TodoFilter(StrEnum):
    ACTIVE = "active"
    TODAY = "today"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    ALL = "all"


FILTER_LABELS = {
    TodoFilter.ACTIVE: "Active",
    TodoFilter.TODAY: "Due today",
    TodoFilter.OVERDUE: "Overdue",
    TodoFilter.COMPLETED: "Completed",
    TodoFilter.ALL: "Everything",
}


@dataclass(slots=True)
class TaskDraft:
    """User input collected by :class:`TaskModal`."""

    title: str
    notes: str | None
    due: datetime.datetime | None
    priority: TodoPriority


def filter_items(items: list[TodoItem], selected: TodoFilter, tz: datetime.tzinfo) -> list[TodoItem]:
    """Return the items that belong to ``selected``, preserving order."""
    now = datetime.datetime.now(tz)

    def keep(item: TodoItem) -> bool:
        done = item["status"] == TodoStatus.COMPLETED
        due = item["due"]
        match selected:
            case TodoFilter.ALL:
                return True
            case TodoFilter.ACTIVE:
                return not done
            case TodoFilter.COMPLETED:
                return done
            case TodoFilter.OVERDUE:
                return not done and due is not None and due < now
            case TodoFilter.TODAY:
                return not done and due is not None and due.astimezone(tz).date() == now.date()

    return [item for item in items if keep(item)]


def describe_item(item: TodoItem) -> str:
    """Two-line summary of a task for list views."""
    done = item["status"] == TodoStatus.COMPLETED
    title = clip(item["title"], 80)
    headline = f"~~{title}~~" if done else f"**{title}**"

    details: list[str] = []
    if item["status"] == TodoStatus.IN_PROGRESS:
        details.append("In progress")
    if item["priority"] != TodoPriority.NONE:
        details.append(f"{PRIORITY_EMOJI[item['priority']]} {PRIORITY_LABELS[item['priority']]}")
    if item["due"]:
        overdue = not done and item["due"] < discord.utils.utcnow()
        details.append(f"{'\N{WHITE HEAVY CHECK MARK} Overdue \N{MIDDLE DOT} ' if overdue else ''}{discord.utils.format_dt(item['due'], 'R')}")

    suffix = f"\n-# {' \N{MIDDLE DOT} '.join(details)}" if details else ""
    return f"{STATUS_EMOJI[item['status']]} {headline}{suffix}"


class TaskModal(discord.ui.Modal):
    """Create or edit a task: title, notes, due date and priority in one form."""

    def __init__(
        self,
        *,
        heading: str,
        on_save: Callable[[discord.Interaction, TaskDraft], Awaitable[None]],
        item: TodoItem | None = None,
        tz: datetime.tzinfo = datetime.UTC,
        due_text: str = "",
    ) -> None:
        super().__init__(title=heading)
        self.on_save = on_save
        self.item = item
        self.initial_due_text = local_text(item["due"], tz) if item and item["due"] else due_text

        self.title_input = discord.ui.TextInput(
            default=item["title"] if item else None,
            placeholder="What needs doing?",
            max_length=MAX_TITLE_LENGTH,
        )
        self.notes_input = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            default=item["notes"] if item else None,
            placeholder="Details, links, anything you want to remember",
            required=False,
            max_length=1000,
        )
        self.due_input = discord.ui.TextInput(
            default=self.initial_due_text or None,
            placeholder="tomorrow 5pm, in 3 days, 2026-12-01 18:00",
            required=False,
            max_length=60,
        )
        current = item["priority"] if item else TodoPriority.NONE
        self.priority_select = discord.ui.Select(
            options=[
                discord.SelectOption(
                    label=PRIORITY_LABELS[priority],
                    value=priority.value,
                    emoji=PRIORITY_EMOJI[priority],
                    default=priority == current,
                )
                for priority in TodoPriority
            ],
            required=False,
        )

        for text, component in (
            ("Title", self.title_input),
            ("Notes", self.notes_input),
            ("Due (optional)", self.due_input),
            ("Priority", self.priority_select),
        ):
            self.add_item(discord.ui.Label(text=text, component=component))

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        raw_due = self.due_input.value.strip()
        due: datetime.datetime | None = None

        if raw_due and self.item and self.item["due"] and raw_due == self.initial_due_text:
            due = self.item["due"]
        elif raw_due:
            try:
                due = await parse_future(interaction, raw_due)
            except commands.BadArgument as error:
                await interaction.response.send_message(f"\N{WHITE HEAVY CHECK MARK} {error}", ephemeral=True)
                return

        priority = TodoPriority(self.priority_select.values[0]) if self.priority_select.values else TodoPriority.NONE
        draft = TaskDraft(
            title=self.title_input.value.strip(),
            notes=self.notes_input.value.strip() or None,
            due=due,
            priority=priority,
        )
        await self.on_save(interaction, draft)


class TodoPanel(BaseLayoutView):
    """Interactive task manager.

    Shows a filterable, paginated list where each row has a checkbox-style
    toggle. Selecting a task swaps the list for a detail card with status,
    priority and due-date selects, edit and delete actions.
    """

    PAGE_SIZE = 5

    def __init__(
        self,
        *,
        cog: Todo,
        author: discord.User | discord.Member,
        selected_id: ObjectId | None = None,
        current_filter: TodoFilter = TodoFilter.ACTIVE,
    ) -> None:
        super().__init__(author=author)
        self.cog = cog
        self.author = author
        self.selected_id = selected_id
        self.filter = current_filter
        self.page = 0
        self.confirming_delete = False
        self.items: list[TodoItem] = []
        self.tz: datetime.tzinfo = datetime.UTC

    @classmethod
    async def open(cls, cog: Todo, author: discord.User | discord.Member, **kwargs: Any) -> Self:
        panel = cls(cog=cog, author=author, **kwargs)
        await panel.reload()
        return panel

    @property
    def selected(self) -> TodoItem | None:
        return next((item for item in self.items if item["id"] == self.selected_id), None)

    async def reload(self) -> None:
        self.items = await self.cog.bot.database.get_user_todo_items(user_id=self.author.id)
        self.tz = await get_user_tz(self.cog.bot, self.author.id)
        self.render()

    async def refresh(self, interaction: discord.Interaction) -> None:
        await self.reload()
        await interaction.response.edit_message(view=self)

    async def redraw(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(view=self)

    def render(self) -> None:
        self.clear_items()
        item = self.selected
        if item is None:
            self.selected_id = None
            self.confirming_delete = False
        self.add_item(self._detail_container(item) if item else self._list_container())

    def _summary(self) -> str:
        done = sum(1 for item in self.items if item["status"] == TodoStatus.COMPLETED)
        overdue = len(filter_items(self.items, TodoFilter.OVERDUE, self.tz))
        return f"{len(self.items) - done} open \N{MIDDLE DOT} {overdue} overdue \N{MIDDLE DOT} {done} completed"

    def _list_container(self) -> discord.ui.Container:
        visible = filter_items(self.items, self.filter, self.tz)
        pages = max(1, math.ceil(len(visible) / self.PAGE_SIZE))
        self.page = min(self.page, pages - 1)
        start = self.page * self.PAGE_SIZE
        chunk = visible[start : start + self.PAGE_SIZE]

        children: list[discord.ui.Item[Any]] = [
            discord.ui.TextDisplay(f"## \N{WHITE HEAVY CHECK MARK} My Tasks \N{MIDDLE DOT} {FILTER_LABELS[self.filter]}"),
            discord.ui.TextDisplay(self._summary()),
            discord.ui.Separator(),
        ]
        if chunk:
            children.extend(self._item_section(item) for item in chunk)
        else:
            children.append(discord.ui.TextDisplay("*Nothing here. Press **New task** to add something.*"))
        children.append(discord.ui.Separator(visible=False))

        filter_options = [
            discord.SelectOption(
                label=f"{FILTER_LABELS[option]} ({len(filter_items(self.items, option, self.tz))})",
                value=option.value,
                default=option == self.filter,
            )
            for option in TodoFilter
        ]
        children.append(discord.ui.ActionRow(make_select("Show\N{HORIZONTAL ELLIPSIS}", filter_options, self._on_filter)))

        if chunk:
            open_options = [discord.SelectOption(label=clip(item["title"], 100), value=str(item["id"])) for item in chunk]
            children.append(discord.ui.ActionRow(make_select("Open a task\N{HORIZONTAL ELLIPSIS}", open_options, self._on_open)))

        has_completed = any(item["status"] == TodoStatus.COMPLETED for item in self.items)
        children.append(
            discord.ui.ActionRow(
                make_button(self._prev, emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", disabled=self.page <= 0),
                make_button(self._noop, label=f"{self.page + 1}/{pages}", disabled=True),
                make_button(self._next, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", disabled=self.page >= pages - 1),
                make_button(self._new, label="New task", emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.primary),
                make_button(self._clear_done, emoji="\N{BROOM}", disabled=not has_completed),
            )
        )
        if self.tz == datetime.UTC:
            children.append(discord.ui.TextDisplay("-# Times you type are read as UTC. Use the `timezone set` command to change that."))

        return discord.ui.Container(*children, accent_colour=discord.Colour.blurple())

    def _item_section(self, item: TodoItem) -> discord.ui.Section:
        done = item["status"] == TodoStatus.COMPLETED
        toggle = make_button(
            partial(self._toggle, item),
            emoji="\N{WHITE HEAVY CHECK MARK}" if done else "\N{WHITE LARGE SQUARE}",
            style=discord.ButtonStyle.success if done else discord.ButtonStyle.secondary,
        )
        return discord.ui.Section(discord.ui.TextDisplay(describe_item(item)), accessory=toggle)

    def _detail_container(self, item: TodoItem) -> discord.ui.Container:
        status, priority, due = item["status"], item["priority"], item["due"]
        info = [
            f"**Status:** {STATUS_EMOJI[status]} {STATUS_LABELS[status]}",
            f"**Priority:** {PRIORITY_EMOJI[priority]} {PRIORITY_LABELS[priority]}",
            f"**Due:** {format_due(due) if due else 'No due date'}",
            f"-# Created {discord.utils.format_dt(item['created_at'], 'R')}"
            + (f" \N{MIDDLE DOT} Completed {discord.utils.format_dt(item['completed_at'], 'R')}" if item["completed_at"] else ""),
        ]

        children: list[discord.ui.Item[Any]] = [discord.ui.TextDisplay(f"## {clip(item['title'], 200)}")]
        if item["notes"]:
            children.append(discord.ui.TextDisplay(item["notes"]))
        children += [
            discord.ui.Separator(),
            discord.ui.TextDisplay("\n".join(info)),
            discord.ui.Separator(visible=False),
        ]

        if self.confirming_delete:
            children += [
                discord.ui.TextDisplay("\N{WHITE HEAVY CHECK MARK} **Delete this task permanently?**"),
                discord.ui.ActionRow(
                    make_button(self._confirm_delete, label="Delete", style=discord.ButtonStyle.danger),
                    make_button(self._cancel_delete, label="Keep it"),
                ),
            ]
        else:
            status_options = [
                discord.SelectOption(label=STATUS_LABELS[option], value=option.value, emoji=STATUS_EMOJI[option], default=option == status)
                for option in TodoStatus
            ]
            priority_options = [
                discord.SelectOption(label=PRIORITY_LABELS[option], value=option.value, emoji=PRIORITY_EMOJI[option], default=option == priority)
                for option in TodoPriority
            ]
            due_options = [discord.SelectOption(label=label, value=key) for key, label in DUE_PRESETS.items()]
            done = status == TodoStatus.COMPLETED
            children += [
                discord.ui.ActionRow(make_select("Status", status_options, self._on_status)),
                discord.ui.ActionRow(make_select("Priority", priority_options, self._on_priority)),
                discord.ui.ActionRow(make_select("Due date", due_options, self._on_due)),
                discord.ui.ActionRow(
                    make_button(self._back, label="Back", emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"),
                    make_button(self._edit, label="Edit", emoji="\N{PENCIL}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.primary),
                    make_button(
                        partial(self._toggle, item),
                        label="Reopen" if done else "Complete",
                        emoji="\N{LEFTWARDS ARROW WITH HOOK}\N{VARIATION SELECTOR-16}" if done else "\N{WHITE HEAVY CHECK MARK}",
                        style=discord.ButtonStyle.secondary if done else discord.ButtonStyle.success,
                    ),
                    make_button(self._ask_delete, emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.danger),
                ),
            ]
        return discord.ui.Container(*children, accent_colour=PRIORITY_COLOURS[priority])

    async def _noop(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

    async def _prev(self, interaction: discord.Interaction) -> None:
        self.page -= 1
        await self.redraw(interaction)

    async def _next(self, interaction: discord.Interaction) -> None:
        self.page += 1
        await self.redraw(interaction)

    async def _on_filter(self, interaction: discord.Interaction, values: list[str]) -> None:
        self.filter = TodoFilter(values[0])
        self.page = 0
        await self.redraw(interaction)

    async def _on_open(self, interaction: discord.Interaction, values: list[str]) -> None:
        self.selected_id = ObjectId(values[0])
        await self.redraw(interaction)

    async def _back(self, interaction: discord.Interaction) -> None:
        self.selected_id = None
        await self.redraw(interaction)

    async def _toggle(self, item: TodoItem, interaction: discord.Interaction) -> None:
        done = item["status"] == TodoStatus.COMPLETED
        await self.cog.update_task(self.author.id, item["id"], status=TodoStatus.PENDING if done else TodoStatus.COMPLETED)
        await self.refresh(interaction)

    async def _on_status(self, interaction: discord.Interaction, values: list[str]) -> None:
        if item := self.selected:
            await self.cog.update_task(self.author.id, item["id"], status=TodoStatus(values[0]))
        await self.refresh(interaction)

    async def _on_priority(self, interaction: discord.Interaction, values: list[str]) -> None:
        if item := self.selected:
            await self.cog.update_task(self.author.id, item["id"], priority=TodoPriority(values[0]))
        await self.refresh(interaction)

    async def _on_due(self, interaction: discord.Interaction, values: list[str]) -> None:
        item = self.selected
        if item is None:
            await self.refresh(interaction)
            return
        if values[0] == "custom":
            await interaction.response.send_modal(WhenModal(heading="Set due date", on_pick=self._apply_due))
            return
        await self.cog.update_task(self.author.id, item["id"], due=preset_due(values[0], self.tz))
        await self.refresh(interaction)

    async def _apply_due(self, interaction: discord.Interaction, due: datetime.datetime) -> None:
        if self.selected_id is not None:
            await self.cog.update_task(self.author.id, self.selected_id, due=due)
        await self.refresh(interaction)

    async def _new(self, interaction: discord.Interaction) -> None:
        await self.cog.prompt_new_task(interaction, refresh=self.refresh)

    async def _edit(self, interaction: discord.Interaction) -> None:
        item = self.selected
        if item is None:
            await self.refresh(interaction)
            return
        await interaction.response.send_modal(TaskModal(heading="Edit task", on_save=self._apply_edit, item=item, tz=self.tz))

    async def _apply_edit(self, interaction: discord.Interaction, draft: TaskDraft) -> None:
        if self.selected_id is not None:
            await self.cog.update_task(
                self.author.id,
                self.selected_id,
                title=draft.title,
                notes=draft.notes,
                due=draft.due,
                priority=draft.priority,
            )
        await self.refresh(interaction)

    async def _ask_delete(self, interaction: discord.Interaction) -> None:
        self.confirming_delete = True
        await self.redraw(interaction)

    async def _cancel_delete(self, interaction: discord.Interaction) -> None:
        self.confirming_delete = False
        await self.redraw(interaction)

    async def _confirm_delete(self, interaction: discord.Interaction) -> None:
        if item := self.selected:
            await self.cog.delete_task(self.author.id, item)
        self.selected_id = None
        self.confirming_delete = False
        await self.refresh(interaction)

    async def _clear_done(self, interaction: discord.Interaction) -> None:
        await self.cog.clear_completed(self.author.id)
        await self.refresh(interaction)


class TodoDueLayout(BaseLayoutView):
    """DM sent when a task becomes due, with one-tap actions."""

    def __init__(self, *, cog: Todo, user: discord.User, item: TodoItem) -> None:
        super().__init__(author=user)
        self.cog = cog
        self.user = user
        self.item = item

        children: list[discord.ui.Item[Any]] = [
            discord.ui.TextDisplay("## \N{ALARM CLOCK} Task due"),
            discord.ui.TextDisplay(f"**{clip(item['title'], 200)}**"),
        ]
        if item["notes"]:
            children.append(discord.ui.TextDisplay(item["notes"]))
        children += [
            discord.ui.Separator(visible=False),
            discord.ui.ActionRow(
                make_button(self._complete, label="Mark done", emoji="\N{WHITE HEAVY CHECK MARK}", style=discord.ButtonStyle.success),
                make_button(partial(self._snooze, datetime.timedelta(hours=1)), label="Snooze 1h", emoji="\N{SLEEPING FACE}"),
                make_button(partial(self._snooze, datetime.timedelta(days=1)), label="Tomorrow", emoji="\N{CALENDAR}"),
            ),
        ]
        self.add_item(discord.ui.Container(*children, accent_colour=PRIORITY_COLOURS[item["priority"]]))

    async def _complete(self, interaction: discord.Interaction) -> None:
        await self.cog.update_task(self.user.id, self.item["id"], status=TodoStatus.COMPLETED)
        text = f"\N{WHITE HEAVY CHECK MARK} Marked **{clip(self.item['title'], 100)}** as done."
        await interaction.response.edit_message(view=NoticeLayout(text))

    async def _snooze(self, delta: datetime.timedelta, interaction: discord.Interaction) -> None:
        due = discord.utils.utcnow() + delta
        await self.cog.update_task(self.user.id, self.item["id"], due=due)
        text = f"\N{SLEEPING FACE} **{clip(self.item['title'], 100)}** snoozed until {discord.utils.format_dt(due, 'f')}."
        await interaction.response.edit_message(view=NoticeLayout(text))


class Todo(commands.Cog):
    """Task manager with due-date reminders."""

    help_emoji = "\N{WHITE HEAVY CHECK MARK}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def sync_due_timer(self, user_id: int, item: TodoItem) -> None:
        """Make the scheduler's ``todo_due`` timer for ``item`` match its current state."""
        await self.bot.event_scheduler.delete(
            event_name="todo_due",
            metadata_filter={"user_id": user_id, "todo_id": str(item["id"])},
            multiple=True,
        )
        due = item["due"]
        if due and item["status"] != TodoStatus.COMPLETED and due > discord.utils.utcnow():
            await self.bot.event_scheduler.create_timer(
                event_name="todo_due",
                expires_at=due,
                metadata={"user_id": user_id, "todo_id": str(item["id"]), "due": int(due.timestamp())},
            )

    async def create_task(self, user_id: int, draft: TaskDraft) -> TodoItem:
        item = await self.bot.database.create_user_todo_item(
            user_id=user_id,
            title=draft.title,
            notes=draft.notes,
            due=draft.due,
            priority=draft.priority,
        )
        await self.sync_due_timer(user_id, item)
        return item

    async def update_task(self, user_id: int, item_id: ObjectId, **changes: Any) -> TodoItem | None:
        updated = await self.bot.database.edit_user_todo_item(user_id=user_id, todo_item_id=item_id, **changes)
        if updated is not None:
            await self.sync_due_timer(user_id, updated)
        return updated

    async def delete_task(self, user_id: int, item: TodoItem) -> bool:
        await self.bot.event_scheduler.delete(
            event_name="todo_due",
            metadata_filter={"user_id": user_id, "todo_id": str(item["id"])},
            multiple=True,
        )
        return await self.bot.database.delete_user_todo_item(user_id=user_id, todo_item_id=item["id"])

    async def clear_completed(self, user_id: int) -> int:
        return len(await self.bot.database.clear_completed_user_todo_items(user_id=user_id))

    async def prompt_new_task(
        self,
        interaction: discord.Interaction,
        *,
        due_text: str = "",
        refresh: Callable[[discord.Interaction], Awaitable[None]] | None = None,
    ) -> None:
        """Open the new-task modal. ``refresh`` re-renders the caller's message after saving."""

        async def save(modal_interaction: discord.Interaction, draft: TaskDraft) -> None:
            item = await self.create_task(modal_interaction.user.id, draft)
            if refresh is not None:
                await refresh(modal_interaction)
                return
            await modal_interaction.response.send_message(f"\N{WHITE HEAVY CHECK MARK} Added **{clip(item['title'], 100)}**.", ephemeral=True)

        await interaction.response.send_modal(TaskModal(heading="New task", on_save=save, due_text=due_text))

    @commands.group(name="todo", aliases=["todos", "tasks", "task"], invoke_without_command=True)
    async def todo(self, ctx: commands.Context[Bot]) -> None:
        """Open your task manager.

        Tick tasks off, filter by due date, set priorities and edit everything
        with buttons and menus.
        """
        panel = await TodoPanel.open(self, ctx.author)
        await ctx.reply(view=panel)

    @todo.command(name="add", aliases=["create", "new", "+"])
    async def add_todo(self, ctx: commands.Context[Bot], *, title: str = commands.parameter(description="The task's title")) -> None:
        """Quickly add a task, then open it to set a due date, priority or notes."""
        if len(title) > MAX_TITLE_LENGTH:
            await ctx.reply(f"Titles can be at most {MAX_TITLE_LENGTH} characters. Use the **Edit** button to add longer details as notes.")
            return

        item = await self.create_task(ctx.author.id, TaskDraft(title=title, notes=None, due=None, priority=TodoPriority.NONE))
        panel = await TodoPanel.open(self, ctx.author, selected_id=item["id"])
        await ctx.reply(view=panel)

    @todo.command(name="list", aliases=["ls", "all"])
    async def list_todo(self, ctx: commands.Context[Bot]) -> None:
        """Show every task, including completed ones."""
        panel = await TodoPanel.open(self, ctx.author, current_filter=TodoFilter.ALL)
        await ctx.reply(view=panel)

    @todo.command(name="clear")
    async def clear_todo(self, ctx: commands.Context[Bot]) -> None:
        """Delete all completed tasks."""
        removed = await self.clear_completed(ctx.author.id)
        await ctx.reply(f"\N{BROOM} Removed {removed} completed task{'s' if removed != 1 else ''}.")

    @commands.Cog.listener()
    async def on_todo_due_timer_complete(self, *, metadata: dict[str, Any]) -> None:
        todo_id = metadata.get("todo_id")
        if not todo_id:
            return

        user_id = metadata["user_id"]
        item = await self.bot.database.get_user_todo_item(user_id=user_id, todo_item_id=ObjectId(todo_id))
        if item is None or item["status"] == TodoStatus.COMPLETED or item["due"] is None:
            return
        if int(item["due"].timestamp()) != metadata.get("due"):
            return

        user = await self.bot.get_or_fetch_user(user_id)
        if user is None:
            _log.warning("User %s not found for to-do item %s", user_id, todo_id)
            return

        try:
            await user.send(view=TodoDueLayout(cog=self, user=user, item=item))
        except discord.HTTPException:
            _log.warning("Cannot DM user %s for to-do item %s", user_id, todo_id)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Todo(bot))
    await bot.add_cog(Agenda(bot))
