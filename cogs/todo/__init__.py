from __future__ import annotations

import datetime
import random
import re
import textwrap
from typing import TYPE_CHECKING, Annotated

from dateutil.tz import gettz
from discord.utils import MISSING, format_dt
from jishaku.paginators import PaginatorEmbedInterface

import discord
from core import Cog, Context, Parrot
from discord import ui
from discord.ext import commands, old_menus as menus
from utilities.formats import plural
from utilities.robopages import FieldPageSource, RoboPages
from utilities.time import Time, UserFriendlyTime

if TYPE_CHECKING:
    from cogs.reminder import Reminders


class InvalidTime(commands.BadArgument):
    pass


MESSAGE_URL_REGEX = re.compile(
    r"https?://(?:(ptb|canary|www)\.)?discord(?:app)?\.com/channels/"
    r"(?P<guild_id>[0-9]{15,20}|@me)"
    r"/(?P<channel_id>[0-9]{15,20})/(?P<message_id>[0-9]{15,20})/?$",
)


class ConfirmationView(discord.ui.View):
    def __init__(self, *, timeout: float, author_id: int, delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: bool | None = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True

        await interaction.response.send_message("This confirmation dialog is not for you.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()


class ListFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    completed: bool = commands.flag(
        description="Include completed todos, defaults to False",
        default=False,
        aliases=["complete"],
    )
    pending: bool = commands.flag(description="Include pending todos, defaults to True", default=True)
    overdue: bool = commands.flag(description="Include overdue todos, defaults to True", default=True)
    brief: bool = commands.flag(
        description="Show a brief summary rather than detailed pages of todos, defaults to False",
        default=False,
        aliases=["compact"],
    )
    private: bool = commands.flag(description="Hide the todo list from others, defaults to False", default=False)


def snowflake_to_str(snowflake: int) -> str:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    base = len(alphabet)

    snowflake_str = ""

    while snowflake > 0:
        snowflake, idx = divmod(snowflake, base)
        snowflake_str = alphabet[idx] + snowflake_str

    return snowflake_str


def str_to_snowflake(snowflake_str: str) -> int:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    base = len(alphabet)

    snowflake = 0
    snowflake_str = snowflake_str[::-1]  # Reverse the input string

    for i, char in enumerate(snowflake_str):
        snowflake += alphabet.index(char) * (base**i)

    return snowflake


def ensure_future_time(
    argument: str,
    now: datetime.datetime,
    tzinfo: datetime.tzinfo,
) -> datetime.datetime:
    try:
        converter = Time(argument, now=now, tzinfo=tzinfo)
    except commands.BadArgument:
        random_future = now + datetime.timedelta(days=random.randint(3, 60))
        msg = f'Due date could not be parsed, sorry. Try something like "tomorrow" or "{random_future.date()}".'
        raise InvalidTime(msg) from None

    minimum_time = now + datetime.timedelta(minutes=5)
    if converter.dt < minimum_time:
        msg = "Due date must be at least 5 minutes in the future."
        raise InvalidTime(msg)

    return converter.dt


async def future_time_from_interaction(
    argument: str,
    interaction: discord.Interaction[Parrot],
) -> tuple[str, datetime.datetime]:
    reminder: Reminders = interaction.client.get_cog("Reminder")
    timezone = "UTC"
    tzinfo = datetime.timezone.utc
    if reminder is not None:
        timezone = await interaction.client.get_user_timezone(interaction.user.id)
        if timezone is not None:
            tzinfo = gettz(timezone) or datetime.timezone.utc
        else:
            timezone = "UTC"

    dt = ensure_future_time(argument, interaction.created_at, tzinfo)
    return timezone, dt


class TodoItem:
    def __init__(self, *, raw_data: dict, bot: Parrot) -> None:
        self._raw_data = raw_data
        self._id: int = raw_data["_id"]
        self.user_id: int = raw_data["user_id"]
        self.channel_id: int = raw_data["channel_id"]
        self.guild_id: int = raw_data["guild_id"]
        self.message_id: int = raw_data["message_id"]
        self.content: str = raw_data["content"]
        self.created_at: datetime.datetime = raw_data["created_at"]
        self.due_date: datetime.datetime = raw_data["due_date"]
        self.completed_at: datetime.datetime = raw_data["completed_at"]

        self.reminder_triggered: bool = raw_data["reminder_triggered"]

        self.message: discord.Message | None = None

        if self.due_date is not None:
            self.due_date = self.due_date.replace(tzinfo=datetime.timezone.utc)

        self.bot = bot
        self.cog: Todos = bot.get_cog("Todo")

    @property
    def id(self):
        return self._id

    def __repr__(self) -> str:
        return f"<TodoItem id={self._id} user_id={self.user_id}>"

    @property
    def jump_url(self) -> str:
        if self.message is not None:
            return self.message.jump_url

        return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}"

    def to_select_option(self, value=None) -> discord.SelectOption:
        return discord.SelectOption(
            label=self.content,
            value=value or str(self._id),
            emoji=self.emoji,
        )

    @property
    def completion_state(self) -> bool | None:
        """
        None -> Not completed
        True -> Completed
        False -> Expired
        """

        state = None
        if self.due_date is not None:
            due_date = self.due_date.replace(tzinfo=datetime.timezone.utc)
            if due_date < discord.utils.utcnow():
                state = False
        if self.completed_at:
            state = True
        return state

    @property
    def emoji(self) -> discord.PartialEmoji:
        if self.completion_state is None:
            return discord.PartialEmoji(name="\N{HEAVY LARGE CIRCLE}")

        if self.completion_state:
            return discord.PartialEmoji(name="\N{WHITE HEAVY CHECK MARK}")

        return discord.PartialEmoji(name="\N{HEAVY EXCLAMATION MARK SYMBOL}")

    @property
    def field_tuple(self) -> tuple[str, str]:
        state = self.completion_state
        if self.content is None:
            name = f"Todo {snowflake_to_str(self._id)}: No content"
        else:
            name = f"Todo {snowflake_to_str(self._id)}: {textwrap.shorten(self.content, width=50, placeholder='...')}"

        value = ""
        if state is False:
            if self.due_date:
                value = f"Expired: {discord.utils.format_dt(self.due_date, style='R')}"
        elif state is None and self.due_date:
            value = f"Due: {discord.utils.format_dt(self.due_date, style='R')}"
        elif self.completed_at:
            value = f"Completed: {discord.utils.format_dt(self.completed_at, style='R')}"

        return name, value or "..."

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"Todo ID: {snowflake_to_str(self._id)}",
            color=discord.Color.blurple(),
        )
        if self.message is not None:
            embed.description = self.message.content
            author = self.message.author
            embed.set_author(name=author, icon_url=author.display_avatar)
            if self.content:
                embed.add_field(name="Content", value=self.content, inline=False)
        else:
            embed.description = self.content

        if url := self.jump_url:
            embed.url = url

        if self.due_date:
            embed.set_footer(text="Due").timestamp = self.due_date
            if discord.utils.utcnow() > self.due_date:
                embed.colour = 0xFE5944
                embed.set_footer(text="Overdue")

        if self.completed_at:
            embed.set_footer(text="Completed").timestamp = self.completed_at
            embed.colour = 0x40AF7C

        return embed

    @property
    def channel(self) -> discord.PartialMessageable | None:
        if self.channel_id is not None:
            return self.bot.get_partial_messageable(self.channel_id, guild_id=self.guild_id)

        return None

    async def edit(
        self,
        *,
        content: str | None = discord.utils.MISSING,
        due_date: datetime.datetime | None = discord.utils.MISSING,
        message: discord.Message | None = discord.utils.MISSING,
        completed_at: datetime.datetime | None = discord.utils.MISSING,
    ):
        payload = {}
        if message:
            self.message = message
            payload["message_id"] = message.id
            payload["channel_id"] = message.channel.id
            if message.guild:
                payload["guild_id"] = message.guild.id
            else:
                payload["guild_id"] = None

        if content is not discord.utils.MISSING:
            payload["content"] = content

        if due_date is not discord.utils.MISSING:
            payload["due_date"] = due_date
            payload["reminder_triggered"] = False

        if completed_at is not discord.utils.MISSING:
            payload["completed_at"] = completed_at
            await self.bot.delete_timer(_id=self._id)

        for k, v in payload.items():
            setattr(self, k, v)

        collection = self.bot.user_db[f"{self.user_id}"]
        await collection.update_one({"_id": self._id}, {"$set": payload}, upsert=True)

        if due_date is not discord.utils.MISSING:
            await self.resync_with_reminders()

    async def delete(self) -> None:
        collection = self.bot.user_db[f"{self.user_id}"]
        await collection.delete_one({"_id": self._id})

    async def fetch_message(self) -> discord.Message | None:
        msg = await self.bot.get_or_fetch_message(self.channel_id, self.message_id)
        self.message = msg
        return msg

    async def resync_with_reminders(self) -> None:
        await self.bot.delete_timer(_id=self._id)
        await self.sync_with_reminders()

    async def sync_with_reminders(self) -> None:
        if not self.due_date:
            return
        await self.bot.create_timer(
            messageAuthor=self.user_id,
            messageURL=self.jump_url,
            message=self.message,  # this could be None
            expires_at=self.due_date.timestamp(),
            created_at=self.created_at.timestamp(),
            content=self.content,
            dm_notify=True,
            is_todo=True,
        )


