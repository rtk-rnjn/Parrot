from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord
from bson import ObjectId
from discord.ext import commands, tasks

from core.utils.database_manager.models import PresenceStatus, StatsEvent, StatsKind, VoiceState

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.stats")
INTERVAL_SECONDS = 30 * 60


class Stats(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._records: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._presence: dict[tuple[int, int], tuple[PresenceStatus, datetime]] = {}
        self._voice: dict[tuple[int, int], tuple[int, VoiceState, datetime]] = {}
        _log.info("Cog loaded: %s", type(self).__name__)

    async def cog_load(self) -> None:
        await self.bot.database.stats_collection.create_index(
            [
                ("interval_start", 1),
                ("guild_id", 1),
                ("user_id", 1),
                ("kind", 1),
                ("event", 1),
                ("channel_id", 1),
                ("status", 1),
                ("voice_state", 1),
            ],
            unique=True,
            name="stats_bucket_identity",
        )
        await self.bot.database.stats_collection.create_index(
            "interval_start",
            expireAfterSeconds=30 * 24 * 60 * 60,
            name="stats_30_day_retention",
        )
        self.flush_stats.start()

    async def cog_unload(self) -> None:
        self.flush_stats.cancel()
        await self._flush()

    @staticmethod
    def _interval_start(value: datetime) -> datetime:
        value = value.astimezone(UTC)
        timestamp = int(value.timestamp()) - int(value.timestamp()) % INTERVAL_SECONDS
        return datetime.fromtimestamp(timestamp, tz=UTC)

    def _increment(  # noqa: PLR0913
        self,
        *,
        interval_start: datetime,
        guild_id: int,
        user_id: int,
        kind: StatsKind,
        values: Mapping[str, int | float],
        event: StatsEvent | None = None,
        channel_id: int | None = None,
        status: PresenceStatus | None = None,
        voice_state: VoiceState | None = None,
    ) -> None:
        dimensions = (interval_start, guild_id, user_id, kind, event, channel_id, status, voice_state)
        record = self._records.setdefault(
            dimensions,
            {
                "_id": ObjectId(),
                "interval_start": interval_start,
                "guild_id": guild_id,
                "user_id": user_id,
                "kind": kind,
                "event": event,
                "channel_id": channel_id,
                "status": status,
                "voice_state": voice_state,
                "values": defaultdict(float),
            },
        )
        for name, value in values.items():
            record["values"][name] += value

    def _add_duration(  # noqa: PLR0913
        self,
        *,
        start: datetime,
        end: datetime,
        guild_id: int,
        user_id: int,
        kind: StatsKind,
        values: Mapping[str, int | float],
        event: StatsEvent | None = None,
        channel_id: int | None = None,
        status: PresenceStatus | None = None,
        voice_state: VoiceState | None = None,
    ) -> None:
        cursor = start
        while cursor < end:
            interval_start = self._interval_start(cursor)
            interval_end = interval_start + timedelta(seconds=INTERVAL_SECONDS)
            segment_end = min(end, interval_end)
            duration = (segment_end - cursor).total_seconds()
            self._increment(
                interval_start=interval_start,
                guild_id=guild_id,
                user_id=user_id,
                kind=kind,
                values={name: value * duration for name, value in values.items()},
                event=event,
                channel_id=channel_id,
                status=status,
                voice_state=voice_state,
            )
            cursor = segment_end

    def _record_event(
        self,
        *,
        guild_id: int,
        event: StatsEvent,
        user_id: int = 0,
        channel_id: int | None = None,
        values: Mapping[str, int | float] | None = None,
    ) -> None:
        self._increment(
            interval_start=self._interval_start(discord.utils.utcnow()),
            guild_id=guild_id,
            user_id=user_id,
            kind=StatsKind.EVENT,
            event=event,
            channel_id=channel_id,
            values=values or {"events": 1},
        )

    def _accrue_presence(self, key: tuple[int, int], end: datetime) -> None:
        current = self._presence.get(key)
        if current is None:
            return
        status, started_at = current
        self._add_duration(
            start=started_at,
            end=end,
            guild_id=key[0],
            user_id=key[1],
            kind=StatsKind.PRESENCE,
            values={"seconds": 1},
            status=status,
        )
        self._presence[key] = (status, end)

    def _accrue_voice(self, key: tuple[int, int], end: datetime) -> None:
        current = self._voice.get(key)
        if current is None:
            return
        channel_id, voice_state, started_at = current
        self._add_duration(
            start=started_at,
            end=end,
            guild_id=key[0],
            user_id=key[1],
            kind=StatsKind.VOICE,
            values={"seconds": 1},
            channel_id=channel_id,
            voice_state=voice_state,
        )
        self._voice[key] = (channel_id, voice_state, end)

    async def _flush(self) -> None:
        now = discord.utils.utcnow()
        for key in tuple(self._presence):
            self._accrue_presence(key, now)
        for key in tuple(self._voice):
            self._accrue_voice(key, now)

        if not self._records:
            return

        records = list(self._records.values())
        await self.bot.database.flush_stats(records)
        self._records.clear()
        _log.debug("Flushed %s stats records", len(records))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        values = {
            "messages": 1,
            "characters": len(message.content),
            "attachments": len(message.attachments),
            "embeds": len(message.embeds),
            "mentions": len(message.mentions),
            "reactions": len(message.reactions),
        }
        if message.reference is not None:
            values["replies"] = 1
        self._increment(
            interval_start=self._interval_start(discord.utils.utcnow()),
            guild_id=message.guild.id,
            user_id=message.author.id,
            kind=StatsKind.MESSAGE,
            values=values,
            channel_id=message.channel.id,
        )

    @commands.Cog.listener()
    async def on_command_completion(self, context: commands.Context[Parrot]) -> None:
        if context.guild is None or context.author.bot:
            return
        self._increment(
            interval_start=self._interval_start(discord.utils.utcnow()),
            guild_id=context.guild.id,
            user_id=context.author.id,
            kind=StatsKind.COMMAND,
            values={"commands": 1},
            channel_id=context.channel.id,
        )

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        key = (after.guild.id, after.id)
        now = discord.utils.utcnow()
        self._accrue_presence(key, now)
        status = PresenceStatus(after.status)
        if before.status != after.status:
            self._increment(
                interval_start=self._interval_start(now),
                guild_id=after.guild.id,
                user_id=after.id,
                kind=StatsKind.PRESENCE_TRANSITION,
                values={"transitions": 1},
                status=status,
            )
        before_activities = {activity.type for activity in before.activities}
        after_activities = {activity.type for activity in after.activities}
        if before_activities != after_activities:
            self._record_event(
                guild_id=after.guild.id,
                user_id=after.id,
                event=StatsEvent.PRESENCE_ACTIVITY,
                values={"updates": 1, "activities": len(after_activities)},
            )
        self._presence[key] = (status, now)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        key = (member.guild.id, member.id)
        now = discord.utils.utcnow()
        self._accrue_voice(key, now)
        if after.channel is None:
            self._voice.pop(key, None)
        else:
            state_parts = []
            if after.self_mute or after.mute:
                state_parts.append("muted")
            if after.self_deaf or after.deaf:
                state_parts.append("deafened")
            if after.self_stream:
                state_parts.append("streaming")
            if after.self_video:
                state_parts.append("video")
            self._voice[key] = (after.channel.id, VoiceState("|".join(state_parts) or VoiceState.NORMAL), now)

        if before.channel != after.channel:
            self._increment(
                interval_start=self._interval_start(now),
                guild_id=member.guild.id,
                user_id=member.id,
                kind=StatsKind.VOICE_TRANSITION,
                values={"transitions": 1},
                channel_id=after.channel.id if after.channel else before.channel.id if before.channel else None,
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        self._record_event(guild_id=member.guild.id, user_id=member.id, event=StatsEvent.MEMBER_JOIN)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        self._record_event(guild_id=member.guild.id, user_id=member.id, event=StatsEvent.MEMBER_LEAVE)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        changed = {
            "roles": before.roles != after.roles,
            "nickname": before.nick != after.nick,
            "timeout": before.timed_out_until != after.timed_out_until,
            "avatar": before.display_avatar != after.display_avatar,
        }
        if any(changed.values()):
            self._record_event(
                guild_id=after.guild.id,
                user_id=after.id,
                event=StatsEvent.MEMBER_UPDATE,
                values={"updates": 1, **{name: int(value) for name, value in changed.items()}},
            )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is not None and not after.author.bot:
            self._record_event(guild_id=after.guild.id, user_id=after.author.id, event=StatsEvent.MESSAGE_EDIT, channel_id=after.channel.id)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is not None and not message.author.bot:
            self._record_event(guild_id=message.guild.id, user_id=message.author.id, event=StatsEvent.MESSAGE_DELETE, channel_id=message.channel.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is not None and payload.user_id != self.bot.user.id:
            self._record_event(guild_id=payload.guild_id, user_id=payload.user_id, event=StatsEvent.REACTION_ADD, channel_id=payload.channel_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is not None and payload.user_id != self.bot.user.id:
            self._record_event(guild_id=payload.guild_id, user_id=payload.user_id, event=StatsEvent.REACTION_REMOVE, channel_id=payload.channel_id)

    @commands.Cog.listener()
    async def on_typing(self, channel: discord.abc.Messageable, user: discord.User, when: datetime) -> None:
        guild = getattr(channel, "guild", None)
        if guild is not None and not user.bot:
            channel_id = getattr(channel, "id", None)
            self._record_event(guild_id=guild.id, user_id=user.id, event=StatsEvent.TYPING_START, channel_id=channel_id)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.guild is not None and interaction.user is not None and not interaction.user.bot:
            channel_id = interaction.channel.id if interaction.channel is not None else None
            self._record_event(guild_id=interaction.guild.id, user_id=interaction.user.id, event=StatsEvent.INTERACTION, channel_id=channel_id)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        self._record_event(guild_id=thread.guild.id, event=StatsEvent.THREAD_CREATE, channel_id=thread.id)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        self._record_event(guild_id=thread.guild.id, event=StatsEvent.THREAD_DELETE, channel_id=thread.id)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        self._record_event(guild_id=channel.guild.id, event=StatsEvent.CHANNEL_CREATE, channel_id=channel.id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        self._record_event(guild_id=channel.guild.id, event=StatsEvent.CHANNEL_DELETE, channel_id=channel.id)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        self._record_event(guild_id=role.guild.id, event=StatsEvent.ROLE_CREATE)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        self._record_event(guild_id=role.guild.id, event=StatsEvent.ROLE_DELETE)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        self._record_event(guild_id=guild.id, user_id=user.id, event=StatsEvent.BAN_ADD)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        self._record_event(guild_id=guild.id, user_id=user.id, event=StatsEvent.BAN_REMOVE)

    @tasks.loop(seconds=INTERVAL_SECONDS)
    async def flush_stats(self) -> None:
        try:
            await self._flush()
        except Exception:
            _log.exception("Failed to flush statistics")

    @flush_stats.before_loop
    async def before_flush_stats(self) -> None:
        await self.bot.wait_until_ready()

    @commands.command(name="stats_flush", aliases=["flush_stats"])
    @commands.is_owner()
    async def flush_stats_command(self, ctx: commands.Context[Parrot]) -> None:
        """Flush the in-memory statistics to the database."""
        await self._flush()
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Stats(bot))
