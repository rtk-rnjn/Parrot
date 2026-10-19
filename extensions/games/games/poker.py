"""Texas Hold'em on the shared card table: blinds, four betting streets, side pots and a Monte Carlo bot."""

from __future__ import annotations

import asyncio
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import discord

from .card_core import RANK_ORDER, ButtonSpec, CardGame, PromptSpec, SeatView, TableView, label, new_deck, rank_of, suit_of

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .blackjack_table import Kind
    from .card_core import Action, Seat

__all__ = ("Poker", "describe", "equity", "evaluate")

FULL_DECK = [f"{rank}{suit}" for suit in "CDHS" for rank in RANK_ORDER]
RANK_NAMES = dict(
    zip(range(2, 15), ("Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King", "Ace"), strict=True)
)
PLURALS = {rank: name + ("es" if name == "Six" else "s") for rank, name in RANK_NAMES.items()}
STREETS = ("Pre-flop", "Flop", "Turn", "River")

ACE = 14
STRAIGHT_FLUSH, QUADS, FULL_HOUSE, FLUSH, STRAIGHT, TRIPS, TWO_PAIR, PAIR = 8, 7, 6, 5, 4, 3, 2, 1
HEADS_UP = 2
FLOP = 3


def _straight_high(ranks: set[int]) -> int | None:
    if ACE in ranks:
        ranks = ranks | {1}
    return next((high for high in range(ACE, 4, -1) if all(r in ranks for r in range(high - 4, high + 1))), None)


def evaluate(cards: Sequence[str]) -> tuple[int, ...]:  # noqa: PLR0911
    """Score any 2 to 7 cards as the best five-card poker hand; bigger tuples beat smaller ones."""
    ranks = sorted((rank_of(c) for c in cards), reverse=True)
    suits = Counter(suit_of(c) for c in cards)
    flush_suit = next((s for s, n in suits.items() if n >= 5), None)
    flush_ranks = sorted((rank_of(c) for c in cards if suit_of(c) == flush_suit), reverse=True) if flush_suit else []

    if flush_ranks and (high := _straight_high(set(flush_ranks))) is not None:
        return (STRAIGHT_FLUSH, high)

    groups = sorted(Counter(ranks).items(), key=lambda item: (item[1], item[0]), reverse=True)
    (top, count), *rest = groups
    if count == 4:
        return (QUADS, top, max(r for r in ranks if r != top))
    if count == 3 and rest and rest[0][1] >= 2:
        return (FULL_HOUSE, top, rest[0][0])
    if flush_ranks:
        return (FLUSH, *flush_ranks[:5])
    high = _straight_high(set(ranks))
    if high is not None:
        return (STRAIGHT, high)
    if count == 3:
        return (TRIPS, top, *[r for r in ranks if r != top][:2])
    if count == 2 and rest and rest[0][1] == 2:
        second = rest[0][0]
        return (TWO_PAIR, top, second, max(r for r in ranks if r not in (top, second)))
    if count == 2:
        return (PAIR, top, *[r for r in ranks if r != top][:3])
    return (0, *ranks[:5])


def describe(score: tuple[int, ...]) -> str:  # noqa: PLR0911
    category, first = score[0], score[1]
    if category == STRAIGHT_FLUSH:
        return "Royal Flush" if first == ACE else f"Straight Flush, {RANK_NAMES[first]} high"
    if category == QUADS:
        return f"Four {PLURALS[first]}"
    if category == FULL_HOUSE:
        return f"Full House, {PLURALS[first]} over {PLURALS[score[2]]}"
    if category == FLUSH:
        return f"Flush, {RANK_NAMES[first]} high"
    if category == STRAIGHT:
        return f"Straight, {RANK_NAMES[first]} high"
    if category == TRIPS:
        return f"Three {PLURALS[first]}"
    if category == TWO_PAIR:
        return f"Two Pair, {PLURALS[first]} and {PLURALS[score[2]]}"
    if category == PAIR:
        return f"Pair of {PLURALS[first]}"
    return f"{RANK_NAMES[first]} high"


def equity(hole: list[str], board: list[str], opponents: int, trials: int = 150) -> float:
    """Monte Carlo estimate of how often ``hole`` wins against ``opponents`` random hands."""
    deck = [c for c in FULL_DECK if c not in hole and c not in board]
    needed = 5 - len(board)
    total = 0.0
    for _ in range(trials):
        draw = random.sample(deck, needed + 2 * opponents)
        full = board + draw[:needed]
        mine = evaluate(hole + full)
        best = max(evaluate(draw[needed + 2 * i : needed + 2 * i + 2] + full) for i in range(opponents))
        total += 1.0 if mine > best else 0.5 if mine == best else 0.0
    return total / trials


