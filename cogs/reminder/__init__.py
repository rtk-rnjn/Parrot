from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Annotated, NamedTuple, TypedDict, cast

import dateutil
import discord
from dateutil.zoneinfo import get_zonefile_instance
from discord.ext import commands
from lxml import etree
from rapidfuzz import fuzz, process

from core.utils import FriendlyTimeResult, FutureTime, UserFriendlyTime
from core.utils import TimerData as Timer

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.reminder")


class ReminderMetadata(TypedDict):
    user_id: int
    guild_id: int
    channel_id: int
    message_id: int
    reminder_text: str


class ReminderLayout(discord.ui.LayoutView):
    def __init__(self, *, reminders: list[Timer]) -> None:
        super().__init__()
        self.reminders = reminders

        self.number_of_reminders_to_display = min(len(reminders), 3)
        self.current_page = 0
        self.offset = 0
        self.total_pages = (len(reminders) + self.number_of_reminders_to_display - 1) // self.number_of_reminders_to_display

        reminder_sections = [
            self.reminder_section(i + 1, reminder)
            for i, reminder in enumerate(reminders[self.offset : self.offset + self.number_of_reminders_to_display])
        ]
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(f"## Your active reminders [`{len(reminders)}`]"),
            discord.ui.Separator(),
            *reminder_sections,
        )

        self.add_item(self.container)
        # self.add_item(self.action_row)

    def reminder_section(self, index: int, reminder: Timer) -> discord.ui.Section:
        metadata: ReminderMetadata = cast(ReminderMetadata, reminder["metadata"])
        jump_url = f"https://discord.com/channels/{metadata['guild_id']}/{metadata['channel_id']}/{metadata['message_id']}"

        relative_time_fmt = discord.utils.format_dt(reminder["expires_at"], "R")
        parsed_text = "Content: " + metadata["reminder_text"][:28] + "..." if len(metadata["reminder_text"]) > 28 else metadata["reminder_text"]

        return discord.ui.Section(
            discord.ui.TextDisplay(f"[{index}. **{relative_time_fmt}**]({jump_url})\n-# {parsed_text}"),
            accessory=discord.ui.Button(
                emoji="\N{WASTEBASKET}",
                style=discord.ButtonStyle.red,
            ),
        )


class SnoozeModal(discord.ui.Modal, title="Snooze"):
    duration = discord.ui.TextInput(label="Duration", placeholder="10 minutes", default="10 minutes", min_length=2)

    def __init__(self, parent: ReminderView, cog: Reminder, metadata: ReminderMetadata) -> None:
        super().__init__()
        self.parent: ReminderView = parent
        self.metadata: ReminderMetadata = metadata
        self.cog: Reminder = cog

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        try:
            when = FutureTime(str(self.duration)).dt
        except Exception:
            await interaction.response.send_message('Duration could not be parsed, sorry. Try something like "5 minutes" or "1 hour"', ephemeral=True)
            return

        self.parent.snooze.disabled = True
        await interaction.response.edit_message(view=self.parent)

        await interaction.client.event_scheduler.create_timer(
            event_name="reminder",
            expires_at=when,
            metadata=self.metadata,
        )
        author_id = self.metadata["user_id"]
        message = self.metadata["reminder_text"]

        source = discord.utils.snowflake_time(self.metadata["message_id"])
        relative_time_fmt = discord.utils.format_dt(source, "R")

        await interaction.followup.send(f"<@{author_id}>, you will be reminded again - {relative_time_fmt}: {message}", ephemeral=True)


class SnoozeButton(discord.ui.Button["ReminderView"]):
    def __init__(self, cog: Reminder, metadata: ReminderMetadata) -> None:
        super().__init__(label="Snooze", style=discord.ButtonStyle.blurple)
        self.metadata: ReminderMetadata = metadata
        self.cog: Reminder = cog

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await interaction.response.send_modal(SnoozeModal(self.view, self.cog, self.metadata))


class ReminderView(discord.ui.View):
    message: discord.Message

    def __init__(self, *, url: str, metadata: ReminderMetadata, cog: Reminder, author_id: int) -> None:
        super().__init__(timeout=300)
        self.author_id: int = author_id
        self.snooze = SnoozeButton(cog, metadata)
        self.add_item(discord.ui.Button(url=url, label="Go to original message"))
        self.add_item(self.snooze)

    async def interaction_check(self, interaction: discord.Interaction[Parrot]) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot interact with this view.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.snooze.disabled = True
        await self.message.edit(view=self)


class TimeZone(NamedTuple):
    label: str
    key: str

    @classmethod
    async def convert(cls, ctx: commands.Context[Parrot], argument: str) -> TimeZone:
        assert isinstance(ctx.cog, Reminder)

        # Prioritise aliases because they handle short codes slightly better
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


