"""Shared infrastructure for the card games.

A game is an async loop (``CardGame.play``). Human turns await :meth:`CardGame.decide`, which shows
controls in a private "My Hand" panel; bots answer through the ``ai`` callback after a short delay.
Card faces come from ``blackjack_table.card_store``, the only place that imports ``ImageStore``.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
from contextlib import suppress
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

import discord
from PIL import Image, ImageDraw

from core.utils.formats import truncate
from core.utils.views import NoticeLayout
from extensions.supercell.render import font

from .blackjack_table import BACK, GOLD, KINDS, _felt, _sprite, card_store, card_url

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from discord.ext import commands

    from core import Bot

    from .blackjack_table import Kind

__all__ = (
    "RANK_ORDER",
    "Action",
    "ButtonSpec",
    "CardGame",
    "GameEnded",
    "Lobby",
    "PromptSpec",
    "Seat",
    "SeatView",
    "SelectSpec",
    "TableView",
    "label",
    "new_deck",
    "rank_of",
    "sort_hand",
    "suit_of",
)

_log = logging.getLogger(__name__)

type Action = tuple[str, tuple[int, ...]]

RANK_ORDER = "23456789" + "0JQKA"
SUIT_SORT = "SHCD"
SUIT_SYMBOLS = {
    "S": "\N{BLACK SPADE SUIT}",
    "H": "\N{BLACK HEART SUIT}",
    "D": "\N{BLACK DIAMOND SUIT}",
    "C": "\N{BLACK CLUB SUIT}",
}
BOT_NAMES = ("Raj", "Simran", "Babu", "Meera", "Vikram", "Anita", "Kabir", "Isha")
NO_MENTIONS = discord.AllowedMentions.none()
SELECT_PAGE = 25  # Discord allows at most 25 options in one select menu


def rank_of(card: str) -> int:
    return RANK_ORDER.index(card[0]) + 2


def suit_of(card: str) -> str:
    return card[1]


def label(card: str) -> str:
    return f"{'10' if card[0] == '0' else card[0]}{SUIT_SYMBOLS[card[1]]}"


def new_deck(decks: int = 1) -> list[str]:
    cards = [f"{rank}{suit}" for _ in range(decks) for suit in "CDHS" for rank in RANK_ORDER]
    random.shuffle(cards)
    return cards


def sort_hand(cards: list[str]) -> list[str]:
    return sorted(cards, key=lambda c: (SUIT_SORT.index(c[1]), rank_of(c)))


class GameEnded(Exception):
    """Raised when the game message disappears."""


@dataclass(eq=False, slots=True)
class Seat:
    name: str
    user: discord.User | discord.Member | None = None
    afk: int = 0

    @property
    def is_bot(self) -> bool:
        return self.user is None or self.afk >= 2

    @property
    def tag(self) -> str:
        return f"\N{ROBOT FACE} {self.name}" if self.user is None else self.name

    @property
    def mention(self) -> str:
        return f"<@{self.user.id}>" if self.user is not None else self.name


@dataclass(frozen=True, slots=True)
class SeatView:
    name: str
    sub: str = ""
    cards: int = 0
    shown: tuple[str, ...] = ()
    played: str | None = None
    active: bool = False
    dim: bool = False
    badge: str | None = None
    badge_kind: Kind = "neutral"


@dataclass(frozen=True, slots=True)
class TableView:
    seats: Sequence[SeatView]
    centre: tuple[str, ...] = ()
    stack: int = 0
    note: str = ""


@dataclass(slots=True)
class ButtonSpec:
    id: str
    label: str
    style: discord.ButtonStyle = discord.ButtonStyle.secondary
    emoji: str | None = None
    disabled: bool = False


@dataclass(slots=True)
class SelectSpec:
    placeholder: str
    minimum: int
    maximum: int
    options: list[tuple[int, str]]
    confirm_label: str = "Confirm"


@dataclass(slots=True)
class PromptSpec:
    cards: list[str]
    caption: str
    hidden: bool = False
    select: SelectSpec | None = None
    buttons: list[ButtonSpec] = field(default_factory=list)
    local: dict[str, Callable[[], None]] = field(default_factory=dict)
    dimmed: set[int] = field(default_factory=set)


@dataclass(slots=True)
class Pending:
    seat: Seat
    build: Callable[[], PromptSpec]
    validate: Callable[[Action], str | None]
    future: asyncio.Future[Action]


def _png(img: Image.Image) -> bytes:
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


def _pill(draw: ImageDraw.ImageDraw, cx: int, top: int, text: str, kind: Kind = "dark", size: int = 16) -> None:
    face = font(size)
    width = int(draw.textlength(text, font=face)) + 24
    height = size + 14
    draw.rounded_rectangle((cx - width // 2, top, cx + width // 2, top + height), height // 2, fill=KINDS[kind])
    ink = (45, 28, 0, 255) if kind == "gold" else (255, 255, 255, 255)
    draw.text((cx, top + height // 2), text, font=face, fill=ink, anchor="mm")


def _tint(img: Image.Image, box: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int, int], outline=None, width: int = 0) -> None:
    """Blend a translucent rounded rectangle onto ``img`` (drawing straight onto an RGBA image would overwrite the pixels)."""
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((0, 0, x1 - x0, y1 - y0), radius, fill=fill, outline=outline, width=width)
    img.alpha_composite(layer, (x0, y0))


def _pill_row(draw: ImageDraw.ImageDraw, cx: int, top: int, items: list[tuple[str, Kind]], size: int) -> None:
    face = font(size)
    widths = [int(draw.textlength(text, font=face)) + 24 for text, _ in items]
    x = cx - (sum(widths) + 6 * (len(items) - 1)) // 2
    for (text, kind), width in zip(items, widths, strict=True):
        _pill(draw, x + width // 2, top, text, kind, size)
        x += width + 6


def _seat_info(seat: SeatView) -> list[tuple[str, Kind]]:
    info: list[tuple[str, Kind]] = []
    if seat.sub:
        info.append((seat.sub, "dark"))
    if seat.badge:
        info.append((seat.badge, seat.badge_kind))
    return info


def codes_needed(view: TableView) -> set[str]:
    codes = set(view.centre)
    for seat in view.seats:
        codes.update(seat.shown)
        if seat.played:
            codes.add(seat.played)
        if seat.cards:
            codes.add(BACK)
    if view.stack:
        codes.add(BACK)
    return codes


def render_table(view: TableView, images: dict[str, bytes | None]) -> bytes:  # noqa: PLR0912
    size = (900, 620)
    cx, cy = 450, 310
    img = _felt(size)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle((12, 12, 887, 607), 26, outline=(214, 170, 70, 130), width=3)
    draw.rounded_rectangle((22, 22, 877, 597), 20, outline=(255, 255, 255, 28), width=1)

    def put(code: str, x: float, y: float, w: int, h: int) -> None:
        img.alpha_composite(_sprite(code, images.get(code), w, h), (int(x), int(y)))

    cw, ch = 72, 100
    row_w = len(view.centre) * (cw + 8) - 8
    left = cx - row_w // 2
    if view.stack:
        stack_x = left - 96 if view.centre else cx - cw // 2
        for k in range(min(view.stack, 4)):
            put(BACK, stack_x + k * 4, cy - 50 - k * 3, cw, ch)
        _pill(draw, stack_x + cw // 2, cy + 56, f"\N{MULTIPLICATION SIGN}{view.stack}", "dark", 15)
    for k, code in enumerate(view.centre):
        put(code, left + k * (cw + 8), cy - 50, cw, ch)
    if view.note:
        _pill(draw, cx, cy + 84, view.note, "dark", 17)

    spots: list[tuple[float, float]] = []
    for i, seat in enumerate(view.seats):
        angle = math.radians(90 + 360 * i / len(view.seats))
        spots.append((cx + 340 * math.cos(angle), cy + 225 * math.sin(angle)))
        sx, sy = int(spots[-1][0]), int(spots[-1][1])
        top = sy - 70

        if seat.active:
            _tint(img, (sx - 88, top - 8, sx + 88, top + 146), 18, (255, 255, 255, 18), GOLD, 3)
        _pill(draw, sx, top + 2, truncate(seat.name, 16), "gold" if seat.active else "dark", 17)

        if info := _seat_info(seat):
            _pill_row(draw, sx, top + 38, info, 14)

        card_y = top + 68
        if seat.shown:
            shown = seat.shown[:7]
            span = 50 + 32 * (len(shown) - 1)
            for k, code in enumerate(shown):
                put(code, sx - span // 2 + k * 32, card_y, 50, 70)
        elif seat.cards:
            count = min(seat.cards, 5)
            span = 50 + 16 * (count - 1)
            x0 = sx - span // 2
            for k in range(count):
                put(BACK, x0 + k * 16, card_y, 50, 70)
            bx = x0 + span + 16
            draw.ellipse((bx - 14, card_y + 21, bx + 14, card_y + 49), fill=(0, 0, 0, 170))
            draw.text((bx, card_y + 35), str(seat.cards), font=font(15), fill=(255, 255, 255, 255), anchor="mm")

        if seat.dim:
            _tint(img, (sx - 88, top - 8, sx + 88, top + 146), 18, (0, 0, 0, 115))

    for seat, (sx, sy) in zip(view.seats, spots, strict=True):
        if seat.played:
            put(seat.played, cx + (sx - cx) * 0.46 - 35, cy + (sy - cy) * 0.46 - 48, 70, 96)

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), 32, fill=255)
    img.putalpha(mask)
    return _png(img)


def render_hand(
    cards: list[str],
    images: dict[str, bytes | None],
    *,
    hidden: bool = False,
    raised: set[int] | frozenset[int] = frozenset(),
    dimmed: set[int] | frozenset[int] = frozenset(),
) -> bytes:
    cw, ch, per_row, lift = 84, 117, 13, 18
    count = len(cards)
    rows = math.ceil(count / per_row)
    widest = min(count, per_row)
    step = min(round(cw * 0.62), max(20, (820 - cw) // (widest - 1))) if widest > 1 else 0
    width = max(cw + step * (widest - 1) + 56, 420)
    row_h = ch + lift + 30
    size = (width, rows * row_h + 24)

    img = _felt(size)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle((6, 6, size[0] - 7, size[1] - 7), 20, outline=(214, 170, 70, 130), width=3)

    for index, code in enumerate(cards):
        row, column = divmod(index, per_row)
        in_row = min(per_row, count - row * per_row)
        x = (width - (cw + step * (in_row - 1))) // 2 + column * step
        base_y = 12 + lift + row * row_h
        face = BACK if hidden else code
        img.alpha_composite(_sprite(face, images.get(face), cw, ch), (x, base_y - (lift if index in raised else 0)))
        if index in dimmed:
            _tint(img, (x, base_y, x + cw - 1, base_y + ch - 1), 8, (0, 0, 0, 125))
        if not hidden:
            nx = x + (cw if column == in_row - 1 else step) // 2
            ny = base_y + ch + 14
            draw.ellipse((nx - 11, ny - 11, nx + 11, ny + 11), fill=(0, 0, 0, 150))
            draw.text((nx, ny), str(index + 1), font=font(14), fill=(255, 255, 255, 255), anchor="mm")

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), 24, fill=255)
    img.putalpha(mask)
    return _png(img)


class Lobby(discord.ui.LayoutView):
    """Pre-game lobby: anyone can press Join Game, the host starts, and empty seats are filled with bots."""

    def __init__(self, ctx: commands.Context[Bot], game_cls: type[CardGame], *, timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.game_cls = game_cls
        self.seats = [Seat(truncate(ctx.author.display_name, 14), ctx.author)]
        self.started = False
        self.message: discord.PartialMessage | None = None
        self._render()

    def _bot_seat(self) -> Seat:
        taken = {seat.name for seat in self.seats}
        return Seat(next((name for name in BOT_NAMES if name not in taken), f"Bot{len(self.seats)}"))

    def _button(
        self, text: str, callback, style: discord.ButtonStyle = discord.ButtonStyle.secondary, *, disabled: bool = False
    ) -> discord.ui.Button:
        button = discord.ui.Button(label=text, style=style, disabled=disabled)
        button.callback = callback
        return button

    def _render(self) -> None:
        game = self.game_cls
        self.clear_items()
        names = "\n".join(f"`{i}.` {seat.tag}" + (" \N{CROWN}" if i == 1 else "") for i, seat in enumerate(self.seats, 1))
        full = len(self.seats) >= game.max_players

        container = discord.ui.Container(accent_colour=game.colour)
        container.add_item(discord.ui.TextDisplay(f"### {game.emoji} {game.title}\n{game.rules}"))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(f"**Players ({len(self.seats)}/{game.max_players})**\n{names}"))
        container.add_item(
            discord.ui.TextDisplay(
                f"-# {game.min_players}\N{EN DASH}{game.max_players} players. Empty seats are filled with bots when the host starts."
            )
        )
        container.add_item(
            discord.ui.ActionRow(
                self._button("Join Game", self._join, discord.ButtonStyle.success, disabled=full),
                self._button("Leave", self._leave),
                self._button("Add Bot", self._add_bot, disabled=full),
            )
        )
        container.add_item(
            discord.ui.ActionRow(
                self._button("Start", self._start, discord.ButtonStyle.primary),
                self._button("Cancel", self._cancel, discord.ButtonStyle.danger),
            )
        )
        self.add_item(container)

    def _is_host(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id

    async def _join(self, interaction: discord.Interaction) -> None:
        if any(seat.user and seat.user.id == interaction.user.id for seat in self.seats):
            await interaction.response.send_message("You're already in this game.", ephemeral=True)
        elif len(self.seats) >= self.game_cls.max_players:
            await interaction.response.send_message("The table is full.", ephemeral=True)
        else:
            self.seats.append(Seat(truncate(interaction.user.display_name, 14), interaction.user))
            self._render()
            await interaction.response.edit_message(view=self)

    async def _leave(self, interaction: discord.Interaction) -> None:
        if self._is_host(interaction):
            await interaction.response.send_message("The host can't leave - press Cancel instead.", ephemeral=True)
            return
        seat = next((s for s in self.seats if s.user and s.user.id == interaction.user.id), None)
        if seat is None:
            await interaction.response.send_message("You're not in this game.", ephemeral=True)
            return
        self.seats.remove(seat)
        self._render()
        await interaction.response.edit_message(view=self)

    async def _add_bot(self, interaction: discord.Interaction) -> None:
        if not self._is_host(interaction):
            await interaction.response.send_message("Only the host can add bots.", ephemeral=True)
        elif len(self.seats) >= self.game_cls.max_players:
            await interaction.response.send_message("The table is full.", ephemeral=True)
        else:
            self.seats.append(self._bot_seat())
            self._render()
            await interaction.response.edit_message(view=self)

    async def _start(self, interaction: discord.Interaction) -> None:
        if not self._is_host(interaction):
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
            return

        game = self.game_cls
        if len(self.seats) < game.min_players:
            while len(self.seats) < max(game.fill_to, game.min_players):
                self.seats.append(self._bot_seat())

        self.started = True
        await interaction.response.edit_message(view=NoticeLayout.info("Dealing the cards\N{HORIZONTAL ELLIPSIS}", title=game.title))
        self.stop()

    async def _cancel(self, interaction: discord.Interaction) -> None:
        if not self._is_host(interaction):
            await interaction.response.send_message("Only the host can cancel.", ephemeral=True)
            return
        await interaction.response.edit_message(view=NoticeLayout.warning("The game was cancelled.", title=self.game_cls.title))
        self.stop()

    async def on_timeout(self) -> None:
        if not self.started and self.message is not None:
            with suppress(discord.HTTPException):
                await self.message.edit(view=NoticeLayout.warning("The lobby expired.", title=self.game_cls.title))

    async def run(self) -> tuple[list[Seat], discord.PartialMessage] | None:
        sent = await self.ctx.reply(view=self, allowed_mentions=NO_MENTIONS)
        self.message = self.ctx.channel.get_partial_message(sent.id)
        await self.wait()
        return (self.seats, self.message) if self.started else None


class TableLayout(discord.ui.LayoutView):
    """The public table: image, caption and the shared buttons."""

    def __init__(self, game: CardGame, filename: str) -> None:
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=game.colour)
        container.add_item(discord.ui.TextDisplay(f"### {game.emoji} {game.title}"))
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{filename}")))
        container.add_item(discord.ui.TextDisplay(truncate(game.caption_text or "-# Waiting\N{HORIZONTAL ELLIPSIS}", 3800)))

        if not game.finished:

            async def rules(interaction: discord.Interaction) -> None:
                await interaction.response.send_message(view=NoticeLayout.info(game.rules, title=game.title), ephemeral=True)

            async def end(interaction: discord.Interaction) -> None:
                if interaction.user.id != game.host.id:
                    await interaction.response.send_message("Only the host can end the game.", ephemeral=True)
                    return
                await interaction.response.defer()
                game.stop_game()

            hand = discord.ui.Button(label="My Hand", emoji="\N{PLAYING CARD BLACK JOKER}", style=discord.ButtonStyle.primary)
            hand.callback = game.open_hand
            rules_button = discord.ui.Button(label="Rules", style=discord.ButtonStyle.secondary)
            rules_button.callback = rules
            end_button = discord.ui.Button(label="End Game", style=discord.ButtonStyle.danger)
            end_button.callback = end
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.ActionRow(hand, rules_button, end_button))

        self.add_item(container)


class HandPanel(discord.ui.LayoutView):
    """Ephemeral, per-player view of a hand with the controls for the current decision."""

    def __init__(self, game: CardGame, seat: Seat) -> None:
        super().__init__(timeout=300)
        self.game = game
        self.seat = seat
        self.selected: list[int] = []
        self.spec: PromptSpec | None = None
        self.page = 0
        self._frame = 0

    async def build(self) -> list[discord.File]:
        game = self.game
        spec = self.spec = game.panel_spec(self.seat)
        self.selected = [i for i in self.selected if i < len(spec.cards)]
        self.clear_items()

        container = discord.ui.Container(accent_colour=game.colour)
        container.add_item(discord.ui.TextDisplay(truncate(spec.caption, 1800)))
        files: list[discord.File] = []

        if spec.cards:
            codes = sorted(set(spec.cards) | {BACK})
            fetched = await card_store(game.bot).many([card_url(code) for code in codes])
            png = await asyncio.to_thread(
                render_hand,
                spec.cards,
                dict(zip(codes, fetched, strict=True)),
                hidden=spec.hidden,
                raised=set(self.selected),
                dimmed=spec.dimmed,
            )
            self._frame += 1
            filename = f"hand-{self._frame}.png"
            files.append(discord.File(BytesIO(png), filename=filename))
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{filename}")))

        if game.pendings.get(self.seat) is not None:
            self._controls(container, spec)

        self.add_item(container)
        return files

    def _controls(self, container: discord.ui.Container, spec: PromptSpec) -> None:
        container.add_item(discord.ui.Separator())
        buttons: list[discord.ui.Button] = []

        for button_spec in spec.buttons:
            button = discord.ui.Button(label=button_spec.label, emoji=button_spec.emoji, style=button_spec.style, disabled=button_spec.disabled)
            button.callback = self._on_button(button_spec.id)
            buttons.append(button)

        if (select := spec.select) and select.options:
            pages = math.ceil(len(select.options) / SELECT_PAGE)
            self.page = min(self.page, pages - 1)
            options = select.options[self.page * SELECT_PAGE : (self.page + 1) * SELECT_PAGE]
            menu = discord.ui.Select(
                placeholder=select.placeholder,
                min_values=min(select.minimum, len(options)),
                max_values=min(select.maximum, len(options)),
                options=[discord.SelectOption(label=f"{i + 1}. {text}", value=str(i), default=i in self.selected) for i, text in options],
            )
            menu.callback = self._on_select(menu, {i for i, _ in options})
            container.add_item(discord.ui.ActionRow(menu))

            if pages > 1:
                for text, step in (("\N{BLACK LEFT-POINTING TRIANGLE}", -1), (f"\N{BLACK RIGHT-POINTING TRIANGLE} {self.page + 1}/{pages}", 1)):
                    pager = discord.ui.Button(label=text, style=discord.ButtonStyle.secondary, disabled=not 0 <= self.page + step < pages)
                    pager.callback = self._on_page(step)
                    buttons.append(pager)

            if select.maximum > 1:
                ready = select.minimum <= len(self.selected) <= select.maximum
                confirm = discord.ui.Button(
                    label=f"{select.confirm_label} ({len(self.selected)})",
                    style=discord.ButtonStyle.success,
                    disabled=not ready,
                )
                confirm.callback = self._on_confirm
                buttons.append(confirm)

        for chunk in discord.utils.as_chunks(buttons, 5):
            container.add_item(discord.ui.ActionRow(*chunk))

    def _on_select(self, menu: discord.ui.Select, on_page: set[int]):
        async def callback(interaction: discord.Interaction) -> None:
            values = tuple(int(v) for v in menu.values)
            if self.spec is not None and self.spec.select is not None and self.spec.select.maximum == 1:
                await self._submit(interaction, ("select", values))
                return
            self.selected = [i for i in self.selected if i not in on_page] + list(values)
            files = await self.build()
            await interaction.response.edit_message(view=self, attachments=files)

        return callback

    def _on_page(self, step: int):
        async def callback(interaction: discord.Interaction) -> None:
            self.page += step
            files = await self.build()
            await interaction.response.edit_message(view=self, attachments=files)

        return callback

    async def _on_confirm(self, interaction: discord.Interaction) -> None:
        await self._submit(interaction, ("select", tuple(self.selected)))

    def _on_button(self, button_id: str):
        async def callback(interaction: discord.Interaction) -> None:
            if self.spec is not None and button_id in self.spec.local:
                self.spec.local[button_id]()
                files = await self.build()
                await interaction.response.edit_message(view=self, attachments=files)
                return
            await self._submit(interaction, (button_id, ()))

        return callback

    async def _submit(self, interaction: discord.Interaction, action: Action) -> None:
        if (error := self.game.submit(self.seat, action)) is not None:
            await interaction.response.send_message(error, ephemeral=True)
            return
        await interaction.response.edit_message(view=NoticeLayout.success("Move sent - watch the table."), attachments=[])


class CardGame:
    """Base class: owns the public message, pending decisions and the main loop."""

    title: ClassVar[str] = "Cards"
    emoji: ClassVar[str] = "\N{PLAYING CARD BLACK JOKER}"
    rules: ClassVar[str] = ""
    min_players: ClassVar[int] = 2
    max_players: ClassVar[int] = 6
    fill_to: ClassVar[int] = 4
    colour: ClassVar[discord.Colour] = discord.Colour.from_rgb(30, 112, 70)
    human_timeout: ClassVar[float] = 90.0
    bot_delay: ClassVar[float] = 1.0

    def __init__(self, ctx: commands.Context[Bot], seats: list[Seat], message: discord.PartialMessage) -> None:
        self.ctx = ctx
        self.bot = ctx.bot
        self.host = ctx.author
        self.seats = seats
        self.message = message
        self.pendings: dict[Seat, Pending] = {}
        self.caption_text = ""
        self.finished = False
        self._frame = 0
        self._task: asyncio.Task | None = None

    async def play(self) -> None:
        raise NotImplementedError

    def table_view(self) -> TableView:
        raise NotImplementedError

    def hand_of(self, seat: Seat) -> list[str]:
        return []

    def hand_hidden(self, seat: Seat) -> bool:
        return False

    def idle_caption(self, seat: Seat) -> str:
        return "Waiting for your turn\N{HORIZONTAL ELLIPSIS}"

    def seat_of(self, user: discord.abc.User) -> Seat | None:
        return next((seat for seat in self.seats if seat.user is not None and seat.user.id == user.id), None)

    def panel_spec(self, seat: Seat) -> PromptSpec:
        if (pending := self.pendings.get(seat)) is not None:
            return pending.build()
        return PromptSpec(cards=self.hand_of(seat), caption=self.idle_caption(seat), hidden=self.hand_hidden(seat))

    async def refresh(self, caption: str | None = None) -> None:
        if caption is not None:
            self.caption_text = caption

        view = self.table_view()
        codes = sorted(codes_needed(view))
        fetched = await card_store(self.bot).many([card_url(code) for code in codes])
        png = await asyncio.to_thread(render_table, view, dict(zip(codes, fetched, strict=True)))

        self._frame += 1
        filename = f"table-{self._frame}.png"
        try:
            await self.message.edit(view=TableLayout(self, filename), attachments=[discord.File(BytesIO(png), filename=filename)])
        except discord.NotFound:
            raise GameEnded from None

    async def pause(self, seconds: float | None = None) -> None:
        await asyncio.sleep(self.bot_delay if seconds is None else seconds)

    async def ping(self, seat: Seat) -> None:
        if seat.user is None:
            return
        with suppress(discord.HTTPException):
            await self.message.channel.send(
                f"{seat.user.mention} your move - press **My Hand**.",
                delete_after=20,
                allowed_mentions=discord.AllowedMentions(users=[seat.user]),
            )

    async def decide(
        self,
        seat: Seat,
        *,
        caption: str | None,
        build: Callable[[], PromptSpec],
        validate: Callable[[Action], str | None],
        ai: Callable[[], Action],
        refresh: bool = True,
    ) -> Action:
        """Ask ``seat`` for a move. Bots (and humans who time out) answer through ``ai``."""
        if seat.is_bot:
            await self.pause()
            return ai()

        pending = Pending(seat, build, validate, asyncio.get_running_loop().create_future())
        self.pendings[seat] = pending
        try:
            if refresh:
                await self.refresh(caption)
            await self.ping(seat)
            return await asyncio.wait_for(pending.future, self.human_timeout)
        except TimeoutError:
            seat.afk += 1
            return ai()
        finally:
            self.pendings.pop(seat, None)

    def submit(self, seat: Seat, action: Action) -> str | None:
        pending = self.pendings.get(seat)
        if pending is None or pending.future.done():
            return "It's not your turn."
        if (error := pending.validate(action)) is not None:
            return error
        seat.afk = 0
        pending.future.set_result(action)
        return None

    async def open_hand(self, interaction: discord.Interaction) -> None:
        seat = self.seat_of(interaction.user)
        if seat is None:
            await interaction.response.send_message("You're not playing in this game.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        panel = HandPanel(self, seat)
        files = await panel.build()
        await interaction.followup.send(view=panel, files=files, ephemeral=True)

    def stop_game(self) -> None:
        if self._task is not None:
            self._task.cancel()

    async def run(self) -> None:
        self._task = asyncio.current_task()
        try:
            await self.refresh()
            await self.play()
        except asyncio.CancelledError:
            if self._task is not None:
                self._task.uncancel()
            self.caption_text = "Game ended by the host."
        except GameEnded:
            return
        except Exception:
            _log.exception("%s crashed", self.title)
            self.caption_text = "Something went wrong, so the game was aborted."
        finally:
            self.finished = True
            self.pendings.clear()

        with suppress(GameEnded, discord.HTTPException):
            await self.refresh()
