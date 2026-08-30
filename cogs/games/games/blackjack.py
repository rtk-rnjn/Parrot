from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

import discord
from discord.ext import commands

from .utils import DEFAULT_COLOR, BaseView, DiscordColor
from .wordle import WordInputButton

if TYPE_CHECKING:
    from core.bot import Parrot

# fmt: off
_black_jack_cards = {
    "0C": discord.PartialEmoji(name="0C", id=1137283528640434196),
    "0D": discord.PartialEmoji(name="0D", id=1137283545224724531),
    "0H": discord.PartialEmoji(name="0H", id=1137283484742852628),
    "0S": discord.PartialEmoji(name="0S", id=1137283517777186848),
    "2C": discord.PartialEmoji(name="2C", id=1137283494985334785),
    "2D": discord.PartialEmoji(name="2D", id=1137283504590295060),
    "2H": discord.PartialEmoji(name="2H", id=1137283540053143572),
    "2S": discord.PartialEmoji(name="2S", id=1137283532427898991),
    "3C": discord.PartialEmoji(name="3C", id=1137283515994603570),
    "3D": discord.PartialEmoji(name="3D", id=1137283482129813644),
    "3H": discord.PartialEmoji(name="3H", id=1137283535116451880),
    "3S": discord.PartialEmoji(name="3S", id=1137283559200129065),
    "4C": discord.PartialEmoji(name="4C", id=1137283487179739196),
    "4D": discord.PartialEmoji(name="4D", id=1137283542586503198),
    "4H": discord.PartialEmoji(name="4H", id=1137283578267455621),
    "4S": discord.PartialEmoji(name="4S", id=1137283530049736824),
    "5C": discord.PartialEmoji(name="5C", id=1137283523468865576),
    "5D": discord.PartialEmoji(name="5D", id=1137283556331237457),
    "5H": discord.PartialEmoji(name="5H", id=1137283462399799336),
    "5S": discord.PartialEmoji(name="5S", id=1137283554938736761),
    "6C": discord.PartialEmoji(name="6C", id=1137283450253082654),
    "6D": discord.PartialEmoji(name="6D", id=1137283477000167454),
    "6H": discord.PartialEmoji(name="6H", id=1137283489557913681),
    "6S": discord.PartialEmoji(name="6S", id=1137283464870248469),
    "7C": discord.PartialEmoji(name="7C", id=1137283575318843425),
    "7D": discord.PartialEmoji(name="7D", id=1137283474269687878),
    "7H": discord.PartialEmoji(name="7H", id=1137283510114193419),
    "7S": discord.PartialEmoji(name="7S", id=1137283478879211531),
    "8C": discord.PartialEmoji(name="8C", id=1137283459774161006),
    "8D": discord.PartialEmoji(name="8D", id=1137283566527594538),
    "8H": discord.PartialEmoji(name="8H", id=1137283507752800306),
    "8S": discord.PartialEmoji(name="8S", id=1137283521166180422),
    "9C": discord.PartialEmoji(name="9C", id=1137283565172838490),
    "9H": discord.PartialEmoji(name="9H", id=1137402224507617340),
    "9D": discord.PartialEmoji(name="9D", id=1137283471753084978),
    "9S": discord.PartialEmoji(name="9S", id=1137283569425842246),
    "AC": discord.PartialEmoji(name="AC", id=1137283549721014273),
    "AD": discord.PartialEmoji(name="AD", id=1137283537750462568),
    "AH": discord.PartialEmoji(name="AH", id=1137283453080051742),
    "AS": discord.PartialEmoji(name="AS", id=1137403003918372884),
    "JC": discord.PartialEmoji(name="JC", id=1137283581262188564),
    "JD": discord.PartialEmoji(name="JD", id=1137283526711058443),
    "JH": discord.PartialEmoji(name="JH", id=1137283562417160192),
    "JS": discord.PartialEmoji(name="JS", id=1137283468494127114),
    "KC": discord.PartialEmoji(name="KC", id=1137283513259937863),
    "KD": discord.PartialEmoji(name="KD", id=1137283573569818694),
    "KH": discord.PartialEmoji(name="KH", id=1137283456825557032),
    "KS": discord.PartialEmoji(name="KS", id=1137283552577327205),
    "QC": discord.PartialEmoji(name="QC", id=1137283502178566146),
    "QD": discord.PartialEmoji(name="QD", id=1137283498495971442),
    "QH": discord.PartialEmoji(name="QH", id=1137283548622106775),
    "QS": discord.PartialEmoji(name="QS", id=1137283492619767818),
}
_card_back = discord.PartialEmoji(name="CARD_BACK", id=1143090855910051851)
# fmt: off

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

    @property
    def value(self) -> int:
        total = 0
        aces = 0

        for card in self.cards:
            rank = card[0]
            if rank == "A":
                total += 11
                aces += 1
            elif rank in {"J", "Q", "K", "0"}:
                total += 10
            else:
                total += int(rank)

        while total > 21 and aces:
            total -= 10
            aces -= 1

        return total

    @property
    def is_soft(self) -> bool:
        total = 0
        aces = 0

        for card in self.cards:
            rank = card[0]
            if rank == "A":
                total += 11
                aces += 1
            elif rank in {"J", "Q", "K", "0"}:
                total += 10
            else:
                total += int(rank)

        while total > 21 and aces:
            total -= 10
            aces -= 1

        return aces > 0

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21

    @property
    def is_bust(self) -> bool:
        return self.value > 21

    @property
    def can_hit(self) -> bool:
        return self.status is HandStatus.ACTIVE and not self.split_aces and not self.is_bust