class CLDRDataEntry(NamedTuple):
    description: str
    aliases: list[str]
    deprecated: bool
    preferred: str | None


class Reminder(commands.Cog):
    DEFAULT_POPULAR_TIMEZONE_IDS = (
        # America
        "usnyc",  # America/New_York
        "uslax",  # America/Los_Angeles
        "uschi",  # America/Chicago
        "usden",  # America/Denver
        # India
        "inccu",  # Asia/Kolkata
        # Europe
        "trist",  # Europe/Istanbul
        "rumow",  # Europe/Moscow
        "gblon",  # Europe/London
        "frpar",  # Europe/Paris
        "esmad",  # Europe/Madrid
        "deber",  # Europe/Berlin
        "grath",  # Europe/Athens
        "uaiev",  # Europe/Kyev
        "itrom",  # Europe/Rome
        "nlams",  # Europe/Amsterdam
        "plwaw",  # Europe/Warsaw
        # Canada
        "cator",  # America/Toronto
        # Australia
        "aubne",  # Australia/Brisbane
        "ausyd",  # Australia/Sydney
        # Brazil
        "brsao",  # America/Sao_Paulo
        # Japan
        "jptyo",  # Asia/Tokyo
        # China
        "cnsha",  # Asia/Shanghai
    )

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._timezone_aliases: dict[str, str] = {
            "Eastern Time": "America/New_York",
            "Central Time": "America/Chicago",
            "Mountain Time": "America/Denver",
            "Pacific Time": "America/Los_Angeles",
            # (Unfortunately) special case American timezone abbreviations
            "EST": "America/New_York",
            "CST": "America/Chicago",
            "MST": "America/Denver",
            "PST": "America/Los_Angeles",
            "EDT": "America/New_York",
            "CDT": "America/Chicago",
            "MDT": "America/Denver",
            "PDT": "America/Los_Angeles",
        }

        self.valid_timezones: set[str] = set(get_zonefile_instance().zones)
        _log.info("Cog loaded: %s", self.__class__.__name__)

    async def cog_load(self) -> None:
        await self.parse_bcp47_timezones()

    def find_timezones(self, query: str) -> list[TimeZone]:
        # A bit hacky, but if '/' is in the query then it's looking for a raw identifier;
        # otherwise it's looking for a CLDR alias.
        if "/" in query:
            matches = process.extract(
                query,
                self.valid_timezones,
                scorer=fuzz.WRatio,
                score_cutoff=50,
                limit=10,
            )
            return [TimeZone(key=match[0], label=match[0]) for match in matches]

        matches = process.extract(
            query,
            self._timezone_aliases.keys(),
            scorer=fuzz.WRatio,
            score_cutoff=50,
            limit=10,
        )
        return [TimeZone(label=match[0], key=self._timezone_aliases[match[0]]) for match in matches]

    async def get_timezone(self, user_id: int, /) -> str | None:
        return await self.bot.database.get_user_timezone(user_id)

    async def get_tzinfo(self, user_id: int, /) -> datetime.tzinfo:
        tz = await self.get_timezone(user_id)
        if tz is None:
            return datetime.UTC
        return dateutil.tz.gettz(tz) or datetime.UTC

    async def parse_bcp47_timezones(self) -> None:
        async with self.bot.http_session.get(
            "https://raw.githubusercontent.com/unicode-org/cldr/main/common/bcp47/timezone.xml",
        ) as resp:
            if resp.status != 200:
                return

            parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
            tree = etree.fromstring(await resp.read(), parser=parser)

            # Build a temporary dictionary to resolve "preferred" mappings
            entries: dict[str, CLDRDataEntry] = {
                node.attrib["name"]: CLDRDataEntry(
                    description=node.attrib["description"],
                    aliases=node.get("alias", "Etc/Unknown").split(" "),
                    deprecated=node.get("deprecated", "false") == "true",
                    preferred=node.get("preferred"),
                )
                for node in tree.iter("type")
                # Filter the Etc/ entries (except UTC)
                if not node.attrib["name"].startswith(("utcw", "utce", "unk")) and not node.attrib["description"].startswith("POSIX")
            }

            for entry in entries.values():
                # These use the first entry in the alias list as the "canonical" name to use when mapping the
                # timezone to the IANA database.
                # The CLDR database is not particularly correct when it comes to these, but neither is the IANA database.
                # It turns out the notion of a "canonical" name is a bit of a mess. This works fine for users where
                # this is only used for display purposes, but it's not ideal.
                if entry.preferred is not None:
                    preferred = entries.get(entry.preferred)
                    if preferred is not None:
                        self._timezone_aliases[entry.description] = preferred.aliases[0]
                else:
                    self._timezone_aliases[entry.description] = entry.aliases[0]

    @commands.group(name="timezone", aliases=["tz"], invoke_without_command=True)
    async def timezone(self, ctx: commands.Context[Parrot]) -> discord.Message:
        """Get or set your timezone for use with the reminder command.

        This is used to convert times to your local timezone when
        using the reminder command and other miscellaneous commands.
        """
        return await ctx.send_help(ctx.command)

    @timezone.command(name="set", aliases=["change", "update"])
    async def set_timezone(self, ctx: commands.Context[Parrot], *, timezone: TimeZone) -> discord.Message:
        """Set your timezone for use with the reminder command.

        This is used to convert times to your local timezone when
        using the reminder command and other miscellaneous commands.
        """

        label = timezone.label
        key = timezone.key

        await self.bot.database.set_user_timezone(user_id=ctx.author.id, timezone=key)
        return await ctx.reply(f"Your timezone has been set to {label} (IANA: {key}).")

    @timezone.command(name="info")
    async def timezone_info(self, ctx: commands.Context[Parrot], *, tz: TimeZone):
        """Retrieves info about a timezone."""

        key = tz.key
        label = tz.label

        dt = discord.utils.utcnow().astimezone(dateutil.tz.gettz(tz.key))
        time = dt.strftime("%Y-%m-%d %I:%M %p")

        offset = dt.utcoffset()

        if offset is not None:
            hours, remainder = divmod(offset.total_seconds(), 3600)
            minutes = remainder // 60
            offset_str = f"{int(hours):+03d}:{int(minutes):02d}"
        else:
            offset_str = "Unknown"

        return await ctx.reply(f"Timezone: {label} (IANA: {key})\nCurrent time: {time}\nUTC offset: {offset_str}")

    async def send_dm(self, *, user: discord.User, content: str, view: ReminderView) -> discord.Message | None:
        try:
            return await user.send(content, view=view)
        except discord.Forbidden:
            pass

    @commands.Cog.listener("on_reminder_timer_complete")
    async def on_reminder_timer_complete(self, *, metadata: ReminderMetadata) -> None:
        await self.bot.wait_until_ready()

        guild_id = metadata["guild_id"]
        channel_id = metadata["channel_id"]
        message_id = metadata["message_id"]
        user_id = metadata["user_id"]

        guild = self.bot.get_guild(guild_id)

        if guild is not None and not guild.chunked:
            await guild.chunk()

        channel = guild.get_channel(channel_id) if guild is not None else None

        message_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        response = f"<@{user_id}>, this is your reminder: {metadata['reminder_text']}"

        view = ReminderView(
            url=message_url,
            metadata=metadata,
            cog=self,
            author_id=user_id,
        )

        # Try sending in the original channel first.
        if guild is not None and isinstance(channel, discord.abc.Messageable):
            me = guild.me

            permissions = channel.permissions_for(me)

            if permissions.send_messages:
                message = await channel.send(response, view=view, reference=discord.PartialMessage(channel=channel, id=message_id))
                if message is not None:
                    view.message = message
                return

        # Guild/channel unavailable, bot member unavailable, or
        # bot does not have permission to send in the channel.
        user = await self.bot.get_or_fetch_user(user_id)

        if user is not None:
            message = await self.send_dm(user=user, content=response, view=view)
            if message is not None:
                view.message = message

    @commands.group(name="remind", aliases=["reminder", "remindme", "remindin"], invoke_without_command=True)
    async def remind(
        self,
        ctx: commands.Context[Parrot],
        *,
        when: Annotated[FriendlyTimeResult, UserFriendlyTime(commands.clean_content, default="...")],
    ):
        """Reminds you of something after a certain amount of time.

        The input can be any direct date (e.g. YYYY-MM-DD) or a human
        readable offset. Examples:

        - "next thursday at 3pm do something funny"
        - "do the dishes tomorrow"
        - "in 3 days do the thing"
        - "2d unmute someone"

        Times are in UTC unless a timezone is specified
        using the "timezone set" command.
        """

        if TYPE_CHECKING:
            assert ctx.guild is not None

        # Store the reminder in the database
        metadata = ReminderMetadata(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            reminder_text=when.arg,
        )

        await self.bot.event_scheduler.create_timer(
            event_name="reminder",
            expires_at=when.dt,
            metadata=metadata,
        )

        return await ctx.reply(
            f"You will be reminded in {discord.utils.format_dt(when.dt, 'R')} ({discord.utils.format_dt(when.dt, 'F')})",
        )

    @commands.command(name="reminders")
    async def reminders(self, ctx: commands.Context[Parrot]) -> discord.Message:
        """Lists your active reminders.

        This command will show you a list of all your active reminders, along with the time remaining until each reminder is triggered.
        """

        reminders = await self.bot.event_scheduler.search_timers(event_name="reminder", metadata_filter={"user_id": ctx.author.id})

        if not reminders:
            return await ctx.reply("You have no active reminders.")

        return await ctx.reply(view=ReminderLayout(reminders=reminders))


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Reminder(bot))
