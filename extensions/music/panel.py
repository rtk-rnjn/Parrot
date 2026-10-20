from __future__ import annotations

import asyncio
import contextlib
import enum
import logging
import math
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import discord

from core.utils import NoticeLayout as Notice
from core.utils import format_clock_duration, plural, truncate

from .models import PRESETS, LoopMode, Song
from .ui import describe_song, format_progress

if TYPE_CHECKING:
    from discord.ext.commands import Context

    from core import Bot

    from .player import MusicPlayer, VoteResult

__all__ = ("MusicPanel", "SearchView", "Tab")

_log = logging.getLogger(__name__)

QUEUE_PAGE_SIZE = 5
SETTLE_SECONDS = 1.5  # a skip is ignored this soon after a track change: it was aimed at the previous track
TICK_SECONDS = 15  # how often the progress bar is refreshed while playing
VOLUME_STEP = 10

LOOP_EMOJI = {
    LoopMode.off: "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
    LoopMode.track: "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}",
    LoopMode.queue: "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
}

type Handler = Callable[[discord.Member], Awaitable[Notice | None]]


class Tab(enum.Enum):
    player = ("Player", "\N{MUSICAL NOTE}")
    queue = ("Queue", "\N{SCROLL}")
    filters = ("Filters", "\N{CONTROL KNOBS}\N{VARIATION SELECTOR-16}")
    settings = ("Settings", "\N{GEAR}\N{VARIATION SELECTOR-16}")

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def emoji(self) -> str:
        return self.value[1]


def _vote_notice(result: VoteResult, pending: str) -> Notice | None:
    """Nothing to say when the vote passed (the panel itself shows the result); a short note when it is pending."""
    if result.passed:
        return None
    return Notice.info(pending, footer=f"{result.votes}/{result.required} votes needed.")


