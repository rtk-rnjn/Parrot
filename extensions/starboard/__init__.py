from __future__ import annotations

import contextlib
import io
import json
import logging
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any

import discord
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from core import Bot
    from core.utils.database.models import StarboardConfig, StarboardEntry

_log = logging.getLogger(__name__)

__all__ = ("Starboard",)

DEFAULT_EMOJI = "\N{WHITE MEDIUM STAR}"
DEFAULT_THRESHOLD = 3
ENTRY_COLOUR = 0xFFAC33
ALLOW_BOT_MESSAGES = False  # not in your config schema; flip to True to let bot messages in

FLUSH_INTERVAL = 5  # seconds between flushes
MAX_PER_FLUSH = 20  # messages handled per flush (keeps us far from rate limits)
SETTINGS_TTL = 30.0  # seconds the assembled settings stay in memory
USER_SCAN_LIMIT = 500  # max reactors listed when a message first reaches the board
SYNC_LIMIT = 200
EXPORT_LIMIT = 5000
MAX_CONTENT = 2000  # a message may carry at most 4000 characters of text in total
NO_MENTIONS = discord.AllowedMentions.none()
MEDALS = ("\N{FIRST PLACE MEDAL}", "\N{SECOND PLACE MEDAL}", "\N{THIRD PLACE MEDAL}")
DOT = " \N{MIDDLE DOT} "


def shorten(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"


def parse_message_id(text: str) -> int | None:
    """Accepts a bare id or a full message link; the message id is always the last number."""
    numbers = re.findall(r"\d{15,21}", text)
    return int(numbers[-1]) if numbers else None


def message_url(guild_id: int, channel_id: int, message_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


def guild_of(ctx: commands.Context[Bot]) -> discord.Guild:
    assert ctx.guild is not None  # every command is guild_only
    return ctx.guild


def yes_no(value: bool) -> str:
    return "on" if value else "off"


def is_nsfw(channel: Any) -> bool:
    check = getattr(channel, "is_nsfw", None)
    return bool(check and check())


def rank(index: int) -> str:
    return MEDALS[index] if index < len(MEDALS) else f"`{index + 1}.`"


def panel(title: str, body: str, *, colour: int = ENTRY_COLOUR) -> discord.ui.LayoutView:
    """A read-only Components V2 card."""
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(f"## {title}"),
            discord.ui.Separator(),
            discord.ui.TextDisplay(shorten(body, 3500)),
            accent_colour=discord.Colour(colour),
        )
    )
    return view


class StarboardEntryView(discord.ui.LayoutView):
    """What gets posted in the starboard channel. Only link buttons, so it needs no callbacks and survives restarts."""

    def __init__(self, message: discord.Message, stars: int, emoji: str) -> None:
        super().__init__(timeout=None)
        nsfw = is_nsfw(message.channel)

        children: list[discord.ui.Item[Any]] = [discord.ui.TextDisplay(f"{emoji} **{stars}**{DOT}<#{message.channel.id}>")]

        reference = message.reference.resolved if message.reference else None
        if isinstance(reference, discord.Message):
            snippet = shorten(reference.clean_content.replace("\n", " "), 100) or "attachment"
            children.append(discord.ui.TextDisplay(f"-# \N{LEFTWARDS ARROW WITH HOOK} {reference.author.display_name}: {snippet}"))

        text = f"**{message.author.display_name}**"
        if message.content:
            text += "\n" + shorten(message.content, MAX_CONTENT)
        children.append(discord.ui.Section(discord.ui.TextDisplay(text), accessory=discord.ui.Thumbnail(message.author.display_avatar.url)))

        gallery: list[discord.MediaGalleryItem] = []
        links: list[str] = []
        for attachment in message.attachments:
            if (attachment.content_type or "").startswith(("image/", "video/")) and len(gallery) < 10:
                gallery.append(discord.MediaGalleryItem(attachment.url, description=attachment.description, spoiler=attachment.is_spoiler() or nsfw))
            else:
                links.append(f"[{attachment.filename}]({attachment.url})")
        for embed in message.embeds:
            if embed.type == "image" and embed.url and len(gallery) < 10:
                gallery.append(discord.MediaGalleryItem(embed.url, spoiler=nsfw))
        if gallery:
            children.append(discord.ui.MediaGallery(*gallery))
        if links:
            children.append(discord.ui.TextDisplay("\N{PAPERCLIP} " + DOT.join(links[:5])))

        children.append(discord.ui.Separator())
        children.append(
            discord.ui.Section(
                discord.ui.TextDisplay(f"-# {discord.utils.format_dt(message.created_at, 'R')}{DOT}ID {message.id}"),
                accessory=discord.ui.Button(label="Jump to message", url=message.jump_url),
            )
        )
        self.add_item(discord.ui.Container(*children, accent_colour=discord.Colour(ENTRY_COLOUR)))