class EditDueDateModal(ui.Modal, title="Edit Due Date"):
    due_date = ui.TextInput(label="Due Date", placeholder="e.g. 5m, 2022-12-31, tomorrow, etc.", max_length=100)

    def __init__(self, item: TodoItem, *, required: bool = False) -> None:
        super().__init__()
        self.item: TodoItem = item
        if required:
            self.due_date.min_length = 2

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        value = self.due_date.value
        if not value:
            due_date = None
            timezone = MISSING
        else:
            try:
                timezone, due_date = await future_time_from_interaction(value, interaction)
            except InvalidTime as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)
        await self.item.edit(due_date=due_date)
        if due_date is None:
            msg = "Removed due date."
        else:
            msg = f'Set due date to {format_dt(due_date)} ({format_dt(due_date, "R")}).'

        await interaction.followup.send(msg, ephemeral=True)


class EditDueDateButton(ui.Button):
    def __init__(
        self,
        todo: TodoItem,
        *,
        label: str = "Add Due Date",
        style: discord.ButtonStyle = discord.ButtonStyle.green,
        required: bool = False,
    ) -> None:
        super().__init__(label=label, style=style)
        self.todo = todo
        self.required: bool = required

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.todo.user_id:
            await interaction.response.send_message("This button is not meant for you, sorry.", ephemeral=True)
            return

        modal = EditDueDateModal(self.todo, required=self.required)
        await interaction.response.send_modal(modal)