@dataclass(slots=True)
class PokerPlayer:
    chips: int
    hole: list[str] = field(default_factory=list)
    bet: int = 0  # committed on the current street
    total: int = 0  # committed in the current hand
    folded: bool = False
    in_hand: bool = False
    note: str = ""
    note_kind: Kind = "neutral"

    @property
    def live(self) -> bool:
        return self.in_hand and not self.folded

    @property
    def can_act(self) -> bool:
        return self.live and self.chips > 0

    def pay(self, amount: int) -> int:
        amount = min(amount, self.chips)
        self.chips -= amount
        self.bet += amount
        self.total += amount
        return amount


@dataclass(slots=True)
class Options:
    to_call: int
    raises: dict[str, int]  # action id -> raise-to amount
    can_raise: bool

    @property
    def ids(self) -> set[str]:
        return {"fold", "call", *self.raises}


class Poker(CardGame):
    title = "Texas Hold'em"
    emoji = "\N{BLACK SPADE SUIT}\N{VARIATION SELECTOR-16}"
    rules = (
        "Everyone starts with `$1000`. Each hand the small and big blinds are posted, two private cards are dealt and the "
        "community cards come out in three streets: the **flop**, **turn** and **river**.\n"
        "On your turn **Check/Call** matches the bet, **Raise** increases it and **Fold** gives up the hand. "
        "Going all-in creates side pots, so you can only win what you matched.\n"
        "Best five-card hand from your two cards plus the board wins. The richest player after the last hand takes the game."
    )
    min_players = 2
    max_players = 6
    fill_to = 4
    colour = discord.Colour.from_rgb(120, 32, 44)

    START_CHIPS = 1000
    SMALL_BLIND = 10
    BIG_BLIND = 20
    MAX_HANDS = 10
    TRIALS = 150

    # Bot thresholds: equity is the estimated chance of having the best hand.
    STRONG = 0.78
    GOOD = 0.62
    BLUFF_CHANCE = 0.08
    RAISE_CHANCE = 0.65
    CHEAP_CALL = 0.05
    CHEAP_CALL_CHANCE = 0.5
    ODDS_MARGIN = 1.1

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.players: dict[Seat, PokerPlayer] = {}
        self.board: list[str] = []
        self.pot = 0
        self.current_bet = 0
        self.min_raise = self.BIG_BLIND
        self.street = 0
        self.hand_no = 0
        self.dealer: Seat | None = None
        self.turn: Seat | None = None
        self.showdown = False

    async def play(self) -> None:
        self.players = {seat: PokerPlayer(self.START_CHIPS) for seat in self.seats}
        button = -1

        for hand_no in range(1, self.MAX_HANDS + 1):
            self.hand_no = hand_no
            funded = [s for s in self.seats if self.players[s].chips > 0]
            if len(funded) < HEADS_UP or all(s.user is None for s in funded):
                break
            button = (button + 1) % len(funded)
            await self.play_hand(funded, button)
            await self.pause(4)

        self.turn = None
        winner = max(self.seats, key=lambda s: self.players[s].chips)
        await self.refresh(f"\N{TROPHY} **{winner.name}** wins the game with `${self.players[winner].chips}`!")

    async def play_hand(self, players: list[Seat], button: int) -> None:
        deck = new_deck()
        self.board = []
        self.pot = 0
        self.street = 0
        self.showdown = False
        self.dealer = players[button]

        for seat, player in self.players.items():
            player.in_hand = seat in players
            player.folded = False
            player.hole = []
            player.bet = player.total = 0
            player.note = ""
        for seat in players:
            self.players[seat].hole = sorted((deck.pop(), deck.pop()), key=rank_of, reverse=True)

        count = len(players)
        small, big = (button, (button + 1) % count) if count == HEADS_UP else ((button + 1) % count, (button + 2) % count)
        self.current_bet = 0
        self.min_raise = self.BIG_BLIND
        self.post(players[small], self.SMALL_BLIND, "SB")
        self.post(players[big], self.BIG_BLIND, "BB")
        await self.refresh(
            f"Hand **{self.hand_no}/{self.MAX_HANDS}** - **{players[small].name}** posts `${self.SMALL_BLIND}`, "
            f"**{players[big].name}** posts `${self.BIG_BLIND}`."
        )
        await self.pause(1.5)

        for street in range(len(STREETS)):
            self.street = street
            if street:
                self.board += [deck.pop() for _ in range(FLOP if street == 1 else 1)]
                self.current_bet = 0
                self.min_raise = self.BIG_BLIND
                for player in self.players.values():
                    player.bet = 0
                    player.note = ""
                await self.refresh(f"**{STREETS[street]}** - {' '.join(label(c) for c in self.board)}")
                await self.pause(1.5)

            first = (big + 1) % count if street == 0 else (button + 1) % count
            await self.betting_round(players, first)

            live = [s for s in players if self.players[s].live]
            if len(live) == 1:
                self.players[live[0]].chips += self.pot
                self.turn = None
                await self.refresh(f"\N{TROPHY} **{live[0].name}** takes `${self.pot}` - everyone else folded.")
                return

        await self.finish_hand(players)

    def post(self, seat: Seat, amount: int, note: str) -> None:
        player = self.players[seat]
        paid = player.pay(amount)
        self.pot += paid
        self.current_bet = max(self.current_bet, player.bet)
        player.note, player.note_kind = f"{note} ${paid}", "chip"

    async def betting_round(self, players: list[Seat], first: int) -> None:
        order = players[first:] + players[:first]
        queue = [s for s in order if self.players[s].can_act]

        while queue:
            seat = queue.pop(0)
            player = self.players[seat]
            if not player.can_act or sum(self.players[s].live for s in players) < HEADS_UP:
                continue
            if player.bet >= self.current_bet and not any(self.players[s].can_act for s in players if s is not seat):
                break

            self.turn = seat
            if await self.take_turn(seat):
                after = order[order.index(seat) + 1 :] + order[: order.index(seat)]
                queue = [s for s in after if self.players[s].can_act]

        self.turn = None

    def options(self, seat: Seat, players: list[Seat]) -> Options:
        player = self.players[seat]
        to_call = min(self.current_bet - player.bet, player.chips)
        can_raise = player.chips > to_call and any(self.players[s].can_act for s in players if s is not seat)
        raises: dict[str, int] = {}
        if can_raise:
            all_in = player.bet + player.chips
            minimum = self.current_bet + self.min_raise
            pot_size = self.current_bet + self.pot + to_call
            for key, amount in (("raise", minimum), ("pot", max(minimum, pot_size))):
                if amount < all_in and amount not in raises.values():
                    raises[key] = amount
            raises["allin"] = all_in
        return Options(to_call, raises, can_raise)

    async def take_turn(self, seat: Seat) -> bool:
        """Ask ``seat`` to act. Returns True when the action re-opens betting for the others."""
        player = self.players[seat]
        players = [s for s in self.seats if self.players[s].in_hand]
        options = self.options(seat, players)
        guess: float | None = None
        if seat.is_bot:
            opponents = sum(self.players[s].live for s in players if s is not seat)
            guess = await asyncio.to_thread(equity, player.hole, self.board, opponents, self.TRIALS)

        def build() -> PromptSpec:
            call_label = "Check" if options.to_call == 0 else f"Call ${options.to_call}"
            if options.to_call and options.to_call == player.chips:
                call_label += " (all-in)"
            buttons = [ButtonSpec("call", call_label, discord.ButtonStyle.success)]
            for key, amount in options.raises.items():
                text = f"All-in ${amount}" if key == "allin" else f"Raise to ${amount}"
                buttons.append(ButtonSpec(key, text, discord.ButtonStyle.secondary if key == "allin" else discord.ButtonStyle.primary))
            buttons.append(ButtonSpec("fold", "Fold", discord.ButtonStyle.danger))
            caption = (
                f"**Pot** `${self.pot}` \N{MIDDLE DOT} **To call** `${options.to_call}` \N{MIDDLE DOT} **Your chips** `${player.chips}`\n"
                f"Board: {' '.join(label(c) for c in self.board) or '*nothing yet*'} \N{MIDDLE DOT} You have **{describe(evaluate(player.hole + self.board))}**"
            )
            return PromptSpec(cards=player.hole, caption=caption, buttons=buttons)

        def validate(action: Action) -> str | None:
            return None if action[0] in options.ids else "You can't do that right now."

        def ai() -> Action:
            return (self.bot_choice(player, options, guess), ())

        action = await self.decide(
            seat,
            caption=f"{seat.mention}'s turn - pot `${self.pot}`, `${options.to_call}` to call.",
            build=build,
            validate=validate,
            ai=ai,
        )
        return self.apply(player, action[0], options)

    def bot_choice(self, player: PokerPlayer, options: Options, guess: float | None) -> str:
        if guess is None:  # a human who ran out of time: check or fold
            return "call" if options.to_call == 0 else "fold"

        raise_key = next((key for key in ("raise", "pot", "allin") if key in options.raises), None)
        big_key = "pot" if "pot" in options.raises else raise_key
        wants_raise = raise_key is not None and random.random() < self.RAISE_CHANCE
        if options.to_call == 0:
            if wants_raise and guess > self.GOOD:
                return (big_key if guess > self.STRONG else raise_key) or "call"
            return raise_key if raise_key and random.random() < self.BLUFF_CHANCE else "call"

        if wants_raise and guess > self.STRONG:
            return big_key or "call"
        pot_odds = options.to_call / (self.pot + options.to_call)
        cheap = options.to_call <= player.chips * self.CHEAP_CALL and random.random() < self.CHEAP_CALL_CHANCE
        return "call" if guess >= pot_odds * self.ODDS_MARGIN or cheap else "fold"

    def apply(self, player: PokerPlayer, action: str, options: Options) -> bool:
        if action == "fold":
            player.folded = True
            player.note, player.note_kind = "FOLD", "neutral"
            return False

        if action == "call":
            paid = player.pay(options.to_call)
            self.pot += paid
            if player.chips == 0:
                player.note, player.note_kind = "ALL-IN", "bad"
            else:
                player.note, player.note_kind = ("CHECK", "neutral") if paid == 0 else (f"CALL ${paid}", "chip")
            return False

        target = options.raises[action]
        paid = player.pay(target - player.bet)
        self.pot += paid
        reopened = player.bet > self.current_bet
        if reopened:
            self.min_raise = max(self.min_raise, player.bet - self.current_bet)
            self.current_bet = player.bet
        player.note, player.note_kind = ("ALL-IN", "bad") if player.chips == 0 else (f"RAISE ${player.bet}", "chip")
        return reopened

    def split_pots(self, players: list[Seat], scores: dict[Seat, tuple[int, ...]]) -> dict[Seat, int]:
        """Pay out main and side pots: each level is shared by the best hand among those who matched it."""
        payouts: dict[Seat, int] = Counter()
        previous = 0
        for level in sorted({self.players[s].total for s in scores}):
            portion = sum(min(self.players[s].total, level) - min(self.players[s].total, previous) for s in players)
            eligible = [s for s in scores if self.players[s].total >= level]
            best = max(scores[s] for s in eligible)
            winners = [s for s in eligible if scores[s] == best]
            share, remainder = divmod(portion, len(winners))
            for index, seat in enumerate(winners):
                payouts[seat] += share + (1 if index < remainder else 0)
            previous = level
        return dict(payouts)

    async def finish_hand(self, players: list[Seat]) -> None:
        self.showdown = True
        self.turn = None
        scores = {s: evaluate(self.players[s].hole + self.board) for s in players if self.players[s].live}
        payouts = self.split_pots(players, scores)
        for seat, amount in payouts.items():
            self.players[seat].chips += amount

        lines = [f"{seat.name}: {describe(scores[seat])}" for seat in sorted(scores, key=scores.get, reverse=True)]  # type: ignore[arg-type]
        winners = " \N{MIDDLE DOT} ".join(f"**{seat.name}** `+${amount}`" for seat, amount in payouts.items())
        await self.refresh(f"**Showdown!** \N{TROPHY} {winners}\n" + "\n".join(f"-# {line}" for line in lines))

    def table_view(self) -> TableView:
        seats: list[SeatView] = []
        for seat in self.seats:
            player = self.players.get(seat)
            if player is None:
                seats.append(SeatView(seat.tag))
                continue

            if not player.in_hand:
                badge, kind = ("OUT", "neutral") if player.chips == 0 else (None, "neutral")
            elif player.folded:
                badge, kind = "FOLD", "neutral"
            else:
                badge, kind = (player.note or None), player.note_kind

            dealer = " \N{MIDDLE DOT} D" if seat is self.dealer else ""
            seats.append(
                SeatView(
                    seat.tag,
                    sub=f"${player.chips}{dealer}",
                    cards=2 if player.live and not self.showdown else 0,
                    shown=tuple(player.hole) if self.showdown and player.live else (),
                    active=seat is self.turn,
                    dim=not player.live,
                    badge=badge,
                    badge_kind=kind,
                )
            )
        return TableView(seats, centre=tuple(self.board), note=f"Pot ${self.pot} \N{MIDDLE DOT} {STREETS[self.street]}")

    def hand_of(self, seat: Seat) -> list[str]:
        player = self.players.get(seat)
        return player.hole if player else []

    def idle_caption(self, seat: Seat) -> str:
        player = self.players.get(seat)
        if player is None or not player.in_hand:
            return "You're sitting out this hand."
        if player.folded:
            return f"You folded. **Chips** `${player.chips}` \N{MIDDLE DOT} waiting for the next hand."
        hand = describe(evaluate(player.hole + self.board))
        return f"**Pot** `${self.pot}` \N{MIDDLE DOT} **Chips** `${player.chips}` \N{MIDDLE DOT} You have **{hand}**. Waiting for your turn."
