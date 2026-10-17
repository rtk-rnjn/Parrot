from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

import discord

from core.utils.views import BaseLayoutView

from .blackjack_table import BACK, HandView, card_store, card_url, render_table
from .utils import DEFAULT_COLOR, DiscordColor

if TYPE_CHECKING:
    from discord.ext import commands

    from core import Bot

    from .blackjack_table import Kind

BLACKJACK_VALUE = 21
INITIAL_HAND_SIZE = 2
MAX_HANDS = 4
DEALER_STAND_VALUE = 17
DEALER_DELAY = 0.9


class HandStatus(Enum):
    ACTIVE = "active"
    STAND = "stand"
    BUST = "bust"
    BLACKJACK = "blackjack"
    SURRENDERED = "surrendered"


@dataclass(slots=True)
class BlackjackHand:
    cards: list[str] = field(default_factory=list)
    bet: int = 0
    status: HandStatus = HandStatus.ACTIVE
    doubled: bool = False
    is_split: bool = False
    split_aces: bool = False
    insurance: int = 0

    def _total(self) -> tuple[int, bool]:
        total = aces = 0

        for card in self.cards:
            rank = card[0]
            if rank == "A":
                total += 11
                aces += 1
            elif rank in {"J", "Q", "K", "0"}:
                total += 10
            else:
                total += int(rank)

        while total > BLACKJACK_VALUE and aces:
            total -= 10
            aces -= 1

        return total, aces > 0

    @property
    def value(self) -> int:
        return self._total()[0]

    @property
    def is_soft(self) -> bool:
        return self._total()[1]

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == INITIAL_HAND_SIZE and self.value == BLACKJACK_VALUE

    @property
    def is_bust(self) -> bool:
        return self.value > BLACKJACK_VALUE

    @property
    def can_hit(self) -> bool:
        return self.status is HandStatus.ACTIVE and not self.split_aces and not self.is_bust


@dataclass(frozen=True, slots=True)
class Resolution:
    lines: list[str]
    hand_deltas: list[int]
    insurance_delta: int

    @property
    def net(self) -> int:
        return sum(self.hand_deltas) + self.insurance_delta


def _total_text(hand: BlackjackHand) -> str:
    value = hand.value
    return f"Soft {value}" if hand.is_soft and value < BLACKJACK_VALUE else str(value)


def _total_kind(hand: BlackjackHand) -> Kind:
    if hand.is_bust:
        return "bad"
    return "gold" if hand.value == BLACKJACK_VALUE else "dark"


class BlackjackDeck:
    """Multi-deck blackjack shoe."""

    RANKS: ClassVar[tuple[str, ...]] = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "0", "J", "Q", "K")
    SUITS: ClassVar[tuple[str, ...]] = ("C", "D", "H", "S")

    def __init__(self, decks: int = 6) -> None:
        if decks < 1:
            msg = "decks must be at least 1"
            raise ValueError(msg)

        self.cards = [f"{rank}{suit}" for _ in range(decks) for suit in self.SUITS for rank in self.RANKS]
        random.shuffle(self.cards)

    def draw(self) -> str:
        if not self.cards:
            msg = "Blackjack shoe is empty."
            raise RuntimeError(msg)

        return self.cards.pop()