class BlackjackDeck:
    """Standard one-deck blackjack shoe."""

    RANKS: ClassVar[tuple[str, ...]] = (
        "A",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "0",
        "J",
        "Q",
        "K",
    )

    SUITS: ClassVar[tuple[str, ...]] = ("C", "D", "H", "S")

    def __init__(self, decks: int = 6) -> None:
        if decks < 1:
            raise ValueError("decks must be at least 1")

        self.cards = [f"{rank}{suit}" for _ in range(decks) for suit in self.SUITS for rank in self.RANKS]
        random.shuffle(self.cards)

    def draw(self) -> str:
        if not self.cards:
            raise RuntimeError("Blackjack shoe is empty.")

        return self.cards.pop()


class Blackjack:
    """Single-player blackjack against a computer dealer.

    Supports:
    - Hit
    - Stand
    - Double down
    - Split
    - Insurance
    - Late surrender
    - Multiple splits
    - Double after split
    - Split aces
    - Natural blackjack
    - Dealer soft 17
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
            raise ValueError("wager must be greater than zero")

        self.wager = wager
        self.embed_color = embed_color

        self.deck = BlackjackDeck(decks)

        self.dealer = BlackjackHand()
        self.hands: list[BlackjackHand] = []

        self.current_hand_index = 0
        self.insurance_available = False
        self.finished = False

        self.message: discord.Message | None = None
        self.view: BlackjackView | None = None

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

    def card_emoji(self, card: str) -> str:
        emoji = _black_jack_cards.get(card)
        if emoji is None:
            error_message = f"No blackjack emoji registered for {card!r}"
            raise KeyError(error_message)
        return str(emoji)

    def render_cards(
        self,
        cards: list[str],
        *,
        hide_first: bool = False,
    ) -> str:
        rendered: list[str] = []

        for index, card in enumerate(cards):
            if hide_first and index == 0:
                rendered.append(str(_card_back))
            else:
                rendered.append(self.card_emoji(card))

        return "".join(rendered)

    def dealer_visible_value(self) -> str:
        if len(self.dealer.cards) < 2:
            return "0"

        if self.finished:
            return str(self.dealer.value)

        visible = BlackjackHand(cards=self.dealer.cards[1:])
        return str(visible.value)

    def make_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Blackjack",
            color=self.embed_color,
        )

        dealer_cards = self.render_cards(
            self.dealer.cards,
            hide_first=not self.finished,
        )

        dealer_value = str(self.dealer.value) if self.finished else self.dealer_visible_value()

        embed.add_field(
            name=f"Dealer — {dealer_value}",
            value=dealer_cards or "-",
            inline=False,
        )

        for index, hand in enumerate(self.hands):
            marker = " ← **YOUR TURN**" if (not self.finished and index == self.current_hand_index and hand.status is HandStatus.ACTIVE) else ""

            status = hand.status.value.title()

            embed.add_field(
                name=(f"Hand `{index + 1}` — {hand.value} — ${hand.bet}{marker}"),
                value=(f"{self.render_cards(hand.cards)}"),
                inline=False,
            )
            embed.set_footer(text=f"Status: {status}")

        if self.insurance_available and not self.finished:
            embed.set_footer(text="Dealer shows an Ace — insurance is available.")

        return embed

    def can_double(self, hand: BlackjackHand) -> bool:
        return hand.status is HandStatus.ACTIVE and len(hand.cards) == 2 and not hand.doubled

    def can_split(self, hand: BlackjackHand) -> bool:
        if hand.status is not HandStatus.ACTIVE:
            return False

        if len(hand.cards) != 2:
            return False

        if len(self.hands) >= 4:
            return False

        first = hand.cards[0][0]
        second = hand.cards[1][0]

        return self.card_value(first) == self.card_value(second)

    def can_surrender(self, hand: BlackjackHand) -> bool:
        return hand.status is HandStatus.ACTIVE and len(hand.cards) == 2 and not hand.is_split

    @staticmethod
    def card_value(rank: str) -> int:
        if rank in {"J", "Q", "K", "0"}:
            return 10
        if rank == "A":
            return 11
        return int(rank)

    def hit(self, hand: BlackjackHand) -> None:
        if not hand.can_hit:
            raise ValueError("This hand cannot hit.")

        self.draw(hand)

        if hand.is_bust:
            hand.status = HandStatus.BUST

    def stand(self, hand: BlackjackHand) -> None:
        if hand.status is not HandStatus.ACTIVE:
            raise ValueError("This hand is already finished.")

        hand.status = HandStatus.STAND

    def double(self, hand: BlackjackHand) -> None:
        if not self.can_double(hand):
            raise ValueError("This hand cannot be doubled.")

        hand.bet *= 2
        hand.doubled = True

        self.draw(hand)

        if hand.is_bust:
            hand.status = HandStatus.BUST
        else:
            hand.status = HandStatus.STAND

    def split(self, hand: BlackjackHand) -> None:
        if not self.can_split(hand):
            raise ValueError("This hand cannot be split.")

        if len(self.hands) >= 4:
            raise ValueError("Maximum number of hands reached.")

        first_card, second_card = hand.cards

        first = BlackjackHand(
            cards=[first_card],
            bet=hand.bet,
            is_split=True,
            split_aces=first_card[0] == "A",
        )

        second = BlackjackHand(
            cards=[second_card],
            bet=hand.bet,
            is_split=True,
            split_aces=second_card[0] == "A",
        )

        first.cards.append(self.deck.draw())
        second.cards.append(self.deck.draw())

        self.hands[self.current_hand_index] = first
        self.hands.insert(self.current_hand_index + 1, second)

        # Split aces receive exactly one additional card.
        if first.split_aces:
            first.status = HandStatus.STAND

        if second.split_aces:
            second.status = HandStatus.STAND

    def insure(self, hand: BlackjackHand) -> None:
        if not self.insurance_available:
            raise ValueError("Insurance is not available.")

        if hand.insurance:
            raise ValueError("Insurance has already been taken.")

        hand.insurance = hand.bet // 2
        self.insurance_available = False

    def surrender(self, hand: BlackjackHand) -> None:
        if not self.can_surrender(hand):
            raise ValueError("This hand cannot be surrendered.")

        hand.status = HandStatus.SURRENDERED

    def dealer_play(self) -> None:
        self.finished = True

        while True:
            value = self.dealer.value

            if value > 21:
                self.dealer.status = HandStatus.BUST
                return

            if value < 17:
                self.draw(self.dealer)
                continue

            if value == 17 and self.dealer.is_soft:
                if self.DEALER_STANDS_ON_SOFT_17:
                    self.dealer.status = HandStatus.STAND
                    return

                self.draw(self.dealer)
                continue

            self.dealer.status = HandStatus.STAND
            return

    def all_hands_finished(self) -> bool:
        return all(hand.status is not HandStatus.ACTIVE for hand in self.hands)

    def advance_hand(self) -> bool:
        if not self.all_hands_finished():
            return False

        if self.current_hand_index + 1 < len(self.hands):
            self.current_hand_index += 1
            return True

        return False

    def resolve(self) -> list[str]:  # noqa: PLR0912, C901
        """Resolve all hands and return human-readable results."""
        results: list[str] = []

        dealer_blackjack = self.dealer.is_blackjack
        dealer_value = self.dealer.value

        for index, hand in enumerate(self.hands, start=1):
            if hand.insurance:
                if dealer_blackjack:
                    insurance_profit = int(hand.insurance * self.INSURANCE_PAYOUT)
                    results.append(f"Hand {index}: insurance paid `${insurance_profit}`.")
                else:
                    results.append(f"Hand {index}: insurance lost `${hand.insurance}`.")

            if hand.status is HandStatus.SURRENDERED:
                results.append(f"Hand {index}: surrendered for `${hand.bet // 2}` returned.")
                continue

            if hand.status is HandStatus.BUST:
                results.append(f"Hand {index}: busted — lost `${hand.bet}`.")
                continue

            if hand.is_blackjack and not hand.is_split:
                if dealer_blackjack:
                    results.append(f"Hand {index}: push — both have blackjack.")
                else:
                    payout = int(hand.bet * self.BLACKJACK_PAYOUT)
                    results.append(f"Hand {index}: blackjack — won `${payout}`.")
                continue

            if dealer_blackjack:
                results.append(f"Hand {index}: dealer blackjack — lost `${hand.bet}`.")
                continue

            if self.dealer.is_bust:
                results.append(f"Hand {index}: dealer bust — won `${hand.bet}`.")
                continue

            if hand.value > dealer_value:
                results.append(f"Hand {index}: `{hand.value}` beats `{dealer_value}` — won `${hand.bet}`.")
            elif hand.value < dealer_value:
                results.append(f"Hand {index}: `{hand.value}` loses to `{dealer_value}` — lost `${hand.bet}`.")
            else:
                results.append(f"Hand {index}: push at `{hand.value}`.")

        return results

    def result_embed(self) -> discord.Embed:
        results = self.resolve()

        embed = discord.Embed(
            title="Blackjack — Game Over",
            color=self.embed_color,
        )

        dealer_cards = self.render_cards(self.dealer.cards)

        embed.add_field(
            name=f"Dealer — {self.dealer.value}",
            value=dealer_cards,
            inline=False,
        )

        embed.description = "\n".join(results)

        return embed

    async def finish(self) -> None:
        self.finished = True

        if not all(hand.status is HandStatus.SURRENDERED or hand.status is HandStatus.BUST for hand in self.hands):
            self.dealer_play()

        if self.view is not None:
            self.view.disable_all()

        if self.message is not None:
            await self.message.edit(
                embed=self.result_embed(),
                view=self.view,
            )

        if self.view is not None:
            self.view.stop()

    async def refresh(self) -> None:
        if self.message is not None:
            await self.message.edit(
                embed=self.make_embed(),
                view=self.view,
            )

    async def start(
        self,
        ctx: commands.Context[Parrot],
        *,
        timeout: float | None = None,
        **kwargs,
    ) -> discord.Message:
        self.deal_initial()
        self.player = ctx.author

        self.view = BlackjackView(self, timeout=timeout)

        self.message = await ctx.reply(
            embed=self.make_embed(),
            view=self.view,
            **kwargs,
        )

        self.view.message = self.message

        if self.finished:
            await self.finish()
            return self.message

        await self.view.wait()

        if not self.finished:
            await self.finish()

        return self.message


class BlackjackButton(WordInputButton):
    view: BlackjackView

    def __init__(
        self,
        *,
        action: str,
        label: str,
        emoji: str | discord.Emoji | discord.PartialEmoji | None = None,
        cancel_button: bool = False,
    ) -> None:
        super().__init__(cancel_button=cancel_button)
        self.action = action
        self.label = label
        self.emoji = emoji

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is None:
            return

        game = self.view.game

        if interaction.user.id != game.player.id:
            await interaction.response.send_message(
                "This is not your game.",
                ephemeral=True,
            )
            return

        if self.action == "cancel":
            game.finished = True
            self.view.disable_all()

            await interaction.response.edit_message(
                content="**Blackjack — Cancelled**",
                view=self.view,
            )

            self.view.stop()
            return

        if game.finished:
            await interaction.response.send_message(
                "This game has already ended.",
                ephemeral=True,
            )
            return

        try:
            await self.view.handle_action(
                interaction,
                self.action,
            )
        except ValueError as exc:
            await interaction.response.send_message(
                str(exc),
                ephemeral=True,
            )


class BlackjackView(BaseView):
    """Interactive blackjack controls."""

    def __init__(
        self,
        game: Blackjack,
        *,
        timeout: float | None,
    ) -> None:
        super().__init__(timeout=timeout)

        self.game = game

        self.hit_button = BlackjackButton(
            action="hit",
            label="Hit",
            emoji="👊",
        )

        self.stand_button = BlackjackButton(
            action="stand",
            label="Stand",
            emoji="🛑",
        )

        self.double_button = BlackjackButton(
            action="double",
            label="Double",
            emoji="2️⃣",
        )

        self.split_button = BlackjackButton(
            action="split",
            label="Split",
            emoji="✂️",
        )

        self.insurance_button = BlackjackButton(
            action="insurance",
            label="Insurance",
            emoji="🛡️",
        )

        self.surrender_button = BlackjackButton(
            action="surrender",
            label="Surrender",
            emoji="🏳️",
        )

        self.add_item(self.hit_button)
        self.add_item(self.stand_button)
        self.add_item(self.double_button)
        self.add_item(self.split_button)
        self.add_item(self.insurance_button)
        self.add_item(self.surrender_button)
        self.add_item(
            BlackjackButton(
                action="cancel",
                label="Cancel",
                cancel_button=True,
            ),
        )

        self.update_buttons()

    def update_buttons(self) -> None:
        if self.game.finished:
            self.disable_all()
            return

        hand = self.game.current_hand

        self.hit_button.disabled = not hand.can_hit
        self.stand_button.disabled = hand.status is not HandStatus.ACTIVE
        self.double_button.disabled = not self.game.can_double(hand)
        self.split_button.disabled = not self.game.can_split(hand)
        self.insurance_button.disabled = not self.game.insurance_available
        self.surrender_button.disabled = not self.game.can_surrender(hand)

    async def handle_action(
        self,
        interaction: discord.Interaction,
        action: str,
    ) -> None:
        game = self.game
        hand = game.current_hand

        if action == "hit":
            game.hit(hand)

        elif action == "stand":
            game.stand(hand)

        elif action == "double":
            game.double(hand)

        elif action == "split":
            game.split(hand)

        elif action == "insurance":
            game.insure(hand)

        elif action == "surrender":
            game.surrender(hand)

        else:
            msg = f"Unknown blackjack action: {action}"
            raise ValueError(msg)

        # Insurance itself doesn't end the hand.
        # Splitting creates a new current hand, so keep the player there.
        if action != "split":
            if hand.status is not HandStatus.ACTIVE:
                if not game.advance_hand():
                    await interaction.response.edit_message(
                        embed=game.make_embed(),
                        view=self,
                    )
                    await game.finish()
                    return

        self.update_buttons()

        await interaction.response.edit_message(
            embed=game.make_embed(),
            view=self,
        )

    async def on_timeout(self) -> None:
        if self.game.finished:
            return

        self.game.finished = True

        if self.message is not None:
            self.disable_all()

            await self.message.edit(
                content="**Blackjack — Timed Out**",
                embed=self.game.make_embed(),
                view=self,
            )