@dataclass(slots=True)
class Job:
    """Everything that happened to one message since the last flush."""

    channel_id: int
    users: dict[int, bool] = field(default_factory=dict)  # user id -> reacted (True) or removed (False); last event wins
    rebuild: bool = False  # recount from the live reactions instead of trusting the stored users


class Starboard(commands.Cog):
    """Collect starred messages in a dedicated channel."""

    help_category = "Starboard"
    help_emoji = DEFAULT_EMOJI
    help_description = "Highlight the best messages of your server."

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._pending: dict[tuple[int, int], Job] = {}  # insertion order = processing order
        self._settings_cache: dict[int, tuple[float, StarboardConfig]] = {}

    async def cog_load(self) -> None:
        entries = self.bot.database.starboards_collection
        await entries.create_index([("guild_id", 1), ("source_message_id", 1)], unique=True)
        await entries.create_index([("guild_id", 1), ("board_message_id", 1)])
        self.flush.start()

    async def cog_unload(self) -> None:
        self.flush.stop()
        await self._flush_once()  # best effort; `starboard sync` repairs whatever is still queued

    async def get_settings(self, guild_id: int) -> StarboardConfig:
        """All settings in one dict, kept in memory for a few seconds.

        Reaction events arrive in every guild, so this keeps the hot path off Redis and Mongo, and it also caches
        "no starboard configured", which your individual getters do not cache.
        """
        cached = self._settings_cache.get(guild_id)
        if cached is not None and time.monotonic() - cached[0] < SETTINGS_TTL:
            return cached[1]

        db = self.bot.database

        settings: StarboardConfig = {
            "enabled": await db.is_starboard_enabled(guild_id),
            "channel_id": await db.get_starboard_board_channel_id(guild_id),
            "emoji": await db.get_starboard_emoji(guild_id) or DEFAULT_EMOJI,
            "threshold": await db.get_starboard_threshold(guild_id) or DEFAULT_THRESHOLD,
            "self_star": await db.is_starboard_self_star_enabled(guild_id),
            "allow_nsfw": await db.is_starboard_nsfw_allowed(guild_id),
            "max_age_days": await db.get_starboard_max_age_days(guild_id) or 30,
            "ignored_channels": await db.get_starboard_ignored_channels(guild_id),
            "ignored_roles": await db.get_starboard_ignored_roles(guild_id),
            "ignored_users": await db.get_starboard_ignored_users(guild_id),
        }
        self._settings_cache[guild_id] = (time.monotonic(), settings)
        return settings

    async def _edit(self, guild_id: int, **fields: Any) -> None:
        await self.bot.database.edit_starboard_config(guild_id=guild_id, **fields)
        self._settings_cache.pop(guild_id, None)

    def enqueue(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        *,
        user_id: int | None = None,
        added: bool = True,
        rebuild: bool = False,
    ) -> None:
        """Mark a message as dirty. Fifty reactions on one message in five seconds still cost one update."""
        job = self._pending.setdefault((guild_id, message_id), Job(channel_id))
        if user_id is not None:
            job.users[user_id] = added
        job.rebuild = job.rebuild or rebuild

    @tasks.loop(seconds=FLUSH_INTERVAL)
    async def flush(self) -> None:
        await self._flush_once()

    @flush.before_loop
    async def _before_flush(self) -> None:
        await self.bot.wait_until_ready()

    async def _flush_once(self) -> None:
        keys = [key for _, key in zip(range(MAX_PER_FLUSH), self._pending, strict=False)]
        for key in keys:
            job = self._pending.pop(key)  # popped *before* work, so a reaction arriving meanwhile re-queues it
            try:
                await self._process(key[0], key[1], job)
            except Exception:
                _log.exception("Starboard update failed for message %s", key[1])

    @commands.Cog.listener("on_raw_reaction_add")
    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_star_reaction(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or (self.bot.user is not None and payload.user_id == self.bot.user.id):
            return

        settings = await self.get_settings(payload.guild_id)
        if not settings["enabled"] or settings["channel_id"] is None or str(payload.emoji) != settings["emoji"]:
            return
        if payload.channel_id == settings["channel_id"] or payload.channel_id in settings["ignored_channels"]:
            return

        added = payload.event_type == "REACTION_ADD"
        if added and payload.member is not None and payload.member.bot:
            return
        if added and not settings["self_star"] and getattr(payload, "message_author_id", None) == payload.user_id:
            return

        self.enqueue(payload.guild_id, payload.channel_id, payload.message_id, user_id=payload.user_id, added=added)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if payload.guild_id is not None:
            await self._handle_deleted(payload.guild_id, payload.channel_id, [payload.message_id])

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent) -> None:
        if payload.guild_id is not None:
            await self._handle_deleted(payload.guild_id, payload.channel_id, list(payload.message_ids))

    async def _handle_deleted(self, guild_id: int, channel_id: int, message_ids: list[int]) -> None:
        settings = await self.get_settings(guild_id)
        if not settings["enabled"] or settings["channel_id"] is None:
            return

        db = self.bot.database
        guild = self.bot.get_guild(guild_id)
        board = guild.get_channel(settings["channel_id"]) if guild else None

        for message_id in message_ids:
            if channel_id == settings["channel_id"]:
                # Somebody deleted a board message by hand: forget the entry so a new star can repost it.
                entry = await db.get_starboard_entry_by_board_message_id(guild_id=guild_id, board_message_id=message_id)
                if entry is not None:
                    await db.delete_starboard_entry(guild_id=guild_id, source_message_id=entry["source_message_id"])
            else:
                entry = await db.get_starboard_entry(guild_id=guild_id, source_message_id=message_id)
                if entry is not None:  # the original is gone, so is its entry
                    if isinstance(board, discord.TextChannel):
                        await self._delete_board_message(board, entry["board_message_id"])
                    await db.delete_starboard_entry(guild_id=guild_id, source_message_id=message_id)

    async def _process(self, guild_id: int, message_id: int, job: Job) -> None:
        settings = await self.get_settings(guild_id)
        guild = self.bot.get_guild(guild_id)
        if guild is None or not settings["enabled"] or settings["channel_id"] is None:
            return

        board = guild.get_channel(settings["channel_id"])
        source = guild.get_channel_or_thread(job.channel_id)
        if not isinstance(board, discord.TextChannel) or not isinstance(source, discord.abc.Messageable):
            return

        entry = await self.bot.database.get_starboard_entry(guild_id=guild_id, source_message_id=message_id)
        if entry is None:
            await self._add_to_board(guild_id, message_id, job, board, source, settings)
        else:
            await self._update_entry(guild_id, message_id, job, entry, board, source, settings)

    async def _add_to_board(
        self,
        guild_id: int,
        message_id: int,
        job: Job,
        board: discord.TextChannel,
        source: discord.abc.Messageable,
        settings: StarboardConfig,
    ) -> None:
        """Not on the board yet. Raw events work for uncached (old) messages, so fetch and count the live reactions."""
        message = await self.bot.get_or_fetch_message(source, message_id)
        if message is None or not self._eligible(message, source, settings, is_new=True):
            return

        reaction = next((reaction for reaction in message.reactions if str(reaction.emoji) == settings["emoji"]), None)
        if reaction is None or reaction.count < settings["threshold"]:
            return  # cheap exit, no reactor list needed

        users = await self._reactors(message, settings, reaction)
        if len(users) < settings["threshold"]:
            return

        board_id = await self._upsert(board, message, None, len(users), settings["emoji"])
        if board_id is None:
            return
        await self.bot.database.add_starboard_entry(
            guild_id=guild_id,
            source_message_id=message_id,
            source_channel_id=job.channel_id,
            board_message_id=board_id,
            author_id=message.author.id,
            users=sorted(users),
            star_count=len(users),
            is_nsfw=is_nsfw(source),
        )

    async def _update_entry(  # noqa: PLR0912
        self,
        guild_id: int,
        message_id: int,
        job: Job,
        entry: StarboardEntry,
        board: discord.TextChannel,
        source: discord.abc.Messageable,
        settings: StarboardConfig,
    ) -> None:
        db = self.bot.database
        current = set(entry.get("users") or [])
        board_id: int = entry["board_message_id"]
        # Entries whose stored users do not add up to the stored count (older data) are recounted from reactions.
        rebuild = job.rebuild or len(current) != entry.get("star_count", 0)

        message: discord.Message | None = None
        if rebuild:
            message = await self.bot.get_or_fetch_message(source, message_id)
            if message is None:
                return
            reaction = next((reaction for reaction in message.reactions if str(reaction.emoji) == settings["emoji"]), None)
            target = await self._reactors(message, settings, reaction) if reaction else set()
        else:
            target = set(current)
            for user_id, added in job.users.items():
                if added and (user_id != entry.get("author_id") or settings["self_star"]):
                    target.add(user_id)
                elif not added:
                    target.discard(user_id)

        if not rebuild and target == current:
            return  # net effect of the burst was nothing

        message = message or await self.bot.get_or_fetch_message(source, message_id)
        if message is None:
            return

        stars = len(target)
        if stars < settings["threshold"]:
            await self._delete_board_message(board, board_id)
            await db.delete_starboard_entry(guild_id=guild_id, source_message_id=message_id)
            return

        new_board_id = await self._upsert(board, message, board_id, stars, settings["emoji"])
        if new_board_id is None:
            return

        if new_board_id != board_id:  # the old board message had vanished; your mixin has no "update board id", so swap the entry
            await db.delete_starboard_entry(guild_id=guild_id, source_message_id=message_id)
            await db.add_starboard_entry(
                guild_id=guild_id,
                source_message_id=message_id,
                source_channel_id=job.channel_id,
                board_message_id=new_board_id,
                author_id=entry["author_id"],
                users=sorted(target),
                star_count=stars,
                is_nsfw=bool(entry.get("is_nsfw")),
            )
            return

        for user_id in target - current:
            await db.add_user_to_starboard_entry(guild_id=guild_id, source_message_id=message_id, user_id=user_id)
        for user_id in current - target:
            await db.remove_user_from_starboard_entry(guild_id=guild_id, source_message_id=message_id, user_id=user_id)

    def _eligible(  # noqa: PLR0911
        self,
        message: discord.Message,
        source: Any,
        settings: StarboardConfig,
        *,
        is_new: bool,
    ) -> bool:
        if message.type not in (discord.MessageType.default, discord.MessageType.reply):
            return False
        if message.author.bot and not ALLOW_BOT_MESSAGES:
            return False
        if message.author.id in settings["ignored_users"]:
            return False

        ignored = set(settings["ignored_channels"])
        if message.channel.id in ignored or getattr(source, "parent_id", None) in ignored:
            return False
        if is_nsfw(source) and not settings["allow_nsfw"]:
            return False

        member = message.guild.get_member(message.author.id) if message.guild else None
        if member is not None and any(role.id in settings["ignored_roles"] for role in member.roles):
            return False

        # The age limit only stops *new* entries; messages already on the board keep updating.
        max_age = settings["max_age_days"]
        return not (is_new and max_age and (discord.utils.utcnow() - message.created_at).days >= max_age)

    async def _reactors(self, message: discord.Message, settings: StarboardConfig, reaction: discord.Reaction) -> set[int]:
        me = self.bot.user.id if self.bot.user else 0
        users: set[int] = set()
        async for user in reaction.users(limit=USER_SCAN_LIMIT):
            if user.bot or user.id == me:
                continue
            if user.id == message.author.id and not settings["self_star"]:
                continue
            users.add(user.id)
        return users

    async def _upsert(self, board: discord.TextChannel, message: discord.Message, board_id: int | None, stars: int, emoji: str) -> int | None:
        if board_id is not None:
            partial = board.get_partial_message(board_id)  # no extra fetch needed to edit
            try:
                await partial.edit(view=StarboardEntryView(message, stars, emoji))
                return board_id
            except discord.Forbidden:
                _log.warning("Cannot edit starboard message %s", board_id)
                return board_id
            except discord.NotFound:
                pass  # deleted meanwhile, post a fresh one
            except discord.HTTPException:
                # Entries made by an embed-based version cannot be turned into Components V2 messages.
                await partial.delete(delay=0)

        try:
            sent = await board.send(view=StarboardEntryView(message, stars, emoji), allowed_mentions=NO_MENTIONS)
        except discord.HTTPException:
            _log.warning("Cannot post to starboard channel %s", board.id, exc_info=True)
            return None
        return sent.id

    @staticmethod
    async def _delete_board_message(board: discord.TextChannel, board_id: int) -> None:
        with contextlib.suppress(discord.NotFound, discord.Forbidden):
            await board.get_partial_message(board_id).delete(delay=0)

    @commands.group(name="starboard", aliases=["sb"], invoke_without_command=True)
    @commands.guild_only()
    async def starboard(self, ctx: commands.Context[Bot]) -> None:
        """Show the current starboard configuration."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @starboard.command(name="threshold")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_threshold(
        self,
        ctx: commands.Context[Bot],
        amount: Annotated[int, commands.Range[int, 1, 100]] = commands.parameter(description="Stars needed"),
    ) -> None:
        """Set how many stars a message needs."""
        await self._edit(guild_of(ctx).id, threshold=amount)
        await ctx.reply(f"Messages now need **{amount}** stars.")

    @starboard.command(name="emoji")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_emoji(self, ctx: commands.Context[Bot], emoji: str = commands.parameter(description="Unicode or custom emoji")) -> None:
        """Set the reaction that counts as a star."""
        partial = discord.PartialEmoji.from_str(emoji.strip())
        await self._edit(guild_of(ctx).id, emoji=str(partial))
        await ctx.reply(
            f"The star emoji is now {partial}. Existing entries keep their stars; run `{ctx.clean_prefix}starboard sync` to recount them."
        )

    @starboard.command(name="toggle")
    @commands.has_guild_permissions(manage_guild=True)
    async def toggle(self, ctx: commands.Context[Bot]) -> None:
        """Turn the starboard on or off."""
        self._settings_cache.pop(guild_of(ctx).id, None)
        settings = await self.get_settings(guild_of(ctx).id)
        await self._edit(guild_of(ctx).id, enabled=not settings["enabled"])
        await ctx.reply(f"Starboard is now **{yes_no(not settings['enabled'])}**.")

    @starboard.command(name="self-star")
    @commands.has_guild_permissions(manage_guild=True)
    async def self_star(self, ctx: commands.Context[Bot], enabled: bool = commands.parameter(description="Count stars from the author")) -> None:
        """Allow or disallow members from starring their own messages."""
        await self._edit(guild_of(ctx).id, self_star=enabled)
        await ctx.reply(f"Self-starring is now **{yes_no(enabled)}**.")

    @starboard.command(name="nsfw")
    @commands.has_guild_permissions(manage_guild=True)
    async def nsfw(self, ctx: commands.Context[Bot], enabled: bool = commands.parameter(description="Let NSFW channels appear")) -> None:
        """Allow or disallow messages from NSFW channels (their media is spoilered)."""
        await self._edit(guild_of(ctx).id, allow_nsfw=enabled)
        await ctx.reply(f"NSFW messages are now **{yes_no(enabled)}**.")

    @starboard.command(name="max-age")
    @commands.has_guild_permissions(manage_guild=True)
    async def max_age(
        self,
        ctx: commands.Context[Bot],
        days: Annotated[int, commands.Range[int, 0, 3650]] = commands.parameter(description="0 means no limit"),
    ) -> None:
        """Ignore stars on messages older than this many days (entries already on the board keep updating)."""
        await self._edit(guild_of(ctx).id, max_age_days=days)
        await ctx.reply(f"Messages older than **{days}** days can no longer be added." if days else "There is no age limit anymore.")

    async def _change_list(self, ctx: commands.Context[Bot], field: str, value: int, *, add: bool) -> bool:
        """Your config stores whole lists, so this is read, change, write. ``False`` if nothing changed."""
        guild_id = guild_of(ctx).id
        self._settings_cache.pop(guild_id, None)
        items: list[int] = list((await self.get_settings(guild_id))[field])
        if (value in items) == add:
            return False
        items.append(value) if add else items.remove(value)
        await self._edit(guild_id, **{field: items})
        return True

    @starboard.group(name="ignore", invoke_without_command=True)
    async def ignore(self, ctx: commands.Context[Bot]) -> None:
        """List channels that are excluded from the starboard."""
        settings = await self.get_settings(guild_of(ctx).id)
        channels = " ".join(f"<#{channel_id}>" for channel_id in settings["ignored_channels"]) or "No ignored channels."
        await ctx.reply(view=panel("Ignored channels", channels), allowed_mentions=NO_MENTIONS)

    @ignore.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def ignore_add(
        self,
        ctx: commands.Context[Bot],
        channel: discord.TextChannel = commands.parameter(description="Channel to exclude"),  # noqa: B008
    ) -> None:
        """Exclude a channel from the starboard."""
        changed = await self._change_list(ctx, "ignored_channels", channel.id, add=True)
        await ctx.reply(f"{channel.mention} is now ignored." if changed else f"{channel.mention} was already ignored.", allowed_mentions=NO_MENTIONS)

    @ignore.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def ignore_remove(
        self,
        ctx: commands.Context[Bot],
        channel: discord.TextChannel = commands.parameter(description="Channel to include again"),  # noqa: B008
    ) -> None:
        """Remove a channel from the exclusion list."""
        changed = await self._change_list(ctx, "ignored_channels", channel.id, add=False)
        await ctx.reply(
            f"{channel.mention} is no longer ignored." if changed else f"{channel.mention} was not ignored.", allowed_mentions=NO_MENTIONS
        )

    @starboard.group(name="blacklist", invoke_without_command=True)
    async def blacklist(self, ctx: commands.Context[Bot]) -> None:
        """List users whose messages cannot be starred."""
        settings = await self.get_settings(guild_of(ctx).id)
        users = " ".join(f"<@{user_id}>" for user_id in settings["ignored_users"]) or "Nobody is blacklisted."
        await ctx.reply(view=panel("Blacklisted users", users), allowed_mentions=NO_MENTIONS)

    @blacklist.command(name="add")
    @commands.has_guild_permissions(manage_guild=True)
    async def blacklist_add(
        self,
        ctx: commands.Context[Bot],
        user: discord.User = commands.parameter(description="User to blacklist"),  # noqa: B008
    ) -> None:
        """Prevent a user's messages from being starred."""
        changed = await self._change_list(ctx, "ignored_users", user.id, add=True)
        await ctx.reply(f"{user.mention} is blacklisted." if changed else f"{user.mention} was already blacklisted.", allowed_mentions=NO_MENTIONS)

    @blacklist.command(name="remove")
    @commands.has_guild_permissions(manage_guild=True)
    async def blacklist_remove(
        self,
        ctx: commands.Context[Bot],
        user: discord.User = commands.parameter(description="User to allow again"),  # noqa: B008
    ) -> None:
        """Remove a user from the blacklist."""
        changed = await self._change_list(ctx, "ignored_users", user.id, add=False)
        await ctx.reply(
            f"{user.mention} is no longer blacklisted." if changed else f"{user.mention} was not blacklisted.", allowed_mentions=NO_MENTIONS
        )

    async def _find_entry(self, ctx: commands.Context[Bot], text: str) -> StarboardEntry | None:
        message_id = parse_message_id(text)
        if message_id is None:
            return None
        db, guild_id = self.bot.database, guild_of(ctx).id
        return await db.get_starboard_entry(guild_id=guild_id, source_message_id=message_id) or await db.get_starboard_entry_by_board_message_id(
            guild_id=guild_id, board_message_id=message_id
        )

    @starboard.command(name="info", aliases=["show"])
    async def info(self, ctx: commands.Context[Bot], message: str = commands.parameter(description="Message ID or link")) -> None:
        """Show the star count and board status of a message."""
        entry = await self._find_entry(ctx, message)
        if entry is None:
            await ctx.reply("That message is not on the starboard.")
            return

        guild = guild_of(ctx)
        settings = await self.get_settings(guild.id)
        lines = [f"**Stars:** {entry.get('star_count', 0)}{DOT}**Author:** <@{entry['author_id']}>"]
        if entry.get("source_channel_id"):
            lines.append(f"**Original:** [jump]({message_url(guild.id, entry['source_channel_id'], entry['source_message_id'])})")
        if settings["channel_id"]:
            lines.append(f"**Board entry:** [jump]({message_url(guild.id, settings['channel_id'], entry['board_message_id'])})")
        if entry.get("created_at"):
            lines.append(f"**On the board since:** {discord.utils.format_dt(entry['created_at'], 'R')}")
        if entry.get("is_nsfw"):
            lines.append("**NSFW channel**")
        await ctx.reply(view=panel("Starboard entry", "\n".join(lines)), allowed_mentions=NO_MENTIONS)

    @starboard.command(name="top")
    async def top(self, ctx: commands.Context[Bot]) -> None:
        """Show the most-starred messages."""
        guild = guild_of(ctx)
        entries = sorted(
            await self.bot.database.get_starboard_entries_by_guild(guild.id), key=lambda entry: entry.get("star_count", 0), reverse=True
        )[:10]
        if not entries:
            await ctx.reply("Nothing on the starboard yet.")
            return

        settings = await self.get_settings(guild.id)
        lines = []
        for index, entry in enumerate(entries):
            channel_id = entry.get("source_channel_id")
            where = f"[message]({message_url(guild.id, channel_id, entry['source_message_id'])})" if channel_id else "message"
            lines.append(f"{rank(index)} **{entry.get('star_count', 0)}** {settings['emoji']}{DOT}{where}{DOT}<@{entry['author_id']}>")
        await ctx.reply(view=panel("Top messages", "\n".join(lines)), allowed_mentions=NO_MENTIONS)

    @starboard.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context[Bot]) -> None:
        """Show the most-starred members."""
        entries = await self.bot.database.get_starboard_entries_by_guild(guild_of(ctx).id)
        if not entries:
            await ctx.reply("Nothing on the starboard yet.")
            return

        stars: Counter[int] = Counter()
        posts: Counter[int] = Counter()
        for entry in entries:
            stars[entry["author_id"]] += entry.get("star_count", 0)
            posts[entry["author_id"]] += 1

        settings = await self.get_settings(guild_of(ctx).id)
        lines = [
            f"{rank(index)} <@{author_id}> - **{count}** {settings['emoji']} in {posts[author_id]} post(s)"
            for index, (author_id, count) in enumerate(stars.most_common(10))
        ]
        await ctx.reply(view=panel("Starboard leaderboard", "\n".join(lines)), allowed_mentions=NO_MENTIONS)

    @starboard.command(name="stats")
    async def stats(self, ctx: commands.Context[Bot]) -> None:
        """Show starboard statistics for this server."""
        entries = await self.bot.database.get_starboard_entries_by_guild(guild_of(ctx).id)
        total = sum(entry.get("star_count", 0) for entry in entries)
        best = max((entry.get("star_count", 0) for entry in entries), default=0)
        lines = [
            f"**Entries on the board:** {len(entries)}",
            f"**Stars across them:** {total}",
            f"**Most stars on one message:** {best}",
            f"**Queued updates right now:** {len(self._pending)}",
        ]
        if entries:
            totals: Counter[int] = Counter()
            for entry in entries:
                totals[entry["author_id"]] += entry.get("star_count", 0)
            author_id, count = totals.most_common(1)[0]
            lines.append(f"**Most starred member:** <@{author_id}> ({count} stars)")
        await ctx.reply(view=panel("Starboard statistics", "\n".join(lines)), allowed_mentions=NO_MENTIONS)

    @starboard.command(name="sync")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def sync(self, ctx: commands.Context[Bot]) -> None:
        """Recount recent entries from their live reactions and repair missing board messages."""
        guild = guild_of(ctx)
        entries = await self.bot.database.get_starboard_entries_by_guild(guild.id)
        entries.sort(key=lambda entry: entry.get("created_at") or 0, reverse=True)

        queued = skipped = 0
        for entry in entries[:SYNC_LIMIT]:
            if entry.get("source_channel_id"):
                self.enqueue(guild.id, entry["source_channel_id"], entry["source_message_id"], rebuild=True)
                queued += 1
            else:
                skipped += 1  # created before source_channel_id was stored, so the original cannot be located

        eta = math.ceil(queued / MAX_PER_FLUSH) * FLUSH_INTERVAL
        note = f" {skipped} older entries have no stored channel and were skipped." if skipped else ""
        await ctx.reply(f"Queued **{queued}** entries (newest first), about {eta} seconds.{note}")

    @starboard.command(name="export")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def export(self, ctx: commands.Context[Bot]) -> None:
        """Export the configuration and stored entries as JSON."""
        guild = guild_of(ctx)
        settings = await self.get_settings(guild.id)
        entries = (await self.bot.database.get_starboard_entries_by_guild(guild.id))[:EXPORT_LIMIT]
        data = json.dumps({"settings": settings, "entries": entries}, indent=2, default=str).encode()
        await ctx.reply("Here is your export.", file=discord.File(io.BytesIO(data), filename=f"starboard-{guild.id}.json"))


async def setup(bot: Bot) -> None:
    await bot.add_cog(Starboard(bot))