class Blackjack:
    """Single-player blackjack against a computer dealer, rendered as an image table.

    Supports hit, stand, double down, split (up to four hands, double after split, split aces),
    insurance, late surrender, natural blackjack and a dealer that stands on every 17.
    The dealer's first card is the upcard; the second is the hole card.
    """

    BASE_WAGER = 100
    BLACKJACK_PAYOUT = 1.5
    INSURANCE_PAYOUT = 2.0
    DEALER_STANDS_ON_SOFT_17 = True

    def __init__(
        self,
        *,
        wager: int = BASE_WAGER,
        decks: int = 6,
        embed_color: DiscordColor = DEFAULT_COLOR,
    ) -> None:
        if wager <= 0:
            msg = "wager must be greater than zero"
            raise ValueError(msg)

        self.wager = wager
        self.embed_color = embed_color
        self.deck = BlackjackDeck(decks)

        self.dealer = BlackjackHand()
        self.hands: list[BlackjackHand] = []

        self.current_hand_index = 0
        self.insurance_available = False
        self.finished = False
        self.revealed = False
        self.cancelled = False
        self.timed_out = False
        self.resolution: Resolution | None = None

        self.player: discord.User | discord.Member
        self.message: discord.Message | None = None
        self.view: BlackjackView
        self._frame = 0

    @property
    def current_hand(self) -> BlackjackHand:
        return self.hands[self.current_hand_index]

    @property
    def current_hand_number(self) -> int:
        return self.current_hand_index + 1

    @property
    def has_split(self) -> bool:
        return any(hand.is_split for hand in self.hands)

    def draw(self, hand: BlackjackHand) -> None:
        hand.cards.append(self.deck.draw())

    def deal_initial(self) -> None:
        self.hands = [BlackjackHand(bet=self.wager)]

        self.draw(self.hands[0])
        self.draw(self.dealer)
        self.draw(self.hands[0])
        self.draw(self.dealer)

        if self.hands[0].is_blackjack:
            self.hands[0].status = HandStatus.BLACKJACK
            self.finished = True
            return

        self.insurance_available = self.dealer.cards[0][0] == "A"

    @staticmethod
    def card_value(rank: str) -> int:
        if rank in {"J", "Q", "K", "0"}:
            return 10
        if rank == "A":
            return 11
        return int(rank)

    def can_double(self, hand: BlackjackHand) -> bool:
        return hand.status is HandStatus.ACTIVE and len(hand.cards) == INITIAL_HAND_SIZE and not hand.doubled

    def can_split(self, hand: BlackjackHand) -> bool:
        if hand.status is not HandStatus.ACTIVE or len(hand.cards) != INITIAL_HAND_SIZE or len(self.hands) >= MAX_HANDS:
            return False

        return self.card_value(hand.cards[0][0]) == self.card_value(hand.cards[1][0])

    def can_surrender(self, hand: BlackjackHand) -> bool:
        return hand.status is HandStatus.ACTIVE and len(hand.cards) == INITIAL_HAND_SIZE and not hand.is_split

    @staticmethod
    def _settle(hand: BlackjackHand) -> None:
        """Bust, or stand automatically on 21."""
        if hand.is_bust:
            hand.status = HandStatus.BUST
        elif hand.value == BLACKJACK_VALUE:
            hand.status = HandStatus.STAND

    def hit(self, hand: BlackjackHand) -> None:
        if not hand.can_hit:
            msg = "This hand cannot hit."
            raise ValueError(msg)

        self.draw(hand)
        self._settle(hand)

    def stand(self, hand: BlackjackHand) -> None:
        if hand.status is not HandStatus.ACTIVE:
            msg = "This hand is already finished."
            raise ValueError(msg)

        hand.status = HandStatus.STAND

    def double(self, hand: BlackjackHand) -> None:
        if not self.can_double(hand):
            msg = "This hand cannot be doubled."
            raise ValueError(msg)

        hand.bet *= 2
        hand.doubled = True
        self.draw(hand)
        hand.status = HandStatus.BUST if hand.is_bust else HandStatus.STAND

    def split(self, hand: BlackjackHand) -> None:
        if not self.can_split(hand):
            msg = "This hand cannot be split."
            raise ValueError(msg)

        first_card, second_card = hand.cards
        first = BlackjackHand(cards=[first_card], bet=hand.bet, is_split=True, split_aces=first_card[0] == "A")
        second = BlackjackHand(cards=[second_card], bet=hand.bet, is_split=True, split_aces=second_card[0] == "A")

        first.cards.append(self.deck.draw())
        second.cards.append(self.deck.draw())

        self.hands[self.current_hand_index] = first
        self.hands.insert(self.current_hand_index + 1, second)

        for split_hand in (first, second):
            if split_hand.split_aces:
                split_hand.status = HandStatus.STAND
            else:
                self._settle(split_hand)

    def insure(self, hand: BlackjackHand) -> None:
        if not self.insurance_available:
            msg = "Insurance is not available."
            raise ValueError(msg)

        if hand.insurance:
            msg = "Insurance has already been taken."
            raise ValueError(msg)

        hand.insurance = hand.bet // INITIAL_HAND_SIZE
        self.insurance_available = False

    def surrender(self, hand: BlackjackHand) -> None:
        if not self.can_surrender(hand):
            msg = "This hand cannot be surrendered."
            raise ValueError(msg)

        hand.status = HandStatus.SURRENDERED

    def dealer_should_draw(self) -> bool:
        value = self.dealer.value
        if value < DEALER_STAND_VALUE:
            return True
        return value == DEALER_STAND_VALUE and self.dealer.is_soft and not self.DEALER_STANDS_ON_SOFT_17

    def advance_hand(self) -> bool:
        if self.current_hand.status is HandStatus.ACTIVE:
            return False

        for index in range(self.current_hand_index + 1, len(self.hands)):
            if self.hands[index].status is HandStatus.ACTIVE:
                self.current_hand_index = index
                return True

        return False

    def apply(self, action: str) -> None:
        """Mutate the game for one button press. Raises ``ValueError`` for illegal moves."""
        hand = self.current_hand

        match action:
            case "hit":
                self.hit(hand)
            case "stand":
                self.stand(hand)
            case "double":
                self.double(hand)
            case "split":
                self.split(hand)
            case "insurance":
                self.insure(hand)
            case "surrender":
                self.surrender(hand)
            case _:
                msg = f"Unknown blackjack action: {action}"
                raise ValueError(msg)

        if action != "insurance":
            self.insurance_available = False

    def _settle_hand(self, hand: BlackjackHand, dealer_blackjack: bool, dealer_value: int) -> tuple[int, str]:  # noqa: PLR0911
        bet = hand.bet

        if hand.status is HandStatus.SURRENDERED:
            lost = bet - bet // 2
            return -lost, f"Surrendered - lost `${lost}`."
        if hand.status is HandStatus.BUST:
            return -bet, f"Busted - lost `${bet}`."
        if hand.is_blackjack and not hand.is_split:
            if dealer_blackjack:
                return 0, "Push - both have blackjack."
            payout = int(bet * self.BLACKJACK_PAYOUT)
            return payout, f"Blackjack - won `${payout}`."
        if dealer_blackjack:
            return -bet, f"Dealer blackjack - lost `${bet}`."
        if self.dealer.is_bust:
            return bet, f"Dealer bust - won `${bet}`."
        if hand.value > dealer_value:
            return bet, f"`{hand.value}` beats `{dealer_value}` - won `${bet}`."
        if hand.value < dealer_value:
            return -bet, f"`{hand.value}` loses to `{dealer_value}` - lost `${bet}`."
        return 0, f"Push at `{hand.value}`."

    def resolve(self) -> Resolution:
        dealer_blackjack = self.dealer.is_blackjack
        dealer_value = self.dealer.value
        lines: list[str] = []
        deltas: list[int] = []
        insurance_delta = 0

        for index, hand in enumerate(self.hands, start=1):
            prefix = f"Hand {index}: " if len(self.hands) > 1 else ""

            if hand.insurance:
                if dealer_blackjack:
                    gain = int(hand.insurance * self.INSURANCE_PAYOUT)
                    insurance_delta += gain
                    lines.append(f"\N{SHIELD}\N{VARIATION SELECTOR-16} {prefix}insurance paid `${gain}`.")
                else:
                    insurance_delta -= hand.insurance
                    lines.append(f"\N{SHIELD}\N{VARIATION SELECTOR-16} {prefix}insurance lost `${hand.insurance}`.")

            delta, text = self._settle_hand(hand, dealer_blackjack, dealer_value)
            deltas.append(delta)
            icon = "\N{WHITE HEAVY CHECK MARK}" if delta > 0 else "\N{CROSS MARK}" if delta < 0 else "\N{HEAVY MINUS SIGN}"
            lines.append(f"{icon} {prefix}{text}")

        return Resolution(lines, deltas, insurance_delta)

    def _hand_view(self, index: int, hand: BlackjackHand) -> HandView:
        badge: str | None = None
        kind: Kind = "neutral"

        if self.resolution is not None:
            delta = self.resolution.hand_deltas[index]
            if delta > 0:
                badge, kind = f"+${delta}", "gold" if hand.status is HandStatus.BLACKJACK else "good"
            elif delta < 0:
                badge, kind = f"-${-delta}", "bad"
            else:
                badge = "PUSH"
        elif hand.status is HandStatus.BLACKJACK:
            badge, kind = "BLACKJACK", "gold"
        elif hand.status is HandStatus.BUST:
            badge, kind = "BUST", "bad"
        elif hand.status is HandStatus.SURRENDERED:
            badge = "SURRENDER"
        elif hand.status is HandStatus.STAND:
            badge, kind = ("DOUBLED", "info") if hand.doubled else ("STAND", "neutral")

        label = f"HAND {index + 1}" if len(self.hands) > 1 else self.player.display_name.upper()[:14]
        active = not self.finished and index == self.current_hand_index and hand.status is HandStatus.ACTIVE

        return HandView(
            cards=tuple(hand.cards),
            label=label,
            total=_total_text(hand),
            total_kind=_total_kind(hand),
            bet=hand.bet,
            badge=badge,
            badge_kind=kind,
            active=active,
            dim=hand.status in {HandStatus.BUST, HandStatus.SURRENDERED},
        )

    def _dealer_view(self) -> HandView:
        hidden = None if self.revealed else 1
        if hidden is None:
            total, total_kind = _total_text(self.dealer), _total_kind(self.dealer)
        else:
            total, total_kind = f"{BlackjackHand(cards=self.dealer.cards[:1]).value} + ?", "dark"

        badge: str | None = None
        kind: Kind = "neutral"
        if self.revealed and self.dealer.is_blackjack:
            badge, kind = "BLACKJACK", "gold"
        elif self.revealed and self.dealer.is_bust:
            badge, kind = "BUST", "bad"

        return HandView(
            cards=tuple(self.dealer.cards),
            label="DEALER",
            total=total,
            total_kind=total_kind,
            badge=badge,
            badge_kind=kind,
            hidden_index=hidden if len(self.dealer.cards) > 1 else None,
        )

    def _header(self) -> str:
        total_bet = sum(hand.bet for hand in self.hands)
        return f"### \N{BLACK SPADE SUIT}\N{VARIATION SELECTOR-16} Blackjack \N{MIDDLE DOT} {self.player.display_name}\n-# Bet `${total_bet}`"

    def _caption(self) -> str:
        if self.cancelled:
            return "Game cancelled - no result."
        if self.timed_out:
            return "Timed out - no result."
        if self.resolution is not None:
            net = self.resolution.net
            headline = f"## You won ${net}" if net > 0 else f"## You lost ${-net}" if net < 0 else "## Push"
            return "\n".join([headline, *self.resolution.lines])
        if self.finished:
            return "Dealer is playing\N{HORIZONTAL ELLIPSIS}"

        caption = "**Your turn**"
        if len(self.hands) > 1:
            caption += f" \N{MIDDLE DOT} Hand {self.current_hand_number} of {len(self.hands)}"
        if self.insurance_available:
            caption += f"\nDealer shows an Ace - insurance costs `${self.current_hand.bet // INITIAL_HAND_SIZE}`."
        return caption

    def _accent(self) -> DiscordColor:
        if self.cancelled or self.timed_out:
            return discord.Colour.dark_grey()
        if self.resolution is None:
            return self.embed_color
        net = self.resolution.net
        return discord.Colour.green() if net > 0 else discord.Colour.red() if net < 0 else discord.Colour.gold()

    async def _compose(self) -> list[discord.File]:
        dealer = self._dealer_view()
        hands = [self._hand_view(index, hand) for index, hand in enumerate(self.hands)]

        codes = sorted({code for view in (dealer, *hands) for code in view.cards} | ({BACK} if dealer.hidden_index is not None else set()))
        fetched = await card_store(self.view.bot).many([card_url(code) for code in codes])
        png = await asyncio.to_thread(render_table, dealer, hands, dict(zip(codes, fetched, strict=True)))

        self._frame += 1
        filename = f"blackjack-{self._frame}.png"
        self.view.rebuild(filename, self._header(), self._caption(), self._accent())
        return [discord.File(BytesIO(png), filename=filename)]

    async def update(self) -> None:
        files = await self._compose()
        if self.message is None:
            return

        try:
            await self.message.edit(view=self.view, attachments=files)
        except discord.NotFound:
            self.finished = True
            self.view.stop()

    async def after_action(self) -> None:
        if self.current_hand.status is not HandStatus.ACTIVE and not self.advance_hand():
            await self.finish()
            return

        await self.update()

    async def cancel(self) -> None:
        self.cancelled = True
        self.finished = True
        await self.update()
        self.view.stop()

    async def finish(self) -> None:
        self.finished = True
        self.revealed = True
        await self.update()

        if any(hand.status is HandStatus.STAND for hand in self.hands):
            while self.dealer_should_draw():
                await asyncio.sleep(DEALER_DELAY)
                self.draw(self.dealer)
                await self.update()
            await asyncio.sleep(DEALER_DELAY)

        self.dealer.status = HandStatus.BUST if self.dealer.is_bust else HandStatus.STAND
        self.resolution = self.resolve()
        await self.update()
        self.view.stop()

    async def start(self, ctx: commands.Context[Bot], *, timeout: float | None = None, **kwargs) -> discord.Message | None:
        self.deal_initial()
        self.player = ctx.author
        self.view = BlackjackView(self, bot=ctx.bot, timeout=timeout)

        files = await self._compose()
        self.message = await ctx.reply(view=self.view, files=files, allowed_mentions=discord.AllowedMentions.none(), **kwargs)

        if self.finished:
            await self.finish()
            return self.message

        await self.view.wait()
        return self.message


