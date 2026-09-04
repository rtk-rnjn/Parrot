from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Literal, TypedDict

import discord
from bson import ObjectId
from discord.ext import commands

from core.utils import FutureTime
from core.utils.database_manager.models import TodoItem

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.todo")


class TodoItemMetadata(TypedDict):
    item: TodoItem
    user_id: int


class TodoAddDueDateModal(discord.ui.Modal, title="Add Due Date"):
    due_date = discord.ui.TextInput(
        label="Due Date",
        placeholder="Eg. 5m, tomorrow, 3 days, etc.",
        required=True,
    )

    def __init__(self, todo_item: TodoItem):
        self.todo_item = todo_item
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction[Parrot]):
        future_time = FutureTime(self.due_date.value)
        datetime = future_time.dt
        await interaction.client.database_manager.edit_user_todo_item(
            user_id=interaction.user.id,
            todo_item_id=self.todo_item["id"],
            due=datetime,
        )
        self.todo_item["due"] = datetime

        relative_time = discord.utils.format_dt(datetime, style="R")
        await interaction.response.send_message(f"For to-do item (ID: `{self.todo_item['id']}`), due {relative_time}", ephemeral=True)
        await interaction.client.timer_manager.create_timer(
            event_name="todo_due",
            expires_at=datetime,
            metadata=TodoItemMetadata(item=self.todo_item, user_id=interaction.user.id),
        )


class TodoEditModal(discord.ui.Modal, title="Edit To-Do Item"):
    title_input = discord.ui.TextInput(
        label="Title",
        placeholder="Enter the new title for the to-do item",
        required=True,
    )

    due_date_input = discord.ui.TextInput(
        label="Due Date",
        placeholder="Enter the new due date for the to-do item (optional)",
        required=False,
    )

    notes_input = discord.ui.TextInput(
        label="Notes",
        placeholder="Enter any notes for the to-do item (optional)",
        required=False,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, todo_item: TodoItem):
        self.todo_item = todo_item
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction[Parrot]):
        future_time = FutureTime(self.due_date_input.value) if self.due_date_input.value else None
        datetime = future_time.dt if future_time else None
        await interaction.client.database_manager.edit_user_todo_item(
            user_id=interaction.user.id,
            todo_item_id=self.todo_item["id"],
            title=self.title_input.value,
            notes=self.notes_input.value,
            due=datetime,
        )
        await interaction.response.send_message(
            f"Updated to-do item (ID: `{self.todo_item['id']}`)",
            ephemeral=True,
        )


class TodoCreateView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member, todo_item: TodoItem):
        self.author = author
        self.todo_item = todo_item
        super().__init__()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Add due date", style=discord.ButtonStyle.primary)
    async def add_due_date(self, interaction: discord.Interaction[Parrot], button: discord.ui.Button):
        modal = TodoAddDueDateModal(self.todo_item)
        await interaction.response.send_modal(modal)


class TodoStatusButton(discord.ui.Button):
    def __init__(self, *, style: discord.ButtonStyle, status: Literal["pending", "in_progress", "completed"], todo_item: TodoItem):
        label = status.replace("_", " ").title()
        super().__init__(label=label, style=style)
        self.status: Literal["pending", "in_progress", "completed"] = status
        self.todo_item = todo_item

    async def callback(self, interaction: discord.Interaction[Parrot]):
        await interaction.client.database_manager.edit_user_todo_item(
            user_id=interaction.user.id,
            todo_item_id=self.todo_item["id"],
            status=self.status,
        )
        await interaction.response.send_message(f"Updated to-do item (ID: `{self.todo_item['id']}`) to status: {self.status}", ephemeral=True)


class TodoViewLayout(discord.ui.LayoutView):
    def __init__(self, author: discord.User | discord.Member, todo_item: TodoItem):
        self.author = author
        self.todo_item = todo_item
        super().__init__()

        views = []
        notes = todo_item.get("notes")
        if notes:
            views.append(discord.ui.TextDisplay(f"**Notes:** {notes}"))

        status = todo_item["status"]
        due = todo_item.get("due")

        buttons = [
            TodoStatusButton(style=discord.ButtonStyle.secondary, status="pending", todo_item=todo_item),
            TodoStatusButton(style=discord.ButtonStyle.primary, status="in_progress", todo_item=todo_item),
            TodoStatusButton(style=discord.ButtonStyle.success, status="completed", todo_item=todo_item),
        ]

        action_row = discord.ui.ActionRow(*buttons)

        container = discord.ui.Container(
            discord.ui.TextDisplay(f"## ID: {self.todo_item['id']}"),
            discord.ui.TextDisplay(f"### {self.todo_item['title']}"),
            *views,
            discord.ui.Separator(),
            discord.ui.TextDisplay(f"**Status:** {status.replace('_', ' ').title()}"),
            discord.ui.TextDisplay(f"**Due:** {discord.utils.format_dt(due, style='R') if due else 'No due date'}"),
            discord.ui.Separator(visible=False),
            action_row,
        )

        async def callback(interaction: discord.Interaction[Parrot]):
            modal = TodoEditModal(todo_item)
            await interaction.response.send_modal(modal)

        edit_button = discord.ui.Button(label="Edit", style=discord.ButtonStyle.primary)
        edit_button.callback = callback

        self.add_item(container)
        self.add_item(discord.ui.ActionRow(edit_button))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
            return False
        return True