class TodoPageSource(menus.ListPageSource):
    def __init__(self, todos: list[TodoItem]) -> None:
        super().__init__(entries=todos, per_page=1)

    async def format_page(self, menu: TodoPages, page: TodoItem):
        if page.channel is not None and page.message is None:
            await page.fetch_message()
        return page.embed


class BriefTodoPageSource(FieldPageSource):
    def __init__(self, todos: list[TodoItem]) -> None:
        super().__init__(entries=[todo.field_tuple for todo in todos], per_page=12)


class AddTodoModal(ui.Modal, title="Add Todo"):
    content = ui.TextInput(label="Content (optional)", max_length=1024, required=False, style=discord.TextStyle.long)

    due_date = ui.TextInput(
        label="Due Date (optional)",
        placeholder="e.g. 5m, 2022-12-31, tomorrow, etc.",
        max_length=100,
        required=False,
    )

    def __init__(self, cog: Todos, message: discord.Message) -> None:
        super().__init__(custom_id=f"todo-add-{message.id}")
        self.cog: Todos = cog
        self.message: discord.Message = message

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        due_date = self.due_date.value
        timezone = "UTC"
        if not due_date:
            due_date = None
        else:
            try:
                timezone, due_date = await future_time_from_interaction(due_date, interaction)
            except InvalidTime as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

        note = self.content.value or None
        await interaction.response.defer(ephemeral=True)
        item = await self.cog.add_todo(
            user_id=interaction.user.id,
            message=self.message,
            due_date=due_date,
            content=note,
            timezone=timezone,
        )
        await interaction.followup.send(
            content=f"<a:agreenTick:1011968947949666324> Added todo item {item.id}.",
            embed=item.embed,
            ephemeral=True,
        )


