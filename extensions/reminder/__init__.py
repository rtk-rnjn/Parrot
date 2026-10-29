from __future__ import annotations

import contextlib
import datetime
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Annotated, Any, NamedTuple, NotRequired, Self, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

import discord
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from lxml import etree
from rapidfuzz import fuzz, process

from core.utils import (
    BaseLayoutView,
    BaseView,
    FriendlyTimeResult,
    TimerData,
    UserFriendlyTime,
    WhenModal,
    as_utc,
    clip,
    get_user_tz,
    local_text,
    make_button,
    make_select,
    parse_future,
)

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)
HTTP_OK = 200

REPEAT_LABELS = {
    "none": "Does not repeat",
    "daily": "Every day",
    "weekly": "Every week",
    "monthly": "Every month",
}
REPEAT_STEPS = {
    "daily": relativedelta(days=1),
    "weekly": relativedelta(weeks=1),
    "monthly": relativedelta(months=1),
}
SNOOZE_OPTIONS = {
    "5m": ("5 minutes", datetime.timedelta(minutes=5)),
    "15m": ("15 minutes", datetime.timedelta(minutes=15)),
    "30m": ("30 minutes", datetime.timedelta(minutes=30)),
    "1h": ("1 hour", datetime.timedelta(hours=1)),
    "3h": ("3 hours", datetime.timedelta(hours=3)),
    "1d": ("Tomorrow", datetime.timedelta(days=1)),
}
POPULAR_TIMEZONES = (
    ("India", "Asia/Kolkata"),
    ("New York", "America/New_York"),
    ("Chicago", "America/Chicago"),
    ("Denver", "America/Denver"),
    ("Los Angeles", "America/Los_Angeles"),
    ("Toronto", "America/Toronto"),
    ("S\N{LATIN SMALL LETTER A WITH TILDE}o Paulo", "America/Sao_Paulo"),
    ("London", "Europe/London"),
    ("Paris", "Europe/Paris"),
    ("Berlin", "Europe/Berlin"),
    ("Athens", "Europe/Athens"),
    ("Istanbul", "Europe/Istanbul"),
    ("Moscow", "Europe/Moscow"),
    ("Dubai", "Asia/Dubai"),
    ("Dhaka", "Asia/Dhaka"),
    ("Bangkok", "Asia/Bangkok"),
    ("Shanghai", "Asia/Shanghai"),
    ("Tokyo", "Asia/Tokyo"),
    ("Brisbane", "Australia/Brisbane"),
    ("Sydney", "Australia/Sydney"),
    ("Auckland", "Pacific/Auckland"),
)


class ReminderMetadata(TypedDict):
    user_id: int
    guild_id: int
    channel_id: int
    message_id: int
    reminder_text: str
    due: NotRequired[int]
    repeat: NotRequired[str]


class ScheduledReminder(NamedTuple):
    timer_id: ObjectId
    when: datetime.datetime
    metadata: ReminderMetadata


@dataclass(slots=True)
class ReminderDraft:
    """User input collected by :class:`ReminderModal`."""

    text: str
    when: datetime.datetime
    repeat: str


def with_repeat(metadata: ReminderMetadata, repeat: str) -> ReminderMetadata:
    """Return a copy of ``metadata`` with ``repeat`` applied (``"none"`` removes it)."""
    updated = dict(metadata)
    if repeat in REPEAT_STEPS:
        updated["repeat"] = repeat
    else:
        updated.pop("repeat", None)
    return updated  # pyright: ignore[reportReturnType]


def jump_url(metadata: ReminderMetadata) -> str | None:
    if not metadata["message_id"]:
        return None
    return f"https://discord.com/channels/{metadata['guild_id'] or '@me'}/{metadata['channel_id']}/{metadata['message_id']}"


def can_send(channel: object) -> bool:
    if isinstance(channel, discord.abc.GuildChannel | discord.Thread):
        return channel.permissions_for(channel.guild.me).send_messages
    return isinstance(channel, discord.DMChannel)


def repeat_options(current: str = "none") -> list[discord.SelectOption]:
    return [discord.SelectOption(label=label, value=key, default=key == current) for key, label in REPEAT_LABELS.items()]


