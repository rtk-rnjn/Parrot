from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

from core.utils import BaseLayoutView, NoticeLayout, plural, truncate
from core.utils.paginator import PaginationLayout

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

EMBED_DESCRIPTION_LIMIT = 4096
MAX_LIST_LENGTH = 3800
MAX_WORDS = 25
MAX_BLOCKED = 25
MIN_WORD_LENGTH = 2
MAX_WORD_LENGTH = 50
NOTIFY_DELAY = 30.0
CONTEXT_MESSAGES = 3
MAIN_CONTENT_LIMIT = 1500
CONTEXT_CONTENT_LIMIT = 300
VIEW_TIMEOUT = 300
NO_MENTIONS = discord.AllowedMentions.none()


def _normalise(word: str) -> str:
    return " ".join(word.split()).lower()


def _safe(text: str) -> str:
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text))


def _compile(words: list[str]) -> re.Pattern[str] | None:
    cleaned = sorted({_normalise(w) for w in words if w.strip()}, key=len, reverse=True)
    if not cleaned:
        return None
    alternation = "|".join(re.escape(w) for w in cleaned)
    return re.compile(rf"(?<!\w)(?:{alternation})(?!\w)", re.IGNORECASE)


def _render(content: str, pattern: re.Pattern[str] | None) -> str:
    escape = discord.utils.escape_markdown
    if pattern is None:
        return escape(content)

    parts: list[str] = []
    last = 0
    for match in pattern.finditer(content):
        parts.append(escape(content[last : match.start()]))
        parts.append(f"**{escape(match.group(0))}**")
        last = match.end()
    parts.append(escape(content[last:]))
    return "".join(parts)


def _user_label(bot: Bot, user_id: int) -> str:
    user = bot.get_user(user_id)
    if user is None:
        return f"Unknown user ({user_id})"
    return f"{user.display_name} ({user.name})"


class AddWordsModal(discord.ui.Modal, title="Add trigger words"):
    words = discord.ui.TextInput(
        label="Words or phrases (one per line)",
        style=discord.TextStyle.paragraph,
        placeholder="python\nrelease notes",
        max_length=500,
    )

    def __init__(self, hub: HighlightHub) -> None:
        super().__init__()
        self.hub = hub

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        notice = await self.hub.cog.add_words(self.hub.guild_id, interaction.user.id, self.words.value)
        await interaction.response.send_message(view=notice, ephemeral=True)
        await self.hub.reload()


class RemoveWordsView(BaseLayoutView):
    def __init__(self, hub: HighlightHub, author: discord.Member | discord.User, words: list[str]) -> None:
        super().__init__(author, timeout=120)
        self.hub = hub

        self.select = discord.ui.Select(
            placeholder="Pick the words to remove",
            min_values=1,
            max_values=len(words),
            options=[discord.SelectOption(label=truncate(word, 100), value=word) for word in words],
        )
        self.select.callback = self.on_select
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("### Remove trigger words\nChoose the words you want to stop watching in this server."),
                discord.ui.ActionRow(self.select),
            )
        )

    async def on_select(self, interaction: discord.Interaction[Bot]) -> None:
        words = list(self.select.values)
        await self.hub.cog.remove_words(self.hub.guild_id, interaction.user.id, words)
        self.stop()
        await interaction.response.edit_message(view=NoticeLayout.success(f"Removed {plural(len(words)):trigger word}."))
        await self.hub.reload()


class BlockUsersView(BaseLayoutView):
    def __init__(self, hub: HighlightHub, author: discord.Member | discord.User) -> None:
        super().__init__(author, timeout=120)
        self.hub = hub

        self.select = discord.ui.UserSelect(placeholder="Pick the users to ignore", min_values=1, max_values=10)
        self.select.callback = self.on_select
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("### Block users\nTheir messages will never trigger your highlights, in any server."),
                discord.ui.ActionRow(self.select),
            )
        )

    async def on_select(self, interaction: discord.Interaction[Bot]) -> None:
        ids = [user.id for user in self.select.values if not user.bot and user.id != interaction.user.id]
        added = await self.hub.cog.block_users(interaction.user.id, ids)
        notice = NoticeLayout.success(f"Blocked {plural(added):user}.") if added else NoticeLayout.warning("There was nobody new to block.")
        self.stop()
        await interaction.response.edit_message(view=notice)
        await self.hub.reload()