class MusicPanel(discord.ui.LayoutView):
    """One live control panel per guild, owned by the player.

    Because there is exactly one panel and its state is always rebuilt from the player, there is nothing to keep
    in sync between views. Concurrent clicks are handled by ``run``: the first one takes the player's lock, any
    click that arrives while it is busy is turned away, and the panel is re-rendered once it finishes.
    """

    def __init__(self, player: MusicPlayer) -> None:
        super().__init__(timeout=None)
        self.player = player
        self.tab = Tab.player
        self.page = 0
        self.message: discord.Message | None = None
        self.closed = False
        self._ticker: asyncio.Task[None] | None = None
        self._build()

    async def open(self, tab: Tab | None = None) -> None:
        """Show the panel on ``tab`` at the bottom of the channel (used by commands)."""
        if tab is not None:
            self.tab, self.page = tab, 0
        await self.present(force=True)

    async def present(self, *, force: bool = False) -> None:
        """Edit the panel in place when it is the newest message, otherwise re-send it at the bottom."""
        if self.closed:
            return

        self._build()
        channel = self.player.text_channel
        if channel is None:
            return

        message = self.message
        newest = (
            message is not None and message.channel.id == getattr(channel, "id", None) and getattr(channel, "last_message_id", None) == message.id
        )
        if message is not None and newest and not force:
            await self.refresh()
            return

        if message is not None:
            await message.delete(delay=0)
            self.message = None

        try:
            self.message = await channel.send(view=self, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            _log.warning("Could not send the music panel.", exc_info=True)
            return

        if self._ticker is None:
            self._ticker = asyncio.ensure_future(self._tick())

    async def refresh(self) -> None:
        if self.closed:
            return

        self._build()
        if self.message is None:
            return
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            self.message = None  # deleted by someone; the next track change re-sends it
        except discord.HTTPException:
            _log.warning("Could not edit the music panel.", exc_info=True)

    async def close(self, reason: str) -> None:
        if self.closed:
            return
        self.closed = True

        if self._ticker is not None:
            self._ticker.cancel()

        self.clear_items()
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## \N{MUSICAL NOTE} Music session ended\n{reason}"),
                accent_colour=discord.Colour.dark_grey(),
            )
        )
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)
        self.stop()

    async def _tick(self) -> None:
        while not self.closed:
            await asyncio.sleep(TICK_SECONDS)
            player = self.player
            if self.tab is Tab.player and player.song is not None and not player.paused and not player.lock.locked():
                await self.refresh()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        player = self.player
        user = interaction.user
        if isinstance(user, discord.Member) and user.voice is not None and user.voice.channel == player.channel:
            return True

        where = player.channel.mention if player.channel is not None else "the voice channel"
        await interaction.response.send_message(view=Notice.warning(f"Join {where} to use these controls."), ephemeral=True)
        return False

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any]) -> None:
        _log.exception("Music panel error on %r", item, exc_info=error)

    async def run(self, interaction: discord.Interaction, handler: Handler) -> None:
        """Run ``handler`` as the one active action, or turn the click away if another action is in flight."""
        player = self.player
        if self.closed or not player.usable:
            await interaction.response.send_message(view=Notice.info("This session has ended."), ephemeral=True)
            return

        # `locked()` and `acquire()` are back to back with no await between them, so no other click can slip in.
        if player.lock.locked():
            await interaction.response.send_message(view=Notice.info("Another control is being handled. Give it a second."), ephemeral=True)
            return

        notice: Notice | None = None
        await player.lock.acquire()
        try:
            await interaction.response.defer()
            try:
                notice = await handler(interaction.user)  # type: ignore[arg-type]
            except Exception:  # pylint: disable=broad-exception-caught
                _log.exception("Music panel action failed.")
                notice = Notice.error("Something went wrong with that action.")
        finally:
            player.lock.release()

        await self.refresh()
        if notice is not None:
            await interaction.followup.send(view=notice, ephemeral=True)

    def _button(
        self,
        custom_id: str,
        handler: Handler,
        *,
        label: str | None = None,
        emoji: str | None = None,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        disabled: bool = False,
    ) -> discord.ui.Button[Any]:
        # Stable custom ids: a click on a slightly stale render still reaches the current handler, and the
        # library's view store does not grow with every re-render.
        button: discord.ui.Button[Any] = discord.ui.Button(custom_id=custom_id, label=label, emoji=emoji, style=style, disabled=disabled)

        async def callback(interaction: discord.Interaction) -> None:
            await self.run(interaction, handler)

        button.callback = callback
        return button

    def _dj_only(self, member: discord.Member) -> Notice | None:
        if self.player.is_dj(member):
            return None
        dj = self.player.dj
        return Notice.error(f"Only {dj.display_name if dj is not None else 'the DJ'} can do that.")

    def _build(self) -> None:
        self.clear_items()
        builders = {
            Tab.player: self._player_tab,
            Tab.queue: self._queue_tab,
            Tab.filters: self._filters_tab,
            Tab.settings: self._settings_tab,
        }
        children = [*builders[self.tab](), discord.ui.Separator(), self._tab_row()]
        self.add_item(discord.ui.Container(*children, accent_colour=self._accent()))

    def _accent(self) -> discord.Colour:
        player = self.player
        if player.song is None:
            return discord.Colour.dark_grey()
        return discord.Colour.gold() if player.paused else discord.Colour.green()

    def _tab_row(self) -> discord.ui.ActionRow[Any]:
        buttons = []
        for tab in Tab:
            current = tab is self.tab
            button: discord.ui.Button[Any] = discord.ui.Button(
                custom_id=f"mp:tab:{tab.name}",
                label=tab.label,
                emoji=tab.emoji,
                style=discord.ButtonStyle.primary if current else discord.ButtonStyle.secondary,
                disabled=current,
            )
            button.callback = self._tab_callback(tab)  # type: ignore[method-assign]
            buttons.append(button)
        return discord.ui.ActionRow(*buttons)

    def _tab_callback(self, tab: Tab) -> Callable[[discord.Interaction], Awaitable[None]]:
        async def callback(interaction: discord.Interaction) -> None:
            self.tab, self.page = tab, 0
            self._build()
            await interaction.response.edit_message(view=self)

        return callback

    def _player_tab(self) -> list[discord.ui.Item[Any]]:
        player, song = self.player, self.player.song
        if song is None:
            return [
                discord.ui.TextDisplay("## Nothing playing\nQueue something with `play <url or search>`."),
                discord.ui.TextDisplay(f"-# {plural(len(player.queue)):track} queued \N{MIDDLE DOT} via {player.backend_name}"),
            ]

        state = "\N{DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16} **Paused**\n" if player.paused else ""
        body = f"## Now Playing\n{describe_song(song)}\n{state}{format_progress(player.position_ms, song.length, is_stream=song.is_stream)}"
        head: discord.ui.Item[Any] = discord.ui.TextDisplay(body)
        if song.thumbnail:
            head = discord.ui.Section(body, accessory=discord.ui.Thumbnail(song.thumbnail))

        requester = discord.utils.escape_markdown(song.requester.display_name) if song.requester is not None else "unknown"
        extras = []
        if player.loop_mode is not LoopMode.off:
            extras.append(f"Loop: {player.loop_mode.value}")
        if player.preset_key in PRESETS:
            extras.append(f"{PRESETS[player.preset_key].emoji} {PRESETS[player.preset_key].label}")
        meta = " \N{MIDDLE DOT} ".join(
            [f"Requested by {requester}", f"{plural(len(player.queue)):track} queued", f"Vol {player.volume_level}%", *extras]
        )

        return [head, discord.ui.TextDisplay(f"-# {meta}"), discord.ui.Separator(), self._controls_row()]

    def _controls_row(self) -> discord.ui.ActionRow[Any]:
        player = self.player
        paused = player.paused
        skip_votes = player.vote_count("skip")
        loop = player.loop_mode

        return discord.ui.ActionRow(
            self._button(
                "mp:pause",
                self._toggle_pause,
                label="Resume" if paused else "Pause",
                emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}" if paused else "\N{DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                style=discord.ButtonStyle.success if paused else discord.ButtonStyle.secondary,
            ),
            self._button(
                "mp:skip",
                self._skip,
                label=f"Skip {skip_votes}/{player.required_votes}" if skip_votes else "Skip",
                emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
            ),
            self._button(
                "mp:stop", self._stop, label="Stop", emoji="\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.danger
            ),
            self._button(
                "mp:loop",
                self._cycle_loop,
                emoji=LOOP_EMOJI[loop],
                style=discord.ButtonStyle.secondary if loop is LoopMode.off else discord.ButtonStyle.primary,
            ),
            self._button("mp:shuffle", self._shuffle, emoji="\N{TWISTED RIGHTWARDS ARROWS}"),
        )

    def _queue_tab(self) -> list[discord.ui.Item[Any]]:
        player = self.player
        items = list(player.queue)
        pages = max(1, math.ceil(len(items) / QUEUE_PAGE_SIZE))
        self.page = min(self.page, pages - 1)
        start = self.page * QUEUE_PAGE_SIZE
        chunk = items[start : start + QUEUE_PAGE_SIZE]

        body = (
            "\n".join(f"`{start + offset}.` {describe_song(song)}" for offset, song in enumerate(chunk, start=1)) if chunk else "The queue is empty."
        )
        now = f"-# Now playing: {describe_song(player.song)}" if player.song is not None else "-# Nothing is playing."
        children: list[discord.ui.Item[Any]] = [
            discord.ui.TextDisplay(f"## Queue\n{plural(len(items)):track} \N{MIDDLE DOT} {format_clock_duration(player.queue.total_length)}"),
            discord.ui.TextDisplay(body),
            discord.ui.TextDisplay(now),
        ]

        if chunk:
            select: discord.ui.Select[Any] = discord.ui.Select(
                custom_id="mp:remove",
                placeholder="Remove a track\N{HORIZONTAL ELLIPSIS}",
                options=[
                    discord.SelectOption(label=truncate(f"{start + offset}. {song.title}", 100), value=str(song.uid))
                    for offset, song in enumerate(chunk, start=1)
                ],
            )

            async def on_remove(interaction: discord.Interaction) -> None:
                uid = int(select.values[0])
                await self.run(interaction, lambda member: self._remove(member, uid))

            select.callback = on_remove
            children.append(discord.ui.ActionRow(select))

        previous: discord.ui.Button[Any] = discord.ui.Button(
            custom_id="mp:prev", emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", disabled=self.page == 0
        )
        following: discord.ui.Button[Any] = discord.ui.Button(
            custom_id="mp:next", emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}", disabled=self.page >= pages - 1
        )
        indicator: discord.ui.Button[Any] = discord.ui.Button(custom_id="mp:page", label=f"{self.page + 1}/{pages}", disabled=True)
        previous.callback = self._page_callback(-1)  # type: ignore[method-assign]
        following.callback = self._page_callback(1)  # type: ignore[method-assign]

        children.append(
            discord.ui.ActionRow(
                previous,
                indicator,
                following,
                self._button("mp:q-shuffle", self._shuffle, emoji="\N{TWISTED RIGHTWARDS ARROWS}"),
                self._button("mp:clear", self._clear, emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.danger),
            )
        )
        return children

    def _page_callback(self, step: int) -> Callable[[discord.Interaction], Awaitable[None]]:
        async def callback(interaction: discord.Interaction) -> None:
            self.page = max(0, self.page + step)
            self._build()
            await interaction.response.edit_message(view=self)

        return callback

    def _filters_tab(self) -> list[discord.ui.Item[Any]]:
        player = self.player
        active = PRESETS.get(player.preset_key) if player.preset_key else None
        status = f"{active.emoji} **{active.label}**: {active.description}" if active is not None else "No filter active."
        how = "Applied by Lavalink." if player.backend_name == "Lavalink" else "Applied through FFmpeg (fallback backend)."

        options = [discord.SelectOption(label="No filter", value="off", emoji="\N{NO ENTRY SIGN}", default=active is None)]
        options += [
            discord.SelectOption(label=preset.label, value=preset.key, description=preset.description, emoji=preset.emoji, default=preset is active)
            for preset in PRESETS.values()
        ]
        select: discord.ui.Select[Any] = discord.ui.Select(
            custom_id="mp:filter", placeholder="Choose a filter\N{HORIZONTAL ELLIPSIS}", options=options
        )

        async def on_pick(interaction: discord.Interaction) -> None:
            value = select.values[0]
            await self.run(interaction, lambda member: self._set_filter(member, value))

        select.callback = on_pick
        return [
            discord.ui.TextDisplay(f"## Filters\n{status}"),
            discord.ui.TextDisplay(f"-# {how} Changes restart the current track at the same position."),
            discord.ui.ActionRow(select),
        ]

    def _settings_tab(self) -> list[discord.ui.Item[Any]]:
        player = self.player
        channel = player.channel
        dj = player.dj
        node = getattr(getattr(player, "node", None), "identifier", None)
        backend = f"**{player.backend_name}**" + (f" (node `{node}`)" if node else "")

        lines = [
            "## Settings",
            f"Backend: {backend}",
            f"Voice channel: {channel.mention if channel is not None else 'none'}",
            f"DJ: {dj.display_name if dj is not None else 'nobody'} \N{MIDDLE DOT} {plural(len(player.listeners)):listener}",
        ]

        loop_select: discord.ui.Select[Any] = discord.ui.Select(
            custom_id="mp:loop-select",
            placeholder="Loop mode",
            options=[discord.SelectOption(label=f"Loop: {mode.value}", value=mode.name, default=mode is player.loop_mode) for mode in LoopMode],
        )

        async def on_loop(interaction: discord.Interaction) -> None:
            value = loop_select.values[0]
            await self.run(interaction, lambda member: self._set_loop(member, LoopMode[value]))

        loop_select.callback = on_loop

        volume_label: discord.ui.Button[Any] = discord.ui.Button(custom_id="mp:vol-label", label=f"{player.volume_level}%", disabled=True)
        return [
            discord.ui.TextDisplay("\n".join(lines)),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                self._button("mp:vol-down", lambda member: self._volume(member, -VOLUME_STEP), emoji="\N{SPEAKER WITH ONE SOUND WAVE}"),
                volume_label,
                self._button("mp:vol-up", lambda member: self._volume(member, VOLUME_STEP), emoji="\N{SPEAKER WITH THREE SOUND WAVES}"),
                self._button("mp:leave", self._leave, label="Disconnect", style=discord.ButtonStyle.danger),
            ),
            discord.ui.ActionRow(loop_select),
        ]

    async def _toggle_pause(self, member: discord.Member) -> Notice | None:
        player = self.player
        if player.song is None:
            return Notice.info("Nothing is playing right now.")
        if player.paused:
            return _vote_notice(await player.vote_resume(member), "Your vote to resume has been counted.")
        return _vote_notice(await player.vote_pause(member), "Your vote to pause has been counted.")

    async def _skip(self, member: discord.Member) -> Notice | None:
        player = self.player
        if player.song is None:
            return Notice.info("Nothing is playing right now.")
        if time.monotonic() - player.last_change < SETTLE_SECONDS:
            return Notice.info("The track just changed. Try again if you still want to skip it.")
        return _vote_notice(await player.vote_skip(member), "Your vote to skip has been counted.")

    async def _stop(self, member: discord.Member) -> Notice | None:
        return _vote_notice(await self.player.vote_stop(member), "Your vote to stop has been counted.")

    async def _shuffle(self, member: discord.Member) -> Notice | None:
        if len(self.player.queue) < 2:
            return Notice.info("There is nothing to shuffle.")
        return _vote_notice(await self.player.vote_shuffle(member), "Your vote to shuffle has been counted.")

    async def _cycle_loop(self, member: discord.Member) -> Notice | None:
        notice = self._dj_only(member)
        if notice is not None:
            return notice
        self.player.loop_mode = self.player.loop_mode.next
        return None

    async def _set_loop(self, member: discord.Member, mode: LoopMode) -> Notice | None:
        notice = self._dj_only(member)
        if notice is not None:
            return notice
        self.player.loop_mode = mode
        return None

    async def _volume(self, member: discord.Member, delta: int) -> Notice | None:
        notice = self._dj_only(member)
        if notice is not None:
            return notice

        await self.player.set_volume_level(self.player.volume_level + delta)
        return None

    async def _set_filter(self, member: discord.Member, value: str) -> Notice | None:
        notice = self._dj_only(member)
        if notice is not None:
            return notice
        try:
            await self.player.set_preset(None if value == "off" else value)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _log.warning("Could not apply filter %r: %s", value, exc)
            await self.player.set_preset(None) if self.player.preset_key else None
            return Notice.error("That filter could not be applied.", footer=str(exc)[:200])
        return None

    async def _remove(self, member: discord.Member, uid: int) -> Notice | None:
        player = self.player
        index = next((position for position, song in enumerate(player.queue) if song.uid == uid), None)
        if index is None:
            return Notice.info("That track is no longer in the queue.")

        requester = player.queue[index].requester
        if not (player.is_dj(member) or (requester is not None and requester.id == member.id)):
            return Notice.error("Only the DJ or the person who requested it can remove that.")

        player.queue.remove(index)
        return None

    async def _clear(self, member: discord.Member) -> Notice | None:
        notice = self._dj_only(member)
        if notice is not None:
            return notice
        self.player.queue.clear()
        return None

    async def _leave(self, member: discord.Member) -> Notice | None:
        notice = self._dj_only(member)
        if notice is not None:
            return notice
        await self.player.teardown(f"Disconnected by {member.display_name}.")
        return None