class ReminderModal(discord.ui.Modal):
    """Create or edit a reminder: what, when and how often."""

    def __init__(
        self,
        *,
        heading: str,
        on_save: Callable[[discord.Interaction, ReminderDraft], Awaitable[None]],
        text: str = "",
        when_text: str = "",
        repeat: str = "none",
        keep_when: datetime.datetime | None = None,
    ) -> None:
        super().__init__(title=heading)
        self.on_save = on_save
        self.initial_when_text = when_text
        self.keep_when = keep_when

        self.text_input = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            default=text or None,
            placeholder="Call the bank, submit the report...",
            max_length=500,
        )
        self.when_input = discord.ui.TextInput(
            default=when_text or None,
            placeholder="in 2 hours, tomorrow 9am, 2026-12-01 18:00",
            max_length=60,
        )
        self.repeat_select = discord.ui.Select(options=repeat_options(repeat), required=False)

        for label, component in (("Remind me to", self.text_input), ("When", self.when_input), ("Repeat", self.repeat_select)):
            self.add_item(discord.ui.Label(text=label, component=component))

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        raw_when = self.when_input.value.strip()
        if self.keep_when and raw_when == self.initial_when_text:
            when = self.keep_when
        else:
            try:
                when = await parse_future(interaction, raw_when)
            except commands.BadArgument as error:
                await interaction.response.send_message(f"\N{WHITE HEAVY CHECK MARK} {error}", ephemeral=True)
                return

        repeat = self.repeat_select.values[0] if self.repeat_select.values else "none"
        await self.on_save(interaction, ReminderDraft(text=self.text_input.value.strip(), when=when, repeat=repeat))