class TodoPages(RoboPages):
    def __init__(self, todos: list[TodoItem], ctx: Context) -> None:
        self.todos: list[TodoItem] = todos
        self.select_menu: ui.Select | None = None
        if 25 >= len(todos) > 1:
            select = ui.Select(
                placeholder=f"Select a todo ({len(todos)} todos found)",
                options=[todo.to_select_option(idx) for idx, todo in enumerate(todos)],
            )
            select.callback = self.selected
            self.select_menu = select

        super().__init__(TodoPageSource(todos), ctx=ctx, compact=True)

    @property
    def active_todo(self) -> TodoItem:
        return self.todos[self.current_page]

    def _update_labels(self, page_number: int) -> None:
        super()._update_labels(page_number)
        is_complete = self.active_todo.completed_at is not None
        button = self.complete_todo
        if is_complete:
            button.style = discord.ButtonStyle.grey
            button.label = "Mark as not complete"
        else:
            button.style = discord.ButtonStyle.green
            button.label = "Mark as complete"

        if self.select_menu:
            self.select_menu.options = [todo.to_select_option(idx) for idx, todo in enumerate(self.todos)]
            self.select_menu.placeholder = f"Select a todo ({plural(len(self.todos)):todo} found)"

    def fill_items(self) -> None:
        super().fill_items()
        if self.select_menu:
            self.clear_items()
            self.add_item(self.select_menu)

        self.add_item(self.complete_todo)
        self.add_item(self.edit_todo)
        self.add_item(self.delete_todo)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await super().on_error(interaction, error, item)

    async def selected(self, interaction: discord.Interaction) -> None:
        assert self.select_menu is not None
        page = int(self.select_menu.values[0])
        await self.show_page(interaction, page)

    @ui.button(label="Mark as complete", style=discord.ButtonStyle.green, row=2)
    async def complete_todo(self, interaction: discord.Interaction, button: ui.Button):
        active = self.active_todo
        if active.completed_at is not None:
            completed_at = None
            text = f"Successfully marked {active.id} as not complete"
        else:
            completed_at = interaction.created_at.replace(tzinfo=None)
            text = f"Successfully marked {active.id} as complete"

        await active.edit(completed_at=completed_at)
        self._update_labels(self.current_page)
        await interaction.response.edit_message(embed=active.embed, view=self)
        await interaction.followup.send(text, ephemeral=True)

    @ui.button(label="Edit", style=discord.ButtonStyle.grey, row=2)
    async def edit_todo(self, interaction: discord.Interaction, button: ui.Button):
        modal = EditTodoModal(self.active_todo)
        await interaction.response.send_modal(modal)
        await modal.wait()

        assert interaction.message is not None
        await interaction.message.edit(view=self, embed=modal.item.embed)

    @ui.button(label="Delete", style=discord.ButtonStyle.red, row=2)
    async def delete_todo(self, interaction: discord.Interaction, button: ui.Button):
        assert interaction.message is not None
        confirm = ConfirmationView(timeout=60.0, author_id=interaction.user.id, delete_after=True)
        await interaction.response.send_message("Are you sure you want to delete this todo?", view=confirm, ephemeral=True)
        await confirm.wait()
        if not confirm.value:
            await interaction.followup.send("Aborting", ephemeral=True)
            return

        todo = self.active_todo
        await todo.delete()
        del self.todos[self.current_page]

        if len(self.todos) == 0:
            await interaction.message.edit(view=None, content="No todos found!", embeds=[])
            self.stop()
            return

        previous = max(0, self.current_page - 1)
        await self.show_page(interaction, previous)