class UnblockUsersView(BaseLayoutView):
    def __init__(self, hub: HighlightHub, author: discord.Member | discord.User, blocked: list[int]) -> None:
        super().__init__(author, timeout=120)
        self.hub = hub

        self.select = discord.ui.Select(
            placeholder="Pick the users to unblock",
            min_values=1,
            max_values=len(blocked),
            options=[
                discord.SelectOption(label=truncate(_user_label(hub.cog.bot, user_id), 100), value=str(user_id), description=str(user_id))
                for user_id in blocked
            ],
        )
        self.select.callback = self.on_select
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("### Unblock users\nTheir messages will be able to trigger your highlights again."),
                discord.ui.ActionRow(self.select),
            )
        )

    async def on_select(self, interaction: discord.Interaction[Bot]) -> None:
        ids = [int(value) for value in self.select.values]
        await self.hub.cog.unblock_users(interaction.user.id, ids)
        self.stop()
        await interaction.response.edit_message(view=NoticeLayout.success(f"Unblocked {plural(len(ids)):user}."))
        await self.hub.reload()


class HighlightHub(BaseLayoutView):
    def __init__(self, cog: Highlights, author: discord.Member | discord.User, guild_id: int) -> None:
        super().__init__(author, timeout=VIEW_TIMEOUT)
        self.cog = cog
        self.guild_id = guild_id
        self.words: dict[int, list[str]] = {}
        self.blocked: list[int] = []

    async def load(self) -> None:
        self.words, self.blocked = await asyncio.gather(
            self.cog.user_words(self.author.id),
            self.cog.blocked(self.author.id),
        )

    async def reload(self) -> None:
        await self.load()
        self.render()
        await self.update_message()

    def summary(self) -> str:
        total = sum(len(words) for words in self.words.values())
        here = len(self.words.get(self.guild_id, ()))

        if total:
            first = f"You have **{plural(total):trigger word}** across **{plural(len(self.words)):server}**, {here} of them in this server."
        else:
            first = "You don't have any trigger words yet. Press **Add words** to get started."

        second = f"You've blocked **{plural(len(self.blocked)):user}**." if self.blocked else "You haven't blocked anyone."
        return f"### \N{BELL} Highlights\n{first}\n{second}\n-# Your words stay private. Use the buttons to manage them."

    def render(self) -> None:
        self.clear_items()
        here = self.words.get(self.guild_id, [])

        add = discord.ui.Button(label="Add words", emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.success)
        add.callback = self.on_add

        remove = discord.ui.Button(label="Remove words", emoji="\N{HEAVY MINUS SIGN}", style=discord.ButtonStyle.secondary, disabled=not here)
        remove.callback = self.on_remove

        show = discord.ui.Button(label="My words", emoji="\N{SCROLL}", style=discord.ButtonStyle.secondary, disabled=not self.words)
        show.callback = self.on_show

        block = discord.ui.Button(
            label="Block users",
            emoji="\N{NO ENTRY SIGN}",
            style=discord.ButtonStyle.danger,
            disabled=len(self.blocked) >= MAX_BLOCKED,
        )
        block.callback = self.on_block

        unblock = discord.ui.Button(
            label="Unblock users", emoji="\N{WHITE HEAVY CHECK MARK}", style=discord.ButtonStyle.secondary, disabled=not self.blocked
        )
        unblock.callback = self.on_unblock

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(self.summary()),
                discord.ui.Separator(),
                discord.ui.ActionRow(add, remove, show),
                discord.ui.ActionRow(block, unblock),
                accent_colour=discord.Colour.blurple(),
            )
        )

    async def on_add(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(AddWordsModal(self))

    async def on_remove(self, interaction: discord.Interaction[Bot]) -> None:
        words = sorted(self.words.get(self.guild_id, []), key=str.casefold)[:MAX_WORDS]
        if not words:
            await interaction.response.send_message(view=NoticeLayout.info("You have no trigger words in this server."), ephemeral=True)
            return
        await interaction.response.send_message(view=RemoveWordsView(self, interaction.user, words), ephemeral=True)

    async def on_show(self, interaction: discord.Interaction[Bot]) -> None:
        if not self.words:
            await interaction.response.send_message(view=NoticeLayout.info("You have no trigger words yet."), ephemeral=True)
            return

        ordered = sorted(self.words.items(), key=lambda entry: entry[0] != self.guild_id)
        pages: list[list[discord.ui.Item]] = []
        for guild_id, words in ordered:
            guild = self.cog.bot.get_guild(guild_id)
            name = guild.name if guild else f"Unknown server ({guild_id})"
            lines = "\n".join(f"{index}. {_safe(word)}" for index, word in enumerate(sorted(words, key=str.casefold), start=1))
            pages.append([discord.ui.TextDisplay(truncate(f"**{_safe(name)}**\n{lines}", MAX_LIST_LENGTH))])

        view = PaginationLayout(
            interaction.user,
            header=discord.ui.TextDisplay("### Your trigger words"),
            footer=discord.ui.TextDisplay("-# Trigger words are set per server"),
            items=pages,
            hide_skip_button=True,
            hide_quit_button=True,
            timeout=VIEW_TIMEOUT,
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    async def on_block(self, interaction: discord.Interaction[Bot]) -> None:
        if len(self.blocked) >= MAX_BLOCKED:
            await interaction.response.send_message(view=NoticeLayout.warning(f"You can block at most {MAX_BLOCKED} users."), ephemeral=True)
            return
        await interaction.response.send_message(view=BlockUsersView(self, interaction.user), ephemeral=True)

    async def on_unblock(self, interaction: discord.Interaction[Bot]) -> None:
        if not self.blocked:
            await interaction.response.send_message(view=NoticeLayout.info("You haven't blocked anyone."), ephemeral=True)
            return
        await interaction.response.send_message(view=UnblockUsersView(self, interaction.user, self.blocked[:MAX_BLOCKED]), ephemeral=True)


class Highlights(commands.Cog):
    """Get a message from Bot when someone posts one of your trigger words."""

    help_emoji = "\N{BELL}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._patterns: dict[int, dict[int, re.Pattern[str]]] = {}
        self._ignored: dict[int, frozenset[int]] = {}
        self._activity: dict[tuple[int, int], float] = {}
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def cog_load(self) -> None:
        self._prune_activity.start()

    async def cog_unload(self) -> None:
        self._prune_activity.cancel()

    async def user_words(self, user_id: int) -> dict[int, list[str]]:
        rows = await self.bot.database.get_user_highlights_by_guild(user_id=user_id)
        return {guild_id: list(words) for guild_id, words in rows.items() if words}

    async def blocked(self, user_id: int) -> list[int]:
        ignored = await self.bot.database.get_user_highlight_ignored_users(user_id=user_id)
        return sorted(ignored or ())

    async def add_words(self, guild_id: int, user_id: int, raw: str) -> NoticeLayout:
        lines = [line for line in raw.splitlines() if line.strip()]
        words: list[str] = []
        for line in lines:
            word = _normalise(line)
            if MIN_WORD_LENGTH <= len(word) <= MAX_WORD_LENGTH and word not in words:
                words.append(word)

        if not words:
            return NoticeLayout.error(f"Trigger words must be {MIN_WORD_LENGTH}-{MAX_WORD_LENGTH} characters long.")

        existing = {_normalise(w) for w in await self.bot.database.get_user_highlights(guild_id=guild_id, user_id=user_id) or []}
        room = MAX_WORDS - len(existing)
        if room <= 0:
            return NoticeLayout.error(f"You can have at most {MAX_WORDS} trigger words in a server.")

        fresh = [word for word in words if word not in existing][:room]
        if not fresh:
            return NoticeLayout.warning("You already have those trigger words.")

        await self.bot.database.add_user_highlight(guild_id=guild_id, user_id=user_id, words=fresh)
        self._patterns.pop(guild_id, None)

        skipped = len(lines) - len(fresh)
        body = f"Added {plural(len(fresh)):trigger word}."
        if skipped:
            body += f" Skipped {skipped} (duplicates, bad length or over the limit of {MAX_WORDS})."
        return NoticeLayout.success(body)

    async def remove_words(self, guild_id: int, user_id: int, words: list[str]) -> None:
        await self.bot.database.remove_user_highlight(guild_id=guild_id, user_id=user_id, words=words)
        self._patterns.pop(guild_id, None)

    async def block_users(self, user_id: int, targets: list[int]) -> int:
        current = set(await self.blocked(user_id))
        fresh = [target for target in dict.fromkeys(targets) if target not in current][: max(0, MAX_BLOCKED - len(current))]
        for target in fresh:
            await self.bot.database.add_user_highlight_ignored_user(user_id=user_id, ignored_user_id=target)
        self._ignored.pop(user_id, None)
        return len(fresh)

    async def unblock_users(self, user_id: int, targets: list[int]) -> None:
        for target in targets:
            await self.bot.database.remove_user_highlight_ignored_user(user_id=user_id, ignored_user_id=target)
        self._ignored.pop(user_id, None)

    async def _guild_patterns(self, guild_id: int) -> dict[int, re.Pattern[str]]:
        cached = self._patterns.get(guild_id)
        if cached is None:
            rows = await self.bot.database.get_guild_highlights(guild_id=guild_id)
            cached = {}
            for user_id, words in rows.items():
                if pattern := _compile(list(words)):
                    cached[user_id] = pattern
            self._patterns[guild_id] = cached
        return cached

    async def _ignored_users(self, user_id: int) -> frozenset[int]:
        if user_id not in self._ignored:
            self._ignored[user_id] = frozenset(await self.blocked(user_id))
        return self._ignored[user_id]

    @tasks.loop(minutes=1)
    async def _prune_activity(self) -> None:
        cutoff = time.monotonic() - NOTIFY_DELAY * 2
        self._activity = {key: seen for key, seen in self._activity.items() if seen >= cutoff}

    @commands.guild_only()
    @commands.command(name="highlight", aliases=["highlights", "hl"])
    async def highlight(self, ctx: commands.Context[Bot]) -> None:
        """Manage your highlights.

        Shows a summary of your trigger words and blocked users. Use the buttons to add or remove
        words, see them privately, and choose users whose messages should never trigger you.
        """
        assert ctx.guild is not None

        hub = HighlightHub(self, ctx.author, ctx.guild.id)
        await hub.load()
        hub.render()
        hub.message = await ctx.reply(view=hub, allowed_mentions=NO_MENTIONS)

    def _mark_active(self, channel_id: int, user_id: int) -> None:
        self._activity[(channel_id, user_id)] = time.monotonic()

    @commands.Cog.listener("on_message")
    async def track_message_activity(self, message: discord.Message) -> None:
        self._mark_active(message.channel.id, message.author.id)

    @commands.Cog.listener()
    async def on_typing(self, channel: discord.abc.Messageable, user: discord.User | discord.Member, _: object) -> None:
        channel_id = getattr(channel, "id", None)
        if channel_id is not None:
            self._mark_active(channel_id, user.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        self._mark_active(payload.channel_id, payload.user_id)

    @commands.Cog.listener("on_message")
    async def find_highlights(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or not message.content:
            return

        patterns = await self._guild_patterns(message.guild.id)
        if not patterns:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        mentioned = {user.id for user in message.mentions}

        for user_id, pattern in patterns.items():
            if user_id == message.author.id or user_id in mentioned:
                continue

            match = pattern.search(message.content)
            if match is None:
                continue

            member = message.guild.get_member(user_id)
            if member is None or member.bot:
                continue

            perms = message.channel.permissions_for(member)
            if not (perms.view_channel and perms.read_message_history):
                continue

            if message.author.id in await self._ignored_users(user_id):
                continue

            self.bot.dispatch("highlight", message, member, pattern, match.group(0))

    @commands.Cog.listener("on_highlight")
    async def deliver_highlight(
        self,
        message: discord.Message,
        member: discord.Member,
        pattern: re.Pattern[str],
        word: str,
    ) -> None:
        sent_at = time.monotonic()

        if member.status is not discord.Status.offline:
            await asyncio.sleep(NOTIFY_DELAY)
            last_seen = self._activity.get((message.channel.id, member.id))
            if last_seen is not None and last_seen >= sent_at:
                return

        await self._send_highlight_notification(message, member, pattern, word)

    async def _send_highlight_notification(
        self,
        message: discord.Message,
        member: discord.Member,
        pattern: re.Pattern[str],
        word: str,
    ) -> None:
        if TYPE_CHECKING:
            assert message.guild is not None
            assert isinstance(message.channel, discord.abc.GuildChannel)

        header = f"In {message.channel.mention} for `{message.guild.name}` you were highlighted with the word **{discord.utils.escape_markdown(word)}**\n\n"

        lines = [
            f"{discord.utils.format_dt(message.created_at, style='R')} `@{message.author!s}`: "  # noqa: ISC004
            f"{_render(truncate(message.content, MAIN_CONTENT_LIMIT), pattern)}"
        ]

        if message.channel.permissions_for(message.guild.me).read_message_history:
            try:
                context: list[str] = []
                async for previous in message.channel.history(limit=CONTEXT_MESSAGES, before=message):
                    if not previous.content:
                        continue
                    context.append(
                        f"{discord.utils.format_dt(previous.created_at, style='R')} `@{previous.author!s}`: "
                        f"{_render(truncate(previous.content, CONTEXT_CONTENT_LIMIT), pattern)}"
                    )
                for text in context:
                    if len(header) + sum(map(len, lines)) + len(text) + len(lines) <= EMBED_DESCRIPTION_LIMIT:
                        lines.insert(0, text)
            except discord.HTTPException:
                pass

        embed = (
            discord.Embed(description=truncate(header + "\n".join(lines), EMBED_DESCRIPTION_LIMIT), timestamp=message.created_at)
            .set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            .set_footer(text="Triggered")
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump to message", url=message.jump_url))

        try:
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            _log.warning("Could not send highlight notification to %s", member)
        except discord.HTTPException:
            _log.exception("Failed to send highlight notification to %s", member)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Highlights(bot))