class ReminderPanel(BaseLayoutView):
    """Paginated list of the user's reminders with edit, bulk delete and create actions."""

    PAGE_SIZE = 5

    def __init__(self, *, cog: Reminder, author: discord.User | discord.Member) -> None:
        super().__init__(author=author)
        self.cog = cog
        self.author = author
        self.page = 0
        self.timers: list[TimerData[ReminderMetadata]] = []
        self.tz: datetime.tzinfo = datetime.UTC

    @classmethod
    async def open(cls, cog: Reminder, author: discord.User | discord.Member) -> Self:
        panel = cls(cog=cog, author=author)
        await panel.reload()
        return panel

    async def reload(self) -> None:
        self.timers = await self.cog.bot.event_scheduler.search(event_name="reminder", metadata_filter={"user_id": self.author.id})  # pyright: ignore[reportAttributeAccessIssue]
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
        pages = max(1, -(-len(self.timers) // self.PAGE_SIZE))
        self.page = min(self.page, pages - 1)
        start = self.page * self.PAGE_SIZE
        chunk = self.timers[start : start + self.PAGE_SIZE]

        children: list[discord.ui.Item[Any]] = [
            discord.ui.TextDisplay(f"## \N{ALARM CLOCK} Your reminders \N{MIDDLE DOT} {len(self.timers)}"),
            discord.ui.Separator(),
        ]
        if chunk:
            children.extend(self._section(start + index + 1, timer) for index, timer in enumerate(chunk))
        else:
            children.append(discord.ui.TextDisplay("*No active reminders. Press **New reminder** to create one.*"))
        children.append(discord.ui.Separator(visible=False))

        if chunk:
            delete_options = [
                discord.SelectOption(
                    label=clip(f"{start + index + 1}. {timer['metadata']['reminder_text']}", 100),
                    description=local_text(timer["expires_at"], self.tz),
                    value=str(timer["_id"]),
                    emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}",
                )
                for index, timer in enumerate(chunk)
            ]
            children.append(discord.ui.Separator())
            children.append(
                discord.ui.ActionRow(
                    make_select(
                        "\N{WARNING SIGN} Select reminders to delete\N{HORIZONTAL ELLIPSIS}",
                        delete_options,
                        self._delete,
                        max_values=len(delete_options),
                    )
                )
            )

        children.append(
            discord.ui.ActionRow(
                make_button(self._prev, emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", disabled=self.page <= 0),
                make_button(self._noop, label=f"{self.page + 1}/{pages}", disabled=True),
                make_button(self._next, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", disabled=self.page >= pages - 1),
                make_button(self._new, label="New reminder", emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.primary),
            )
        )
        self.add_item(discord.ui.Container(*children, accent_colour=discord.Colour.blurple()))

    def _section(self, number: int, timer: TimerData[ReminderMetadata]) -> discord.ui.Section:
        metadata = timer["metadata"]
        when = as_utc(timer["expires_at"])
        details = [clip(metadata["reminder_text"], 80)]
        if metadata.get("repeat") in REPEAT_STEPS:
            details.append(f"\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} {REPEAT_LABELS[metadata['repeat']]}")  # pyright: ignore[reportTypedDictNotRequiredAccess]
        text = f"**{number}. {discord.utils.format_dt(when, 'R')}** \N{MIDDLE DOT} {discord.utils.format_dt(when, 'f')}\n-# {' \N{MIDDLE DOT} '.join(details)}"
        return discord.ui.Section(
            discord.ui.TextDisplay(text),
            accessory=make_button(partial(self._edit, timer), emoji="\N{PENCIL}\N{VARIATION SELECTOR-16}"),
        )

    async def _noop(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

    async def _prev(self, interaction: discord.Interaction) -> None:
        self.page -= 1
        await self.redraw(interaction)

    async def _next(self, interaction: discord.Interaction) -> None:
        self.page += 1
        await self.redraw(interaction)

    async def _new(self, interaction: discord.Interaction) -> None:
        await self.cog.prompt_new_reminder(interaction, refresh=self.refresh)

    async def _delete(self, interaction: discord.Interaction, values: list[str]) -> None:
        owned = {str(timer["_id"]) for timer in self.timers}
        for value in values:
            if value in owned:
                await self.cog.bot.event_scheduler.delete_by_id(ObjectId(value))

        await self.refresh(interaction)

    async def _edit(self, timer: TimerData[ReminderMetadata], interaction: discord.Interaction) -> None:
        metadata = timer["metadata"]
        when = as_utc(timer["expires_at"])
        modal = ReminderModal(
            heading="Edit reminder",
            on_save=partial(self._apply_edit, timer),
            text=metadata["reminder_text"],
            when_text=local_text(when, self.tz),
            repeat=metadata.get("repeat", "none"),
            keep_when=when,
        )
        await interaction.response.send_modal(modal)

    async def _apply_edit(self, timer: TimerData[ReminderMetadata], interaction: discord.Interaction, draft: ReminderDraft) -> None:
        metadata = with_repeat(timer["metadata"], draft.repeat)
        metadata["reminder_text"] = draft.text
        metadata["due"] = int(draft.when.timestamp())
        updated = await self.cog.bot.event_scheduler.update(timer["_id"], expires_at=draft.when, metadata=metadata)
        if not updated:
            await interaction.response.send_message("That reminder has already fired.", ephemeral=True)
            return
        await self.refresh(interaction)


class ReminderCreatedView(BaseView):
    """Attached to the confirmation of ``remind``: change repetition or cancel."""

    def __init__(self, *, cog: Reminder, author: discord.User | discord.Member, scheduled: ScheduledReminder) -> None:
        super().__init__(author=author)
        self.cog = cog
        self.scheduled = scheduled
        self.metadata = scheduled.metadata
        self.add_item(make_select("Repeat\N{HORIZONTAL ELLIPSIS}", repeat_options(), self._set_repeat))
        self.add_item(
            make_button(self._cancel, label="Cancel reminder", emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.danger)
        )

    async def _set_repeat(self, interaction: discord.Interaction, values: list[str]) -> None:
        self.metadata = with_repeat(self.metadata, values[0])
        updated = await self.cog.bot.event_scheduler.update(self.scheduled.timer_id, expires_at=self.scheduled.when, metadata=self.metadata)
        message = (
            f"\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} {REPEAT_LABELS[values[0]]}."
            if updated
            else "That reminder has already fired."
        )
        await interaction.response.send_message(message, ephemeral=True)

    async def _cancel(self, interaction: discord.Interaction) -> None:
        await self.cog.bot.event_scheduler.delete_by_id(self.scheduled.timer_id)
        await interaction.response.edit_message(content="\N{WASTEBASKET}\N{VARIATION SELECTOR-16} Reminder cancelled.", view=None)


class ReminderView(BaseView):
    """Attached to a delivered reminder: quick snooze, custom snooze and a jump link."""

    def __init__(self, *, cog: Reminder, metadata: ReminderMetadata, author_id: int) -> None:
        super().__init__(author=discord.Object(id=author_id))  # pyright: ignore[reportArgumentType]
        self.cog = cog
        self.metadata = metadata
        options = [discord.SelectOption(label=label, value=key) for key, (label, _) in SNOOZE_OPTIONS.items()]
        self.add_item(make_select("Snooze for\N{HORIZONTAL ELLIPSIS}", options, self._snooze))
        self.add_item(make_button(self._custom_snooze, label="Custom snooze", emoji="\N{ALARM CLOCK}"))
        url = jump_url(metadata)
        if url:
            self.add_item(discord.ui.Button(url=url, label="Original message"))

    async def _snooze_until(self, interaction: discord.Interaction, when: datetime.datetime) -> None:
        await self.cog.schedule(with_repeat(self.metadata, "none"), when)
        text = clip(self.metadata["reminder_text"], 200)
        content = f"\N{SLEEPING FACE} Snoozed until {discord.utils.format_dt(when, 't')} ({discord.utils.format_dt(when, 'R')}): {text}"
        await interaction.response.edit_message(content=content, view=None)

    async def _snooze(self, interaction: discord.Interaction, values: list[str]) -> None:
        _, delta = SNOOZE_OPTIONS[values[0]]
        await self._snooze_until(interaction, discord.utils.utcnow() + delta)

    async def _custom_snooze(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(WhenModal(heading="Snooze until", on_pick=self._snooze_until))


class TimeZone(NamedTuple):
    label: str
    key: str

    @classmethod
    async def convert(cls, ctx: commands.Context[Bot], argument: str) -> TimeZone:
        assert isinstance(ctx.cog, Reminder)

        if argument in ctx.cog._timezone_aliases:
            return cls(key=ctx.cog._timezone_aliases[argument], label=argument)

        if argument in ctx.cog.valid_timezones:
            return cls(key=argument, label=argument)

        timezones = ctx.cog.find_timezones(argument)

        try:
            return await ctx.bot.disambiguate(ctx, matches=timezones, entry=lambda t: t[0], ephemeral=True)
        except ValueError:
            error_message = f"Could not find timezone for {argument!r}"
            raise commands.BadArgument(error_message) from None


class TimezoneView(BaseView):
    """One-tap timezone picker for the most common zones."""

    def __init__(self, *, author: discord.User | discord.Member) -> None:
        super().__init__(author=author)
        options = [discord.SelectOption(label=label, value=key, description=key) for label, key in POPULAR_TIMEZONES]
        self.add_item(make_select("Choose your timezone\N{HORIZONTAL ELLIPSIS}", options, self._pick))  # pyright: ignore[reportArgumentType]

    async def _pick(self, interaction: discord.Interaction[Bot], values: list[str]) -> None:
        key = values[0]
        await interaction.client.database.set_user_timezone(user_id=interaction.user.id, timezone=key)
        now = datetime.datetime.now(ZoneInfo(key))
        await interaction.response.edit_message(
            content=f"\N{WHITE HEAVY CHECK MARK} Timezone set to **{key}**. Your local time is {now:%I:%M %p, %d %b}.", view=None
        )


class CLDRDataEntry(NamedTuple):
    description: str
    aliases: list[str]
    deprecated: bool
    preferred: str | None


class Reminder(commands.Cog):
    """Reminders, snoozing, repetition and per-user timezones."""

    help_emoji = "\N{ALARM CLOCK}"

    BCP47_TIMEZONE_DATA_URL = "https://raw.githubusercontent.com/unicode-org/cldr/master/common/bcp47/timezone.xml"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._timezone_aliases: dict[str, str] = {
            "Eastern Time": "America/New_York",
            "Central Time": "America/Chicago",
            "Mountain Time": "America/Denver",
            "Pacific Time": "America/Los_Angeles",
            "EST": "America/New_York",
            "CST": "America/Chicago",
            "MST": "America/Denver",
            "PST": "America/Los_Angeles",
            "EDT": "America/New_York",
            "CDT": "America/Chicago",
            "MDT": "America/Denver",
            "PDT": "America/Los_Angeles",
            "IST": "Asia/Kolkata",
        }
        self.valid_timezones: set[str] = available_timezones()
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def cog_load(self) -> None:
        await self.parse_bcp47_timezones()

    def find_timezones(self, query: str) -> list[TimeZone]:
        if "/" in query:
            matches = process.extract(query, self.valid_timezones, scorer=fuzz.WRatio, score_cutoff=50, limit=10)
            return [TimeZone(key=match[0], label=match[0]) for match in matches]

        matches = process.extract(query, self._timezone_aliases.keys(), scorer=fuzz.WRatio, score_cutoff=50, limit=10)
        return [TimeZone(label=match[0], key=self._timezone_aliases[match[0]]) for match in matches]

    async def get_timezone(self, user_id: int, /) -> str | None:
        return await self.bot.database.get_user_timezone(user_id)

    async def get_tzinfo(self, user_id: int, /) -> datetime.tzinfo:
        """Return the user's timezone as a :class:`~zoneinfo.ZoneInfo`, or UTC when unset or invalid."""
        key = await self.get_timezone(user_id)
        if key is None:
            return datetime.UTC
        try:
            return ZoneInfo(key)
        except ZoneInfoNotFoundError, ValueError:
            return datetime.UTC

    async def parse_bcp47_timezones(self) -> None:
        async with self.bot.http_session.get(self.BCP47_TIMEZONE_DATA_URL) as resp:
            if resp.status != HTTP_OK:
                return

            parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
            tree = etree.fromstring(await resp.read(), parser=parser)

            entries: dict[str, CLDRDataEntry] = {
                node.attrib["name"]: CLDRDataEntry(
                    description=node.attrib["description"],
                    aliases=node.get("alias", "Etc/Unknown").split(" "),
                    deprecated=node.get("deprecated", "false") == "true",
                    preferred=node.get("preferred"),
                )
                for node in tree.iter("type")
                if not node.attrib["name"].startswith(("utcw", "utce", "unk")) and not node.attrib["description"].startswith("POSIX")
            }

            for entry in entries.values():
                if entry.preferred is not None:
                    preferred = entries.get(entry.preferred)
                    if preferred is not None:
                        self._timezone_aliases[entry.description] = preferred.aliases[0]
                else:
                    self._timezone_aliases[entry.description] = entry.aliases[0]

    async def schedule(self, metadata: ReminderMetadata, when: datetime.datetime) -> ScheduledReminder:
        """Persist a reminder timer, recording its intended time in the metadata."""
        full: ReminderMetadata = {**metadata, "due": int(when.timestamp())}
        result = await self.bot.event_scheduler.create_timer(event_name="reminder", expires_at=when, metadata=full)
        return ScheduledReminder(timer_id=result.inserted_id, when=when, metadata=full)

    async def prompt_new_reminder(
        self,
        interaction: discord.Interaction,
        *,
        when_text: str = "",
        refresh: Callable[[discord.Interaction], Awaitable[None]] | None = None,
    ) -> None:
        """Open the new-reminder modal. ``refresh`` re-renders the caller's message after saving."""

        async def save(modal_interaction: discord.Interaction, draft: ReminderDraft) -> None:
            message = modal_interaction.message
            metadata = ReminderMetadata(
                user_id=modal_interaction.user.id,
                guild_id=modal_interaction.guild_id or 0,
                channel_id=modal_interaction.channel_id or 0,
                message_id=message.id if message else 0,
                reminder_text=draft.text,
            )
            await self.schedule(with_repeat(metadata, draft.repeat), draft.when)
            if refresh is not None:
                await refresh(modal_interaction)
                return
            await modal_interaction.response.send_message(
                f"\N{ALARM CLOCK} Bot will remind you {discord.utils.format_dt(draft.when, 'R')}.", ephemeral=True
            )

        await interaction.response.send_modal(ReminderModal(heading="New reminder", on_save=save, when_text=when_text))

    async def deliver(self, metadata: ReminderMetadata) -> None:
        user_id = metadata["user_id"]
        content = f"<@{user_id}>, here's your reminder: {metadata['reminder_text']}"
        view = ReminderView(cog=self, metadata=metadata, author_id=user_id)

        channel = self.bot.get_channel(metadata["channel_id"]) if metadata["channel_id"] else None
        if isinstance(channel, discord.abc.Messageable) and can_send(channel):
            partial_message = channel.get_partial_message(metadata["message_id"])
            with contextlib.suppress(discord.HTTPException):
                view.message = await channel.send(
                    content,
                    view=view,
                    reference=partial_message,
                    allowed_mentions=discord.AllowedMentions(users=[discord.Object(id=user_id)]),
                )
                return

        user = await self.bot.get_or_fetch_user(user_id)
        if user is None:
            return
        with contextlib.suppress(discord.HTTPException):
            view.message = await user.send(content, view=view)

    async def schedule_next_occurrence(self, metadata: ReminderMetadata) -> None:
        """Queue the next run of a repeating reminder, keeping the user's local wall-clock time."""
        step = REPEAT_STEPS.get(metadata.get("repeat", ""))
        if step is None:
            return

        tz = await self.get_tzinfo(metadata["user_id"])
        now = discord.utils.utcnow()
        upcoming = datetime.datetime.fromtimestamp(metadata.get("due", now.timestamp()), tz)
        while upcoming <= now:
            upcoming += step
        await self.schedule(metadata, upcoming)

    @commands.Cog.listener("on_reminder_timer_complete")
    async def on_reminder_timer_complete(self, *, metadata: ReminderMetadata) -> None:
        await self.bot.wait_until_ready()
        await self.schedule_next_occurrence(metadata)
        await self.deliver(metadata)

    @commands.group(name="timezone", aliases=["tz"], invoke_without_command=True)
    async def timezone(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show your timezone, or pick one from a menu.

        Your timezone is used to read times you type, such as "tomorrow 9am".
        """
        key = await self.get_timezone(ctx.author.id)
        current = f"Your timezone is **{key}**." if key else "You haven't set a timezone yet, so times are read as UTC."
        return await ctx.reply(f"{current}\nPick a new one below, or use `timezone set <city or IANA name>`.", view=TimezoneView(author=ctx.author))

    @timezone.command(name="set", aliases=["change", "update"])
    async def set_timezone(
        self,
        ctx: commands.Context[Bot],
        *,
        timezone: TimeZone | None = commands.parameter(default=None, description="The timezone to set. Leave empty to pick from a menu."),  # noqa: B008
    ) -> discord.Message:
        """Set your timezone.

        Run without arguments to choose from a menu of common timezones.
        """
        if timezone is None:
            return await ctx.reply("Choose your timezone:", view=TimezoneView(author=ctx.author))

        await self.bot.database.set_user_timezone(user_id=ctx.author.id, timezone=timezone.key)
        return await ctx.reply(f"Your timezone has been set to {timezone.label} (IANA: {timezone.key}).")

    @timezone.command(name="info")
    async def timezone_info(
        self,
        ctx: commands.Context[Bot],
        *,
        timezone: TimeZone = commands.parameter(description="The timezone to get info about."),  # noqa: B008
    ) -> discord.Message:
        """Retrieve the current time and UTC offset of a timezone."""
        now = datetime.datetime.now(ZoneInfo(timezone.key))
        offset = now.utcoffset() or datetime.timedelta()
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        hours, minutes = divmod(abs(total_minutes), 60)
        return await ctx.reply(
            f"Timezone: {timezone.label} (IANA: {timezone.key})\nCurrent time: {now:%Y-%m-%d %I:%M %p}\nUTC offset: {sign}{hours:02d}:{minutes:02d}"
        )

    @commands.command(name="remind", aliases=["reminder", "remindme", "remindin"])
    async def remind(
        self,
        ctx: commands.Context[Bot],
        *,
        when: Annotated[FriendlyTimeResult, UserFriendlyTime(commands.clean_content, default="...")] = commands.parameter(  # noqa: B008
            description="The time to set the reminder for, in a human-readable format."
        ),
    ) -> None:
        """Remind you of something after a certain amount of time.

        The input can be a direct date (e.g. YYYY-MM-DD) or a human readable
        offset. Examples:

        - "2d unmute someone"
        - "in 3 days do the thing"
        - "next thursday at 3pm do something funny"

        Times follow your timezone (see the "timezone" command). After
        setting a reminder you can make it repeat or cancel it with the menu
        below the confirmation. Use the "reminders" command to manage all of them.
        """
        metadata = ReminderMetadata(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else 0,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            reminder_text=when.arg,
        )
        scheduled = await self.schedule(metadata, when.dt)
        view = ReminderCreatedView(cog=self, author=ctx.author, scheduled=scheduled)
        await ctx.reply(
            f"\N{ALARM CLOCK} Bot will remind you {discord.utils.format_dt(when.dt, 'R')} ({discord.utils.format_dt(when.dt, 'F')}).",
            view=view,
        )

    @commands.command(name="reminders")
    async def reminders(self, ctx: commands.Context[Bot]) -> None:
        """Manage your active reminders.

        Edit, delete several at once, or create new reminders with repeats.
        """
        panel = await ReminderPanel.open(self, ctx.author)
        await ctx.reply(view=panel)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Reminder(bot))