class SearchView(discord.ui.LayoutView):
    """A one-shot picker: choose up to five results from a search. Only the person who searched can use it."""

    def __init__(self, ctx: Context[Bot], player: MusicPlayer, songs: list[Song]) -> None:
        super().__init__(timeout=60)
        self.ctx = ctx
        self.player = player
        self.songs = songs
        self.message: discord.Message | None = None

        self.select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="Pick up to 5 tracks\N{HORIZONTAL ELLIPSIS}",
            min_values=1,
            max_values=min(5, len(songs)),
            options=[
                discord.SelectOption(
                    label=truncate(f"{index}. {song.title}", 100),
                    description=truncate(f"{song.author} \N{MIDDLE DOT} {format_clock_duration(song.length)}", 100),
                    value=str(index - 1),
                )
                for index, song in enumerate(songs, start=1)
            ],
        )
        self.select.callback = self._picked
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("## Search results\nPick what you want queued."),
                discord.ui.ActionRow(self.select),
                accent_colour=discord.Colour.blurple(),
            )
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(view=Notice.warning("Only the person who searched can pick."), ephemeral=True)
        return False

    async def _picked(self, interaction: discord.Interaction) -> None:
        chosen = [self.songs[int(value)] for value in self.select.values]
        self.stop()
        await interaction.response.edit_message(view=Notice.success(f"Queued {plural(len(chosen)):track}."))

        if not self.player.usable:
            return
        self.player.text_channel = self.ctx.channel
        async with self.player.lock:
            await self.player.enqueue(chosen)

    async def on_timeout(self) -> None:
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=Notice.info("Search timed out."))