class EditTodoModal(ui.Modal, title="Edit Todo"):
    due_date = ui.TextInput(
        label="Due Date",
        placeholder="e.g. 5m, 2022-12-31, tomorrow, etc.",
        max_length=100,
        required=False,
    )
    message_url = ui.TextInput(
        label="Message",
        placeholder="https://discord.com/channels/182325885867786241/182328002154201088/182331989766963200",
        max_length=120,
        required=False,
    )
    content = ui.TextInput(label="Content", max_length=1024, style=discord.TextStyle.long, required=False)

    def __init__(self, item: TodoItem) -> None:
        super().__init__(custom_id=f"todo-edit-{item.id}")
        self.title = f"Edit Todo {item.id}"
        self.item: TodoItem = item
        if item.due_date is not None:
            self.due_date.default = item.due_date.isoformat(" ", "minutes")

        url = item.jump_url
        if url is not None:
            self.message_url.default = url

        if item.content is not None:
            self.content.default = item.content

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        await interaction.response.defer(ephemeral=True)
        kwargs: dict = {}
        due_date = self.due_date.value
        if due_date != self.due_date.default:
            if not due_date:
                due_date = None
            else:
                try:
                    timezone, due_date = await future_time_from_interaction(due_date, interaction)
                except InvalidTime as e:
                    await interaction.response.send_message(str(e), ephemeral=True)
                    return
                else:
                    kwargs["timezone"] = timezone

            kwargs["due_date"] = due_date

        message_url = self.message_url.value
        if message_url != self.message_url.default:
            if not message_url:
                message = None
            else:
                match = MESSAGE_URL_REGEX.match(message_url)
                if match is None:
                    await interaction.followup.send(
                        'Message URL could not be parsed, sorry. Be sure to use the "Copy Message Link" context menu!',
                        ephemeral=True,
                    )
                    return

                message_id = int(match.group("message_id"))
                channel_id = int(match.group("channel_id"))
                guild_id = match.group("guild_id")
                guild_id = None if guild_id == "@me" else int(guild_id)
                channel = self.item.bot.get_partial_messageable(channel_id, guild_id=guild_id)
                message = await self.item.bot.get_or_fetch_message(channel, message_id)
                if message is None:
                    await interaction.followup.send(
                        "That message was not found, sorry. Maybe it was deleted or I can't see it.",
                        ephemeral=True,
                    )

            kwargs["message"] = message

        note = self.content.value
        if note != self.content.default:
            kwargs["content"] = note

        if kwargs:
            await self.item.edit(**kwargs)

        await interaction.followup.send("Successfully edited todo!", ephemeral=True)


class AddAnywayButton(ui.Button):
    def __init__(self, cog: Todos, message: discord.Message, row: int = 2):
        super().__init__(label="Add Anyway", style=discord.ButtonStyle.blurple, row=row)
        self.cog = cog
        self.message = message

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AddTodoModal(self.cog, self.message))