class BlackjackView(BaseLayoutView):
    """Table image, status text and controls for one blackjack game."""

    def __init__(self, game: Blackjack, *, bot: Bot, timeout: float | None) -> None:
        super().__init__(game.player, timeout=timeout)
        self.game = game
        self.bot = bot
        self._lock = asyncio.Lock()

    def _button(
        self,
        label: str,
        action: str,
        emoji: str,
        *,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        disabled: bool = False,
    ) -> discord.ui.Button:
        button = discord.ui.Button(label=label, emoji=emoji, style=style, disabled=disabled)
        button.callback = self._callback(action)
        return button

    def rebuild(self, filename: str, header: str, caption: str, colour: DiscordColor) -> None:
        game = self.game
        self.clear_items()

        container = discord.ui.Container(accent_colour=colour)
        container.add_item(discord.ui.TextDisplay(header))
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{filename}")))
        container.add_item(discord.ui.TextDisplay(caption))

        if not game.finished:
            hand = game.current_hand
            container.add_item(discord.ui.Separator())
            container.add_item(
                discord.ui.ActionRow(
                    self._button("Hit", "hit", "\N{FISTED HAND SIGN}", style=discord.ButtonStyle.success, disabled=not hand.can_hit),
                    self._button(
                        "Stand", "stand", "\N{OCTAGONAL SIGN}", style=discord.ButtonStyle.danger, disabled=hand.status is not HandStatus.ACTIVE
                    ),
                    self._button(
                        "Double",
                        "double",
                        "2\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}",
                        style=discord.ButtonStyle.primary,
                        disabled=not game.can_double(hand),
                    ),
                    self._button(
                        "Split",
                        "split",
                        "\N{BLACK SCISSORS}\N{VARIATION SELECTOR-16}",
                        style=discord.ButtonStyle.primary,
                        disabled=not game.can_split(hand),
                    ),
                )
            )

            extras = []
            if game.insurance_available:
                extras.append(self._button("Insurance", "insurance", "\N{SHIELD}\N{VARIATION SELECTOR-16}"))
            extras.append(
                self._button("Surrender", "surrender", "\N{WAVING WHITE FLAG}\N{VARIATION SELECTOR-16}", disabled=not game.can_surrender(hand))
            )
            extras.append(self._button("Quit", "cancel", "\N{CROSS MARK}"))
            container.add_item(discord.ui.ActionRow(*extras))

        self.add_item(container)

    def _callback(self, action: str):
        async def callback(interaction: discord.Interaction) -> None:
            game = self.game

            async with self._lock:
                if game.finished:
                    await interaction.response.send_message("This game has already ended.", ephemeral=True)
                    return

                if action == "cancel":
                    await interaction.response.defer()
                    await game.cancel()
                    return

                try:
                    game.apply(action)
                except ValueError as error:
                    await interaction.response.send_message(str(error), ephemeral=True)
                    return

                await interaction.response.defer()
                await game.after_action()

        return callback

    async def on_timeout(self) -> None:
        game = self.game
        if game.finished:
            return

        game.timed_out = True
        game.finished = True
        await game.update()