class TodoListLayout(discord.ui.LayoutView):
    ITEMS_PER_PAGE = 5

    def __init__(
        self,
        author: discord.User | discord.Member,
        todo_items: list[TodoItem],
    ):
        super().__init__()

        self.author = author
        self.todo_items = todo_items
        self.current_page = 0

        self._render()

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(len(self.todo_items) / self.ITEMS_PER_PAGE))

    @property
    def offset(self) -> int:
        return self.current_page * self.ITEMS_PER_PAGE

    def _render(self) -> None:
        self.clear_items()

        start = self.offset
        end = start + self.ITEMS_PER_PAGE

        title = f"To-Do List (Page {self.current_page + 1}/{self.total_pages})"
        title_display = discord.ui.TextDisplay(f"## {title}")

        items = [title_display] + [
            component for todo_item in self.todo_items[start:end] for component in (self._create_item(todo_item), discord.ui.Separator())
        ]

        self.container = discord.ui.Container(
            *items,
            discord.ui.ActionRow(
                self._create_navigation_button("Previous", self.prev_page, discord.ButtonStyle.secondary),
                self._create_navigation_button("Next", self.next_page, discord.ButtonStyle.secondary),
            ),
        )

        self.add_item(self.container)

    def _create_item(self, todo_item: TodoItem) -> discord.ui.Section:
        due = todo_item.get("due")
        status = todo_item["status"].replace("_", " ").title()
        due_text = discord.utils.format_dt(due, style="R") if due else "No due date"

        button = discord.ui.Button(label="View", style=discord.ButtonStyle.primary)
        button.callback = self.create_callback(todo_item)

        return discord.ui.Section(discord.ui.TextDisplay(f"{todo_item['title']} - [{status}] {due_text}"), accessory=button)

    def _create_navigation_button(self, label: str, callback, style: discord.ButtonStyle) -> discord.ui.Button:
        button = discord.ui.Button(label=label, style=style)
        button.callback = callback

        if (label == "Previous" and self.current_page <= 0) or (label == "Next" and self.current_page >= self.total_pages - 1):
            button.disabled = True

        return button

    def create_callback(self, todo_item: TodoItem):
        async def callback(interaction: discord.Interaction[Parrot]):
            view = TodoViewLayout(author=self.author, todo_item=todo_item)
            await interaction.response.send_message(view=view, ephemeral=True)

        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
            return False

        return True

    async def next_page(self, interaction: discord.Interaction[Parrot]):
        if self.current_page >= self.total_pages - 1:
            return

        self.current_page += 1
        await self._update(interaction)

    async def prev_page(self, interaction: discord.Interaction[Parrot]):
        if self.current_page <= 0:
            return

        self.current_page -= 1
        await self._update(interaction)

    async def _update(self, interaction: discord.Interaction[Parrot]):
        self._render()
        await interaction.response.edit_message(view=self)


class Todo(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.group(name="todo")
    async def todo(self, ctx: commands.Context) -> None:
        """Manage your to-do list."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @todo.command(name="add")
    async def add_todo(self, ctx: commands.Context[Parrot], *, title: str) -> None:
        """Add a new to-do item."""
        todo_item = await self.bot.database_manager.create_user_todo_item(user_id=ctx.author.id, title=title)
        embed = discord.Embed(
            title=f"ID: {todo_item['id']}",
            description=todo_item["title"],
        )
        view = TodoCreateView(author=ctx.author, todo_item=todo_item)
        await ctx.reply(embed=embed, view=view)

    @todo.command(name="list", aliases=["ls"])
    async def list_todo(self, ctx: commands.Context[Parrot]) -> None:
        """List your to-do items."""
        todo_items = await self.bot.database_manager.get_user_todo_items(user_id=ctx.author.id)
        if not todo_items:
            await ctx.reply("You have no to-do items.")
            return

        view = TodoListLayout(author=ctx.author, todo_items=todo_items)
        await ctx.reply(view=view)

    @todo.command(name="remove", aliases=["delete", "rm", "del"])
    async def remove_todo(self, ctx: commands.Context[Parrot], *, id: str) -> None:  # noqa: A002
        """Remove a to-do item."""
        removed = await self.bot.database_manager.delete_user_todo_item(user_id=ctx.author.id, todo_item_id=ObjectId(id))
        if removed:
            await ctx.reply(f"Removed to-do item (ID: `{id}`)")
        else:
            await ctx.reply(f"No to-do item found with ID: `{id}`")

    @todo.command(name="view", aliases=["show"])
    async def view_todo(self, ctx: commands.Context[Parrot], *, id: str) -> None:  # noqa: A002
        """View a to-do item."""
        todo_item = await self.bot.database_manager.get_user_todo_item(user_id=ctx.author.id, todo_item_id=ObjectId(id))
        if not todo_item:
            await ctx.reply(f"No to-do item found with ID: `{id}`")
            return

        view = TodoViewLayout(author=ctx.author, todo_item=todo_item)
        await ctx.reply(view=view)

    @commands.Cog.listener()
    async def on_todo_due_timer_complete(self, metadata: TodoItemMetadata) -> None:
        """Handle the completion of a to-do due timer."""
        user = self.bot.get_user(metadata["user_id"])
        if user is None:
            try:
                user = await self.bot.fetch_user(metadata["user_id"])
            except discord.NotFound:
                _log.warning("User with ID %s not found for to-do item ID %s", metadata["user_id"], metadata["item"]["id"])
                return

        todo_item = metadata["item"]

        try:
            await user.send(f"Your to-do item (ID: `{todo_item['id']}`) is due now: {todo_item['title']}")
        except discord.Forbidden:
            _log.warning("Cannot send DM to user with ID %s for to-do item ID %s", user.id, todo_item["id"])


async def setup(bot: Parrot) -> None:
    """Load the Todo cog."""
    await bot.add_cog(Todo(bot))
