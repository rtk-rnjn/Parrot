from __future__ import annotations

import logging
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

        pages = []
        for index, todo_item in enumerate(todo_items, start=1):
            due = todo_item.get("due")
            page = (
                f"{index}. **ID:** `{todo_item['id']}` - {todo_item['title']}\n"
                f"    [{todo_item['status'].replace('_', ' ').title()}] "
                f"{f'**Due:** {discord.utils.format_dt(due, style="R")}' if due else ''}\n"
            )
            pages.append(page)

        await self.bot.paginate(ctx, embed=discord.Embed(), pages=pages)

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

        embed = discord.Embed(
            title=f"ID: {todo_item['id']}",
            description=todo_item["title"],
        )

        async def callback(interaction: discord.Interaction[Parrot]):
            modal = TodoEditModal(todo_item)
            await interaction.response.send_modal(modal)

        view = discord.ui.View()
        edit_button = discord.ui.Button(label="Edit", style=discord.ButtonStyle.primary)
        edit_button.callback = callback

        view.add_item(edit_button)

        status_buttons = [
            TodoStatusButton(style=discord.ButtonStyle.secondary, status="pending", todo_item=todo_item),
            TodoStatusButton(style=discord.ButtonStyle.primary, status="in_progress", todo_item=todo_item),
            TodoStatusButton(style=discord.ButtonStyle.success, status="completed", todo_item=todo_item),
        ]

        for button in status_buttons:
            view.add_item(button)

        content = f"**Status:** {todo_item['status'].replace('_', ' ').title()}\n"
        due = todo_item.get("due")
        if due:
            content += f"**Due:** {discord.utils.format_dt(due, style='R')}\n"

        await ctx.reply(content=content, embed=embed, view=view)

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
        if not user:
            _log.warning("User with ID %s not found for to-do item ID %s", user.id, todo_item["id"])
            return

        try:
            await user.send(f"Your to-do item (ID: `{todo_item['id']}`) is due now: {todo_item['title']}")
        except discord.Forbidden:
            _log.warning("Cannot send DM to user with ID %s for to-do item ID %s", user.id, todo_item["id"])


async def setup(bot: Parrot) -> None:
    """Load the Todo cog."""
    await bot.add_cog(Todo(bot))