class ShowTodo(ui.View):
    def __init__(self, item: TodoItem) -> None:
        super().__init__(timeout=600.0)
        self.item: TodoItem = item

        if item.completed_at is not None:
            self.complete_todo.style = discord.ButtonStyle.grey
            self.complete_todo.label = "Mark as not complete"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.item.user_id:
            await interaction.response.send_message("This button is not meant for you, sorry.", ephemeral=True)
            return False
        return True

    @ui.button(label="Mark as complete", style=discord.ButtonStyle.green)
    async def complete_todo(self, interaction: discord.Interaction, button: ui.Button):
        if button.style is discord.ButtonStyle.grey:
            completed_at = None
            button.style = discord.ButtonStyle.green
            button.label = "Mark as complete"
            text = f"Successfully marked {self.item.id} as not complete"
        else:
            completed_at = interaction.created_at.replace(tzinfo=None)
            button.style = discord.ButtonStyle.grey
            button.label = "Mark as not complete"
            text = f"Successfully marked {self.item.id} as complete"

        await self.item.edit(completed_at=completed_at)
        await interaction.response.edit_message(embed=self.item.embed, view=self)
        await interaction.followup.send(text, ephemeral=True)

    @ui.button(label="Edit", style=discord.ButtonStyle.grey)
    async def edit_todo(self, interaction: discord.Interaction, button: ui.Button):
        modal = EditTodoModal(self.item)
        await interaction.response.send_modal(modal)
        await modal.wait()
        assert interaction.message is not None
        await interaction.message.edit(view=self, embed=modal.item.embed)

    @ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def delete_todo(self, interaction: discord.Interaction, button: ui.Button):
        assert interaction.message is not None
        confirm = ConfirmationView(timeout=60.0, author_id=interaction.user.id, delete_after=True)
        await interaction.response.send_message("Are you sure you want to delete this todo?", view=confirm, ephemeral=True)
        await confirm.wait()
        if not confirm.value:
            await interaction.followup.send("Aborting", ephemeral=True)
            return

        await self.item.delete()
        await interaction.followup.send("Successfully deleted todo", ephemeral=True)
        await interaction.message.delete()
        self.stop()


class DueTodoView(ShowTodo):
    message: discord.Message

    async def on_timeout(self) -> None:
        try:
            await self.message.edit(view=None)
        except Exception:
            pass

    @ui.button(label="Snooze", style=discord.ButtonStyle.blurple)
    async def edit_todo(self, interaction: discord.Interaction, button: ui.Button):
        modal = EditDueDateModal(self.item, required=True)
        modal.title = "Snooze Todo"
        modal.due_date.placeholder = "10 minutes"
        modal.due_date.default = "10 minutes"
        modal.due_date.label = "Duration"
        await interaction.response.send_modal(modal)
        await modal.wait()

        assert interaction.message is not None
        await interaction.message.edit(view=self, embed=modal.item.embed)


class AmbiguousTodo(ShowTodo):
    def __init__(self, todos: list[TodoItem], message: discord.Message) -> None:
        todo = todos[0]
        super().__init__(todo)
        self.todos = todos

        if len(todos) > 25:
            placeholder = f"Select a todo (only 25 out of {len(todos)} todos shown)"
        else:
            placeholder = f"Select a todo ({len(todos)} todos found)"

        self.select = ui.Select(
            placeholder=placeholder,
            options=[todo.to_select_option(idx) for idx, todo in enumerate(todos[:25])],
        )
        self.select.callback = self.selected
        self.clear_items()
        self.add_item(self.select)
        self.add_item(self.complete_todo)
        self.add_item(self.edit_todo)
        self.add_item(self.delete_todo)
        self.add_item(AddAnywayButton(todo.cog, message))

    async def selected(self, interaction: discord.Interaction) -> None:
        index = int(self.select.values[0])
        self.item = self.todos[index]
        button = self.complete_todo
        if self.item.completed_at is not None:
            button.style = discord.ButtonStyle.grey
            button.label = "Mark as not complete"
        else:
            button.style = discord.ButtonStyle.green
            button.label = "Mark as complete"

        await interaction.response.edit_message(embed=self.item.embed, view=self)


