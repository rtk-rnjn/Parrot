from __future__ import annotations

import asyncio
import enum
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from core.utils.formats import format_duration, human_timedelta, truncate

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from core import Bot
    from core.utils.database.guild.events import EVENT_NAME

_log = logging.getLogger(__name__)

AUDIT_DELAY = 1.2
AUDIT_WINDOW = 20.0
NEW_ACCOUNT = timedelta(days=7)
NO_MENTIONS = discord.AllowedMentions.none()
_MISSING: Any = object()

GREEN = discord.Colour.green()
RED = discord.Colour.red()
ORANGE = discord.Colour.orange()
BLUE = discord.Colour.blurple()

type Formatter = Callable[[Any], str]


def is_bot_or_webhook(target: Any) -> bool:
    if target is None:
        return False
    if getattr(target, "bot", False) or getattr(target, "system", False):
        return True
    if getattr(target, "webhook_id", None) is not None:
        return True
    author = getattr(target, "author", None)
    return bool(author is not None and (getattr(author, "bot", False) or getattr(author, "system", False)))


def fmt(value: Any) -> str:  # noqa: PLR0911
    if value is None:
        return "*None*"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, enum.Enum):
        return str(value.name).replace("_", " ").title()
    if isinstance(value, discord.Colour):
        return str(value)
    if isinstance(value, discord.Asset):
        return f"[link]({value.url})"
    if isinstance(value, timedelta):
        return format_duration(value.total_seconds())
    if hasattr(value, "mention"):
        return value.mention
    if isinstance(value, list | tuple | set | frozenset):
        return ", ".join(fmt(item) for item in value) or "*None*"
    return str(value) if str(value) else "*Empty*"


def seconds(value: int | None) -> str:
    return format_duration(value) if value else "Off"


def minutes(value: int | None) -> str:
    return format_duration(value * 60) if value else "*None*"


def kbps(value: int | None) -> str:
    return f"{value // 1000} kbps" if value else "*None*"


def limit(value: int | None) -> str:
    return str(value) if value else "Unlimited"


def tag_names(tags: Iterable[discord.ForumTag] | None) -> str:
    return ", ".join(f"{tag.name}{' (mod only)' if tag.moderated else ''}" for tag in tags or ()) or "*None*"


def flag_names(flags: Iterable[tuple[str, bool]]) -> list[str]:
    return [name.replace("_", " ").title() for name, enabled in flags if enabled]


def clip(text: str, size: int = 1024) -> str:
    return truncate(text, size)