class Todos(Cog):
    """For making the TODO list."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{WHITE HEAVY CHECK MARK}")

    async def add_todo(
        self,
        user_id: int,
        *,
        content: str | None = None,
        message: discord.Message | None = None,
        due_date: datetime.datetime | None = None,
        **kwargs,
    ) -> TodoItem:
        collection = self.bot.user_db[f"{user_id}"]
        payload = {}
        if message:
            payload = {**payload, "message_id": message.id, "channel_id": message.channel.id}
            if message.guild:
                payload["guild_id"] = message.guild.id
            else:
                payload["guild_id"] = None
        payload["content"] = content
        if due_date:
            payload["due_date"] = due_date
            payload["reminder_triggered"] = False
        else:
            payload["due_date"] = None
            payload["reminder_triggered"] = None

        payload = {
            **payload,
            "created_at": discord.utils.utcnow(),
            "completed_at": None,
            "_id": int(discord.utils.utcnow().timestamp() * 1000),
            "user_id": user_id,
            **kwargs,
        }
        await collection.insert_one(payload)
        item = TodoItem(raw_data=payload, bot=self.bot)
        await item.sync_with_reminders()
        return item

    async def get_todos(self, user_id: int) -> list[TodoItem]:
        collection = self.bot.user_db[f"{user_id}"]
        ls = []

        async for entry in collection.find({"user_id": user_id}):
            ls.append(TodoItem(raw_data=entry, bot=self.bot))

        return ls

    async def delete_all_todos(self, user_id: int) -> None:
        collection = self.bot.user_db[f"{user_id}"]
        await collection.delete_many({"user_id": user_id})
        await self.bot.restart_timer()

    async def get_todo_by_message(self, user_id: int, message_id: int) -> TodoItem | None:
        collection = self.bot.user_db[f"{user_id}"]
        entry = await collection.find_one({"message_id": message_id})
        if entry is None:
            return None

        return TodoItem(raw_data=entry, bot=self.bot)

    async def get_todo_by_id(self, user_id: int, _id: int) -> TodoItem | None:
        collection = self.bot.user_db[f"{user_id}"]
        entry = await collection.find_one({"_id": _id})
        if entry is None:
            return None

        return TodoItem(raw_data=entry, bot=self.bot)

    @commands.group(name="todo", invoke_without_command=True)
    async def todo(self, ctx: Context) -> None:
        """Manage a todo list"""
        if ctx.invoked_subcommand is None:
            ls = []
            async for entry in self.bot.user_db[f"{ctx.author.id}"].find({"user_id": ctx.author.id}):
                ls.append(TodoItem(raw_data=entry, bot=self.bot))

            if len(ls) == 0:
                await ctx.send("You don't have any todos.")
                return

            await TodoPages(ls, ctx).start()

    @todo.command(name="add")
    async def todo_add(
        self,
        ctx: Context,
        *,
        content: Annotated[str | None, commands.clean_content] = None,
    ) -> None:
        """Add a todo item. Can be used as a reply to another message."""

        try:
            await UserFriendlyTime().convert(ctx, str(content))
        except commands.BadArgument:
            pass

        if content is None and ctx.replied_reference and ctx.replied_reference.cached_message:
            content = ctx.replied_reference.cached_message.content

        if content is None:
            err = "There's nothing to remind you of here. You can reply to a message to be reminded of a message or you can pass the text you want to reminded of"
            raise commands.BadArgument(err)

        item = await self.add_todo(
            ctx.author.id,
            content=content,
            message=ctx.message,
            msg_url=ctx.message.jump_url,
        )
        view = discord.ui.View()
        view.add_item(EditDueDateButton(item))
        await ctx.reply(f"{ctx.author.mention} Added todo {item._id}.", view=view, embed=item.embed)

    @todo.command(name="list")
    async def todo_list(self, ctx: Context) -> None:
        """List all your todo items."""

        items = await self.get_todos(ctx.author.id)
        if not items:
            await ctx.reply(f"{ctx.author.mention} You don't have any todos.")
            return

        pages = commands.Paginator(prefix="", suffix="", max_size=1000)
        for idx, item in enumerate(items, start=1):
            pages.add_line(f"{idx}. {item.emoji} {item.content}")

        interface = PaginatorEmbedInterface(ctx.bot, pages, owner=ctx.author)
        await interface.send_to(ctx)

    @todo.command(name="delete")
    async def todo_delete(self, ctx: Context, *, id: str) -> None:
        """Delete a todo item."""

        if id.isdigit():
            _id = int(id)
        else:
            _id = str_to_snowflake(id)

        item = await self.get_todo_by_id(ctx.author.id, _id)
        if item is None:
            await ctx.reply(f"{ctx.author.mention} That todo item was not found.")
            return

        await item.delete()
        await ctx.reply(f"{ctx.author.mention} Successfully deleted todo {item._id}.")

    @todo.command(name="show")
    async def todo_show(self, ctx: Context, *, id: str) -> None:
        """Show a todo item."""

        if id.isdigit():
            _id = int(id)
        else:
            _id = str_to_snowflake(id)

        item = await self.get_todo_by_id(ctx.author.id, _id)
        if item is None:
            await ctx.reply(f"{ctx.author.mention} That todo item was not found.")
            return

        await ctx.reply(embed=item.embed, view=ShowTodo(item))

    @todo.command(name="complete")
    async def todo_complete(self, ctx: Context, *, id: str) -> None:
        """Mark a todo item as complete."""

        if id.isdigit():
            _id = int(id)
        else:
            _id = str_to_snowflake(id)

        item = await self.get_todo_by_id(ctx.author.id, _id)
        if item is None:
            await ctx.reply(f"{ctx.author.mention} That todo item was not found.")
            return

        if item.completed_at is not None:
            await ctx.reply(f"{ctx.author.mention} That todo item is already complete.")
            return

        await item.edit(completed_at=ctx.message.created_at.replace(tzinfo=None))
        await ctx.reply(f"{ctx.author.mention} Successfully marked todo {item._id} as complete.")

    @todo.command(name="incomplete")
    async def todo_incomplete(self, ctx: Context, *, id: str) -> None:
        """Mark a todo item as incomplete."""

        if id.isdigit():
            _id = int(id)
        else:
            _id = str_to_snowflake(id)

        item = await self.get_todo_by_id(ctx.author.id, _id)
        if item is None:
            await ctx.reply(f"{ctx.author.mention} That todo item was not found.")
            return

        if item.completed_at is None:
            await ctx.reply(f"{ctx.author.mention} That todo item is already incomplete.")
            return

        await item.edit(completed_at=None)
        await ctx.reply(f"{ctx.author.mention} Successfully marked todo {item._id} as incomplete.")

    @todo.command(name="due")
    async def todo_due(self, ctx: Context, *, id: str) -> None:
        """Set a due date for a todo item."""

        if id.isdigit():
            _id = int(id)
        else:
            _id = str_to_snowflake(id)

        item = await self.get_todo_by_id(ctx.author.id, _id)
        if item is None:
            await ctx.reply(f"{ctx.author.mention} That todo item was not found.")
            return

        modal = EditDueDateModal(item)
        await ctx.reply(embed=item.embed, view=modal)
        await modal.wait()
        await ctx.reply(embed=item.embed)

    @todo.command(name="edit")
    async def todo_edit(self, ctx: Context, *, id: str) -> None:
        """Edit a todo item."""

        if id.isdigit():
            _id = int(id)
        else:
            _id = str_to_snowflake(id)

        item = await self.get_todo_by_id(ctx.author.id, _id)
        if item is None:
            await ctx.reply(f"{ctx.author.mention} That todo item was not found.")
            return

        modal = EditTodoModal(item)
        await ctx.reply(embed=item.embed, view=modal)
        await modal.wait()
        await ctx.reply(embed=item.embed)

    @todo.command(name="clear")
    async def todo_clear(self, ctx: Context) -> None:
        """Clear all your todo items."""

        confirm = ConfirmationView(timeout=60.0, author_id=ctx.author.id, delete_after=True)
        await ctx.reply("Are you sure you want to delete all your todos?", view=confirm)
        await confirm.wait()
        if not confirm.value:
            await ctx.reply("Aborting")
            return

        await self.delete_all_todos(ctx.author.id)
        await ctx.reply("Successfully deleted all your todos.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Todos(bot))