def stamp(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    return f"{discord.utils.format_dt(moment, 'F')} ({discord.utils.format_dt(moment, 'R')})"


def ident(obj: Any) -> str:
    return f"{getattr(obj, 'mention', obj)} (`{obj.id}`)"


def mention(target: Any) -> str:
    return getattr(target, "mention", f"`{target.id}`")


def add(embed: discord.Embed, name: str, value: Any, *, inline: bool = False) -> None:
    if value in (None, "", []) or len(embed.fields) >= 25:
        return
    embed.add_field(name=name, value=clip(str(value)), inline=inline)


def fit(embed: discord.Embed) -> discord.Embed:
    while len(embed) > 5900 and embed.fields:
        embed.remove_field(len(embed.fields) - 1)
    return embed


def base(
    title: str,
    colour: discord.Colour,
    *,
    description: str | None = None,
    author: discord.abc.User | None = None,
    footer: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(title=title, colour=colour, description=description, timestamp=discord.utils.utcnow())
    if author is not None:
        embed.set_author(name=str(author), icon_url=author.display_avatar.url)
        if footer is None:
            footer = f"User ID: {author.id}"
    if footer:
        embed.set_footer(text=footer)
    return embed


def text_file(name: str, content: str) -> discord.File:
    return discord.File(BytesIO(content.encode()), filename=name)


def diff(before: Any, after: Any, spec: Iterable[tuple[str, str, Formatter]]) -> list[tuple[str, str, str]]:
    changes: list[tuple[str, str, str]] = []
    for label, attribute, formatter in spec:
        old, new = getattr(before, attribute, _MISSING), getattr(after, attribute, _MISSING)
        if old is _MISSING and new is _MISSING:
            continue
        old_text, new_text = formatter(None if old is _MISSING else old), formatter(None if new is _MISSING else new)
        if old_text != new_text:
            changes.append((label, old_text, new_text))
    return changes


def add_changes(embed: discord.Embed, changes: Iterable[tuple[str, str, str]]) -> None:
    for label, old, new in changes:
        add(embed, label, f"**Before:** {clip(old, 450)}\n**After:** {clip(new, 450)}")


def permission_names(permissions: discord.Permissions) -> list[str]:
    return flag_names(permissions)


def permission_delta(before: discord.Permissions, after: discord.Permissions) -> tuple[list[str], list[str]]:
    old, new = dict(before), dict(after)
    granted = [name.replace("_", " ").title() for name, on in new.items() if on and not old.get(name)]
    revoked = [name.replace("_", " ").title() for name, on in old.items() if on and not new.get(name)]
    return granted, revoked


def overwrite_state(value: bool | None) -> str:
    return "\N{WHITE HEAVY CHECK MARK}" if value else "\N{CROSS MARK}" if value is False else "\N{HEAVY MINUS SIGN}"


def overwrite_summary(overwrite: discord.PermissionOverwrite) -> str:
    allow, deny = overwrite.pair()
    parts = []
    if allow.value:
        parts.append(f"\N{WHITE HEAVY CHECK MARK} {', '.join(permission_names(allow))}")
    if deny.value:
        parts.append(f"\N{CROSS MARK} {', '.join(permission_names(deny))}")
    return " \N{MIDDLE DOT} ".join(parts) or "no explicit permissions"


def overwrite_lines(channel: discord.abc.GuildChannel) -> list[str]:
    return [
        clip(f"{mention(target)}: {overwrite_summary(overwrite)}", 300)
        for target, overwrite in channel.overwrites.items()
        if not is_bot_or_webhook(target) and not getattr(target, "managed", False)
    ][:10]


def overwrite_changes(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> list[str]:
    old = {t: ov for t, ov in before.overwrites.items() if not is_bot_or_webhook(t) and not getattr(t, "managed", False)}
    new = {t: ov for t, ov in after.overwrites.items() if not is_bot_or_webhook(t) and not getattr(t, "managed", False)}
    lines = [f"\N{HEAVY PLUS SIGN} {mention(t)}: {overwrite_summary(new[t])}" for t in new.keys() - old.keys()]
    lines += [f"\N{HEAVY MINUS SIGN} {mention(t)} removed" for t in old.keys() - new.keys()]
    for target in old.keys() & new.keys():
        delta = [
            f"{name.replace('_', ' ').title()}: {overwrite_state(o)} \N{RIGHTWARDS ARROW} {overwrite_state(n)}"
            for (name, o), (_, n) in zip(old[target], new[target], strict=True)
            if o != n
        ]
        if delta:
            lines.append(f"\N{PENCIL} {mention(target)}: {'; '.join(delta)}")
    return [clip(line, 400) for line in lines][:10]


CHANNEL_SPEC: tuple[tuple[str, str, Formatter], ...] = (
    ("Name", "name", fmt),
    ("Type", "type", fmt),
    ("Topic", "topic", fmt),
    ("NSFW", "nsfw", fmt),
    ("Slowmode", "slowmode_delay", seconds),
    ("Bitrate", "bitrate", kbps),
    ("User limit", "user_limit", limit),
    ("Category", "category", fmt),
    ("Voice region", "rtc_region", fmt),
    ("Video quality", "video_quality_mode", fmt),
    ("Default auto-archive", "default_auto_archive_duration", minutes),
    ("Default thread slowmode", "default_thread_slowmode_delay", seconds),
    ("Forum layout", "default_layout", fmt),
    ("Forum sort order", "default_sort_order", fmt),
    ("Default reaction", "default_reaction_emoji", fmt),
    ("Forum tags", "available_tags", tag_names),
    ("Synced with category", "permissions_synced", fmt),
)

THREAD_SPEC: tuple[tuple[str, str, Formatter], ...] = (
    ("Name", "name", fmt),
    ("Archived", "archived", fmt),
    ("Locked", "locked", fmt),
    ("Invitable", "invitable", fmt),
    ("Slowmode", "slowmode_delay", seconds),
    ("Auto-archive", "auto_archive_duration", minutes),
    ("Tags", "applied_tags", lambda tags: ", ".join(t.name for t in tags or ()) or "*None*"),
    ("Pinned", "flags", lambda flags: fmt(bool(flags and flags.pinned))),
)

GUILD_SPEC: tuple[tuple[str, str, Formatter], ...] = (
    ("Name", "name", fmt),
    ("Description", "description", fmt),
    ("Icon", "icon", fmt),
    ("Banner", "banner", fmt),
    ("Invite splash", "splash", fmt),
    ("Discovery splash", "discovery_splash", fmt),
    ("Owner", "owner_id", lambda v: f"<@{v}>" if v else "*None*"),
    ("AFK channel", "afk_channel", fmt),
    ("AFK timeout", "afk_timeout", seconds),
    ("System channel", "system_channel", fmt),
    ("Rules channel", "rules_channel", fmt),
    ("Public updates channel", "public_updates_channel", fmt),
    ("Safety alerts channel", "safety_alerts_channel", fmt),
    ("Widget channel", "widget_channel", fmt),
    ("Widget enabled", "widget_enabled", fmt),
    ("Verification level", "verification_level", fmt),
    ("Default notifications", "default_notifications", fmt),
    ("Explicit content filter", "explicit_content_filter", fmt),
    ("2FA requirement", "mfa_level", fmt),
    ("NSFW level", "nsfw_level", fmt),
    ("Preferred locale", "preferred_locale", fmt),
    ("Vanity URL", "vanity_url_code", lambda v: f"discord.gg/{v}" if v else "*None*"),
    ("Boost tier", "premium_tier", lambda v: f"Level {v}"),
    ("Boosts", "premium_subscription_count", lambda v: str(v or 0)),
    ("Boost progress bar", "premium_progress_bar_enabled", fmt),
    ("System channel flags", "system_channel_flags", lambda f: ", ".join(flag_names(f)) if f is not None else "*None*"),
)

ROLE_SPEC: tuple[tuple[str, str, Formatter], ...] = (
    ("Name", "name", fmt),
    ("Colour", "colour", fmt),
    ("Hoisted", "hoist", fmt),
    ("Mentionable", "mentionable", fmt),
    ("Icon", "icon", fmt),
    ("Emoji", "unicode_emoji", fmt),
    ("Shown in onboarding", "flags", lambda f: fmt(bool(f and f.in_prompt))),
)


class RegisteredEvents(commands.Cog, command_attrs={"hidden": True}):
    """This category is of no use for you, ignore it."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._webhooks: dict[str, discord.Webhook] = {}
        self._voice_since: dict[tuple[int, int], datetime] = {}

    async def _webhook(self, guild_id: int, event: EVENT_NAME) -> discord.Webhook | None:
        database = self.bot.database
        if not await database.is_event_enabled(guild_id, event_name=event):
            return None

        uri = await database.get_event_webhook_uri(guild_id, event_name=event)
        if not uri:
            return None

        webhook = self._webhooks.get(uri)
        if webhook is None:
            try:
                webhook = discord.Webhook.from_url(uri, session=self.bot.http_session)
            except ValueError:
                await database.edit_event(guild_id, event_name=event, enabled=False, webhook_uri=None)
                return None
            self._webhooks[uri] = webhook
        return webhook

    async def _send(
        self,
        guild_id: int,
        event: EVENT_NAME,
        webhook: discord.Webhook,
        embed: discord.Embed,
        *,
        files: list[discord.File] | None = None,
    ) -> None:
        async with self._locks[guild_id]:
            try:
                await webhook.send(embed=fit(embed), files=files or [], allowed_mentions=NO_MENTIONS, wait=False)
            except discord.HTTPException as error:
                if error.status in {401, 404}:
                    self._webhooks.pop(webhook.url, None)
                    await self.bot.database.edit_event(guild_id, event_name=event, enabled=False, webhook_uri=None)
                    _log.info("Disabled %s for guild %s: its webhook no longer exists.", event, guild_id)
                else:
                    _log.warning("Could not send %s for guild %s: %s", event, guild_id, error)

    async def _audit(
        self,
        guild: discord.Guild,
        *actions: discord.AuditLogAction,
        target_id: int | None = None,
        window: float = AUDIT_WINDOW,
    ) -> discord.AuditLogEntry | None:
        """Best-effort lookup of who caused an event. Returns ``None`` without View Audit Log."""
        me = guild.me
        if me is None or not me.guild_permissions.view_audit_log:
            return None

        await asyncio.sleep(AUDIT_DELAY)
        try:
            async for entry in guild.audit_logs(limit=15, action=actions[0] if len(actions) == 1 else discord.utils.MISSING):
                if (discord.utils.utcnow() - entry.created_at).total_seconds() > window:
                    break
                if actions and entry.action not in actions:
                    continue
                if target_id is None or getattr(entry.target, "id", None) == target_id:
                    return entry
        except discord.HTTPException:
            return None
        return None

    @staticmethod
    def _audit_is_bot(entry: discord.AuditLogEntry | None) -> bool:
        return entry is not None and is_bot_or_webhook(entry.user)

    @staticmethod
    def _add_audit(embed: discord.Embed, entry: discord.AuditLogEntry | None, *, label: str = "Responsible moderator") -> None:
        if entry is None or is_bot_or_webhook(entry.user):
            return
        if entry.user is not None:
            add(embed, label, ident(entry.user), inline=True)
        add(embed, "Reason", entry.reason)

    @staticmethod
    def _user_fields(embed: discord.Embed, user: discord.User | discord.Member) -> None:
        global_name = getattr(user, "global_name", None)
        if global_name and global_name != user.name:
            add(embed, "Display name", global_name, inline=True)
        age = discord.utils.utcnow() - user.created_at
        created_label = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Account created (new)" if age < NEW_ACCOUNT else "Account created"
        add(embed, created_label, stamp(user.created_at))
        if hasattr(user, "public_flags"):
            add(embed, "Badges", ", ".join(flag_names(user.public_flags)))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if is_bot_or_webhook(member):
            return
        webhook = await self._webhook(member.guild.id, "on_member_join")
        if webhook is None:
            return

        embed = base("Member Joined", GREEN, description=f"{member.mention} joined the server.", author=member)
        self._user_fields(embed, member)
        add(embed, "Member count", f"#{member.guild.member_count:,}", inline=True)
        add(embed, "Pending screening", "Yes" if member.pending else None, inline=True)
        add(embed, "Member flags", ", ".join(flag_names(member.flags)))
        roles = [role.mention for role in member.roles[1:] if not role.managed]
        add(embed, "Roles", " ".join(roles))
        add(embed, "Timed out until", stamp(member.timed_out_until))
        await self._send(member.guild.id, "on_member_join", webhook, embed)

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent) -> None:
        user = payload.user
        if is_bot_or_webhook(user):
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        webhook = await self._webhook(guild.id, "on_member_leave")
        if webhook is None:
            return

        member = user if isinstance(user, discord.Member) else None
        entry = await self._audit(guild, discord.AuditLogAction.kick, discord.AuditLogAction.ban, target_id=user.id)
        if entry is not None and entry.action is discord.AuditLogAction.ban:
            if await self.bot.database.is_event_enabled(guild.id, event_name="on_member_ban"):
                return
            title = "Member Banned"
        elif entry is not None and entry.action is discord.AuditLogAction.kick:
            if self._audit_is_bot(entry):
                return
            title = "Member Kicked"
        else:
            title = "Member Left"

        embed = base(title, RED, description=f"{user.mention} is no longer in the server.", author=user)
        self._user_fields(embed, user)
        self._add_audit(embed, entry)
        add(embed, "Member count", f"#{guild.member_count:,}", inline=True)

        if member is not None:
            if member.nick and member.nick != getattr(member, "global_name", None) and member.nick != member.name:
                add(embed, "Nickname", member.nick, inline=True)
            add(embed, "Joined", stamp(member.joined_at))
            add(embed, "Boosting since", stamp(member.premium_since))
            roles = sorted((r for r in member.roles[1:] if not r.managed), key=lambda r: r.position, reverse=True)
            add(embed, "Roles", " ".join(role.mention for role in roles))
        await self._send(guild.id, "on_member_leave", webhook, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member) -> None:
        if is_bot_or_webhook(user):
            return
        webhook = await self._webhook(guild.id, "on_member_ban")
        if webhook is None:
            return

        entry = await self._audit(guild, discord.AuditLogAction.ban, target_id=user.id)
        if self._audit_is_bot(entry):
            return

        embed = base("Member Banned", RED, description=f"{user.mention} was banned.", author=user)
        self._user_fields(embed, user)
        self._add_audit(embed, entry)

        if entry is None or entry.reason is None:
            try:
                ban = await guild.fetch_ban(user)
            except discord.HTTPException:
                ban = None
            if ban is not None and ban.reason:
                add(embed, "Reason", ban.reason)

        if isinstance(user, discord.Member):
            add(embed, "Joined", stamp(user.joined_at))
            roles = [role.mention for role in user.roles[1:] if not role.managed]
            add(embed, "Roles", " ".join(roles))
        await self._send(guild.id, "on_member_ban", webhook, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        if is_bot_or_webhook(user):
            return
        webhook = await self._webhook(guild.id, "on_member_unban")
        if webhook is None:
            return

        entry = await self._audit(guild, discord.AuditLogAction.unban, target_id=user.id)
        if self._audit_is_bot(entry):
            return

        embed = base("Member Unbanned", GREEN, description=f"{user.mention} was unbanned.", author=user)
        self._user_fields(embed, user)
        self._add_audit(embed, entry)
        await self._send(guild.id, "on_member_unban", webhook, embed)

    @staticmethod
    def _message_fields(embed: discord.Embed, message: discord.Message) -> None:
        if message.attachments:
            lines = [
                f"[{a.filename}]({a.url}) \N{MIDDLE DOT} {a.size / 1024:.1f} KB \N{MIDDLE DOT} {a.content_type or 'unknown'}"
                for a in message.attachments
            ]
            add(embed, f"Attachments ({len(lines)})", "\n".join(lines))
        add(embed, "Stickers", ", ".join(s.name for s in message.stickers))
        if message.embeds:
            add(
                embed,
                f"Embeds ({len(message.embeds)})",
                ", ".join(clip(e.title or e.url or str(e.type), 60) for e in message.embeds),
            )
        if message.poll is not None:
            add(embed, "Poll", message.poll.question)
        if message.reference is not None and message.reference.message_id:
            add(embed, "Reply to", f"[Jump to parent]({message.reference.jump_url})", inline=True)
        if message.reactions:
            add(embed, "Reactions", ", ".join(f"{r.emoji} \N{MULTIPLICATION SIGN}{r.count}" for r in message.reactions))

        add(embed, "Pinned", "Yes" if message.pinned else None, inline=True)
        add(embed, "TTS", "Yes" if message.tts else None, inline=True)
        add(embed, "Type", None if message.type is discord.MessageType.default else fmt(message.type), inline=True)
        add(embed, "Flags", ", ".join(flag_names(message.flags)))
        add(embed, "Forwarded", "Yes" if getattr(message, "message_snapshots", None) else None, inline=True)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            return

        message = payload.cached_message
        if message is not None and is_bot_or_webhook(message):
            return

        webhook = await self._webhook(guild.id, "on_message_delete")
        if webhook is None:
            return

        channel = guild.get_channel_or_thread(payload.channel_id)
        sent = discord.utils.snowflake_time(payload.message_id)

        if message is None:
            embed = base(
                "Message Deleted",
                RED,
                description="*This message wasn't cached, so its author and content are unavailable.*",
                footer=f"Message ID: {payload.message_id}",
            )
            add(embed, "Channel", mention(channel) if channel else f"`{payload.channel_id}`", inline=True)
            add(embed, "Sent", stamp(sent))
            await self._send(guild.id, "on_message_delete", webhook, embed)
            return

        entry = await self._audit(guild, discord.AuditLogAction.message_delete, target_id=message.author.id, window=6.0)
        if self._audit_is_bot(entry):
            return

        embed = base(
            "Message Deleted",
            RED,
            description=clip(message.content, 4000) if message.content else "*No text content.*",
            author=message.author,
            footer=f"Author ID: {message.author.id} \N{MIDDLE DOT} Message ID: {payload.message_id}",
        )
        add(embed, "Channel", mention(channel) if channel else f"`{payload.channel_id}`", inline=True)
        add(embed, "Sent", stamp(sent))
        self._message_fields(embed, message)

        if entry is not None and getattr(entry.extra, "channel", None) is not None and entry.extra.channel.id == payload.channel_id:  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
            self._add_audit(embed, entry, label="Deleted by")
        await self._send(guild.id, "on_message_delete", webhook, embed)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            return

        human_messages = [m for m in payload.cached_messages if not is_bot_or_webhook(m)]
        if payload.cached_messages and not human_messages:
            return

        webhook = await self._webhook(guild.id, "on_message_delete")
        if webhook is None:
            return

        channel = guild.get_channel_or_thread(payload.channel_id)
        embed = base("Messages Bulk Deleted", RED, footer=f"Channel ID: {payload.channel_id}")
        add(embed, "Channel", mention(channel) if channel else f"`{payload.channel_id}`", inline=True)
        add(embed, "Deleted", f"{len(payload.message_ids)} messages", inline=True)
        if human_messages:
            add(embed, "Logged (human)", f"{len(human_messages)} messages", inline=True)

        lines = []
        for message in sorted(human_messages, key=lambda m: m.id):
            extras = " ".join(a.url for a in message.attachments)
            lines.append(f"[{message.created_at:%Y-%m-%d %H:%M:%S}] {message.author} ({message.author.id}): {message.content} {extras}".rstrip())

        files = [text_file("deleted-messages.txt", "\n".join(lines))] if lines else []
        if files:
            embed.description = "A transcript of the cached user messages is attached."
        await self._send(guild.id, "on_message_delete", webhook, embed, files=files)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        after = payload.message
        if guild is None or after is None or after.edited_at is None:
            return
        if is_bot_or_webhook(after):
            return

        before = payload.cached_message
        if before is not None and is_bot_or_webhook(before):
            return
        removed = [a.filename for a in before.attachments if a.id not in {x.id for x in after.attachments}] if before is not None else []
        if before is not None and before.content == after.content and not removed:
            return

        webhook = await self._webhook(guild.id, "on_message_edit")
        if webhook is None:
            return

        embed = base(
            "Message Edited",
            ORANGE,
            description=f"{after.author.mention} edited a [message]({after.jump_url}) in {mention(after.channel)}.",
            author=after.author,
            footer=f"Author ID: {after.author.id} \N{MIDDLE DOT} Message ID: {after.id}",
        )
        files: list[discord.File] = []

        new_text = after.content or "*No text content.*"
        old_text = "*Unavailable - the original message wasn't cached.*" if before is None else before.content or "*No text content.*"

        for label, text, filename in (("Before", old_text, "before.txt"), ("After", new_text, "after.txt")):
            add(embed, label, text)
            if len(text) > 1024:
                files.append(text_file(filename, text))

        add(embed, "Sent", stamp(after.created_at))
        add(embed, "Attachments removed", ", ".join(removed))
        await self._send(guild.id, "on_message_edit", webhook, embed, files=files)

    @staticmethod
    def _channel_summary(embed: discord.Embed, channel: discord.abc.GuildChannel, *, created: bool = False) -> None:
        add(embed, "Type", fmt(channel.type), inline=True)
        add(embed, "Category", getattr(channel.category, "name", None), inline=True)
        add(embed, "Position", channel.position, inline=True)
        if not created:
            add(embed, "Created", stamp(channel.created_at))

        for label, attribute, formatter in CHANNEL_SPEC[2:]:
            if label in {"Category", "Synced with category"}:
                continue
            value = getattr(channel, attribute, _MISSING)
            if value is _MISSING or value in (None, 0, False, "", []):
                continue
            add(embed, label, formatter(value), inline=True)

        overwrites = overwrite_lines(channel)
        if overwrites:
            add(embed, f"Permission overwrites ({len(overwrites)})", "\n".join(overwrites))

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        webhook = await self._webhook(channel.guild.id, "on_channel_create")
        if webhook is None:
            return

        entry = await self._audit(channel.guild, discord.AuditLogAction.channel_create, target_id=channel.id)
        if self._audit_is_bot(entry):
            return

        embed = base(
            "Channel Created",
            GREEN,
            description=f"{getattr(channel, 'mention', f'**{channel.name}**')} was created.",
            footer=f"Channel ID: {channel.id}",
        )
        self._channel_summary(embed, channel, created=True)
        self._add_audit(embed, entry, label="Created by")
        await self._send(channel.guild.id, "on_channel_create", webhook, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        webhook = await self._webhook(channel.guild.id, "on_channel_delete")
        if webhook is None:
            return

        entry = await self._audit(channel.guild, discord.AuditLogAction.channel_delete, target_id=channel.id)
        if self._audit_is_bot(entry):
            return

        embed = base("Channel Deleted", RED, description=f"**#{channel.name}** was deleted.", footer=f"Channel ID: {channel.id}")
        self._channel_summary(embed, channel, created=False)
        self._add_audit(embed, entry, label="Deleted by")
        await self._send(channel.guild.id, "on_channel_delete", webhook, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        changes = diff(before, after, CHANNEL_SPEC)
        overwrites = overwrite_changes(before, after)
        if not changes and not overwrites:
            return

        webhook = await self._webhook(after.guild.id, "on_channel_update")
        if webhook is None:
            return

        entry = await self._audit(
            after.guild,
            discord.AuditLogAction.channel_update,
            discord.AuditLogAction.overwrite_create,
            discord.AuditLogAction.overwrite_update,
            discord.AuditLogAction.overwrite_delete,
            target_id=after.id,
        )
        if self._audit_is_bot(entry):
            return

        embed = base(
            "Channel Updated",
            ORANGE,
            description=f"{getattr(after, 'mention', f'**{after.name}**')} was updated.",
            footer=f"Channel ID: {after.id}",
        )
        add_changes(embed, changes)
        add(embed, "Permission overwrites", "\n".join(overwrites))
        self._add_audit(embed, entry, label="Updated by")
        await self._send(after.guild.id, "on_channel_update", webhook, embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        if is_bot_or_webhook(thread.owner):
            return
        owner = thread.guild.get_member(thread.owner_id)
        if is_bot_or_webhook(owner):
            return

        webhook = await self._webhook(thread.guild.id, "on_thread_create")
        if webhook is None:
            return

        embed = base("Thread Created", GREEN, description=f"{thread.mention} was created.", footer=f"Thread ID: {thread.id}")
        add(embed, "Parent", mention(thread.parent) if thread.parent else f"`{thread.parent_id}`", inline=True)
        add(embed, "Type", fmt(thread.type), inline=True)
        add(embed, "Owner", f"<@{thread.owner_id}>" if thread.owner_id else None, inline=True)
        add(embed, "Auto-archive", minutes(thread.auto_archive_duration), inline=True)
        if thread.slowmode_delay:
            add(embed, "Slowmode", seconds(thread.slowmode_delay), inline=True)
        add(embed, "Invitable", fmt(thread.invitable) if thread.is_private() else None, inline=True)
        add(embed, "Tags", ", ".join(t.name for t in thread.applied_tags))
        if isinstance(thread.parent, discord.ForumChannel):
            add(embed, "Starter message", f"[Jump](https://discord.com/channels/{thread.guild.id}/{thread.id}/{thread.id})", inline=True)
        await self._send(thread.guild.id, "on_thread_create", webhook, embed)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        thread = payload.thread
        if thread is not None and is_bot_or_webhook(thread.owner):
            return

        webhook = await self._webhook(guild.id, "on_thread_delete")
        if webhook is None:
            return

        entry = await self._audit(guild, discord.AuditLogAction.thread_delete, target_id=payload.thread_id)
        if self._audit_is_bot(entry):
            return

        parent = guild.get_channel(payload.parent_id)
        embed = base("Thread Deleted", RED, footer=f"Thread ID: {payload.thread_id}")
        embed.description = f"**{thread.name}** was deleted." if thread else "A thread was deleted. *Its details weren't cached.*"
        add(embed, "Parent", mention(parent) if parent else f"`{payload.parent_id}`", inline=True)
        add(embed, "Type", fmt(payload.thread_type), inline=True)
        add(embed, "Created", stamp(discord.utils.snowflake_time(payload.thread_id)))
        if thread is not None:
            add(embed, "Owner", f"<@{thread.owner_id}>" if thread.owner_id else None, inline=True)
            add(embed, "Messages", thread.message_count, inline=True)
            add(embed, "Members", thread.member_count, inline=True)
            add(embed, "Tags", ", ".join(t.name for t in thread.applied_tags))
        self._add_audit(embed, entry, label="Deleted by")
        await self._send(guild.id, "on_thread_delete", webhook, embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread) -> None:
        changes = diff(before, after, THREAD_SPEC)
        if not changes:
            return

        webhook = await self._webhook(after.guild.id, "on_thread_update")
        if webhook is None:
            return

        entry = await self._audit(after.guild, discord.AuditLogAction.thread_update, target_id=after.id)
        if self._audit_is_bot(entry):
            return

        embed = base("Thread Updated", ORANGE, description=f"{after.mention} was updated.", footer=f"Thread ID: {after.id}")
        add(embed, "Parent", mention(after.parent) if after.parent else f"`{after.parent_id}`", inline=True)
        add_changes(embed, changes)
        self._add_audit(embed, entry, label="Updated by")
        await self._send(after.guild.id, "on_thread_update", webhook, embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        changes = diff(before, after, GUILD_SPEC)
        added, removed = sorted(set(after.features) - set(before.features)), sorted(set(before.features) - set(after.features))
        if not changes and not added and not removed:
            return

        webhook = await self._webhook(after.id, "on_server_update")
        if webhook is None:
            return

        entry = await self._audit(after, discord.AuditLogAction.guild_update)
        if self._audit_is_bot(entry):
            return

        embed = base("Server Updated", ORANGE, description=f"**{after.name}** was updated.", footer=f"Server ID: {after.id}")
        if after.icon is not None and before.icon != after.icon:
            embed.set_thumbnail(url=after.icon.url)
        if after.banner is not None and before.banner != after.banner:
            embed.set_image(url=after.banner.url)

        add_changes(embed, changes)
        add(embed, "Features added", ", ".join(f.replace("_", " ").title() for f in added))
        add(embed, "Features removed", ", ".join(f.replace("_", " ").title() for f in removed))
        self._add_audit(embed, entry, label="Updated by")
        await self._send(after.id, "on_server_update", webhook, embed)

    @staticmethod
    def _role_summary(embed: discord.Embed, role: discord.Role, *, created: bool = False) -> None:
        if role.colour.value:
            add(embed, "Colour", str(role.colour), inline=True)
        add(embed, "Position", role.position, inline=True)
        if role.hoist:
            add(embed, "Hoisted", "Yes", inline=True)
        if role.mentionable:
            add(embed, "Mentionable", "Yes", inline=True)
        if not created:
            add(embed, "Created", stamp(role.created_at))
        add(embed, "Emoji", role.unicode_emoji, inline=True)
        add(embed, "Icon", f"[link]({role.icon.url})" if role.icon else None, inline=True)

        tags = role.tags
        if tags:
            details = []
            if tags.is_premium_subscriber():
                details.append("Server booster role")
            if tags.is_guild_connection():
                details.append("Linked role")
            if tags.is_available_for_purchase():
                details.append("Purchasable")
            add(embed, "Role tags", ", ".join(details))

        permissions = permission_names(role.permissions)
        if permissions:
            add(embed, f"Permissions ({len(permissions)})", ", ".join(permissions))
        if role.permissions.administrator:
            add(embed, "\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Warning", "This role grants **Administrator**.")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        if role.managed or (role.tags and (role.tags.bot_id or role.tags.integration_id)):
            return
        webhook = await self._webhook(role.guild.id, "on_role_create")
        if webhook is None:
            return

        entry = await self._audit(role.guild, discord.AuditLogAction.role_create, target_id=role.id)
        if self._audit_is_bot(entry):
            return

        embed = base("Role Created", GREEN, description=f"{role.mention} was created.", footer=f"Role ID: {role.id}")
        self._role_summary(embed, role, created=True)
        self._add_audit(embed, entry, label="Created by")
        await self._send(role.guild.id, "on_role_create", webhook, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        if role.managed or (role.tags and (role.tags.bot_id or role.tags.integration_id)):
            return
        webhook = await self._webhook(role.guild.id, "on_role_delete")
        if webhook is None:
            return

        entry = await self._audit(role.guild, discord.AuditLogAction.role_delete, target_id=role.id)
        if self._audit_is_bot(entry):
            return

        embed = base("Role Deleted", RED, description=f"**@{role.name}** was deleted.", footer=f"Role ID: {role.id}")
        self._role_summary(embed, role, created=False)
        add(embed, "Members who had it", len(role.members) or None, inline=True)
        self._add_audit(embed, entry, label="Deleted by")
        await self._send(role.guild.id, "on_role_delete", webhook, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        if after.managed or (after.tags and (after.tags.bot_id or after.tags.integration_id)):
            return
        changes = diff(before, after, ROLE_SPEC)
        granted, revoked = permission_delta(before.permissions, after.permissions)
        if not changes and not granted and not revoked:
            return

        webhook = await self._webhook(after.guild.id, "on_role_update")
        if webhook is None:
            return

        entry = await self._audit(after.guild, discord.AuditLogAction.role_update, target_id=after.id)
        if self._audit_is_bot(entry):
            return

        embed = base("Role Updated", ORANGE, description=f"{after.mention} was updated.", footer=f"Role ID: {after.id}")
        add_changes(embed, changes)
        add(embed, "Permissions granted", ", ".join(granted))
        add(embed, "Permissions revoked", ", ".join(revoked))
        if "Administrator" in granted:
            add(embed, "\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Warning", "This role now grants **Administrator**.")
        if after.members:
            add(embed, "Members with role", len(after.members), inline=True)
        self._add_audit(embed, entry, label="Updated by")
        await self._send(after.guild.id, "on_role_update", webhook, embed)

    @staticmethod
    def _voice_flags(state: discord.VoiceState) -> str | None:
        flags = (
            ("Server muted", state.mute),
            ("Server deafened", state.deaf),
            ("Self muted", state.self_mute),
            ("Self deafened", state.self_deaf),
            ("Streaming", state.self_stream),
            ("Camera on", state.self_video),
            ("Suppressed", state.suppress),
            ("AFK", state.afk),
            ("Requested to speak", state.requested_to_speak_at is not None),
        )
        active = [name for name, on in flags if on]
        return ", ".join(active) if active else None

    @staticmethod
    def _voice_channel(channel: discord.VoiceChannel | discord.StageChannel, *, include_mention: bool = False) -> str:
        lines = []
        if include_mention:
            lines.append(f"{channel.mention} (`{channel.id}`)")
        else:
            lines.append(f"ID: `{channel.id}`")
        lines.append(f"Members now: {sum(1 for m in channel.members if not m.bot)}")
        if channel.user_limit:
            lines.append(f"User limit: {channel.user_limit}")
        if channel.category is not None:
            lines.append(f"Category: {channel.category.name}")
        return "\n".join(lines)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        if is_bot_or_webhook(member) or before.channel == after.channel:
            return

        key = (member.guild.id, member.id)
        since = self._voice_since.pop(key, None)
        if after.channel is not None:
            self._voice_since[key] = discord.utils.utcnow()

        if before.channel is None and after.channel is not None:
            event, title, colour = "on_member_join_voice", "Joined Voice Channel", GREEN
            description = f"{member.mention} joined {after.channel.mention}."
        elif after.channel is None and before.channel is not None:
            event, title, colour = "on_member_leave_voice", "Left Voice Channel", RED
            description = f"{member.mention} left {before.channel.mention}."
        elif before.channel is not None and after.channel is not None:
            event, title, colour = "on_member_move_voice", "Moved Voice Channel", BLUE
            description = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}."
        else:
            return

        webhook = await self._webhook(member.guild.id, event)
        if webhook is None:
            return

        embed = base(title, colour, description=description, author=member)
        if event == "on_member_join_voice" and after.channel is not None:
            add(embed, "Channel details", self._voice_channel(after.channel), inline=True)
        elif event == "on_member_leave_voice" and before.channel is not None:
            add(embed, "Channel details", self._voice_channel(before.channel), inline=True)
        elif before.channel is not None and after.channel is not None:
            add(embed, "From", self._voice_channel(before.channel), inline=True)
            add(embed, "To", self._voice_channel(after.channel), inline=True)

        if since is not None and before.channel is not None:
            add(embed, "Time in channel", human_timedelta(since, accuracy=3, suffix=False), inline=True)
        add(embed, "Active flags", self._voice_flags(after if after.channel is not None else before), inline=True)
        await self._send(member.guild.id, event, webhook, embed)
