"""Hearts for four: pass three cards, avoid hearts and the Queen of Spades, or shoot the moon."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord

from .card_core import CardGame, PromptSpec, SeatView, SelectSpec, TableView, label, new_deck, rank_of, sort_hand, suit_of

if TYPE_CHECKING:
    from .card_core import Action, Seat

__all__ = ("Hearts",)

QUEEN = "QS"
TWO_CLUBS = "2C"
HAND_SIZE = 13
MOON = 26
PASS_COUNT = 3
PASS_DIRECTIONS = (("left", 1), ("right", -1), ("across", 2))
QUEEN_RANK = 12
LAST_TO_PLAY = 3


def points(card: str) -> int:
    if card == QUEEN:
        return HAND_SIZE
    return 1 if suit_of(card) == "H" else 0


def is_point(card: str) -> bool:
    return points(card) > 0


class Hearts(CardGame):
    title = "Hearts"
    emoji = "\N{BLACK HEART SUIT}\N{VARIATION SELECTOR-16}"
    rules = (
        "Thirteen cards each. Before most hands you **pass three cards** (left, right, across, then no pass).\n"
        "Whoever holds the 2\N{BLACK CLUB SUIT} leads. Follow suit if you can; the highest card of the led suit takes the trick and leads next. "
        "You can't lead hearts until one has been played, and no points on the first trick.\n"
        "Every heart is **1 point** and the Q\N{BLACK SPADE SUIT} is **13**. Take all 26 to *shoot the moon* and give them to everyone else. "
        "Lowest score wins once someone reaches 50."
    )
    min_players = 4
    max_players = 4
    fill_to = 4
    colour = discord.Colour.from_rgb(170, 40, 60)

    TARGET = 50
    MAX_HANDS = 8

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scores: dict[Seat, int] = {}
        self.hands: dict[Seat, list[str]] = {}
        self.taken: dict[Seat, int] = {}
        self.trick: list[tuple[Seat, str]] = []
        self.trick_no = 0
        self.hand_no = 0
        self.hearts_broken = False
        self.passing: str | None = None
        self.turn: Seat | None = None

    async def play(self) -> None:
        self.scores = dict.fromkeys(self.seats, 0)
        for hand_no in range(1, self.MAX_HANDS + 1):
            self.hand_no = hand_no
            await self.play_hand((hand_no - 1) % (len(PASS_DIRECTIONS) + 1))
            if max(self.scores.values()) >= self.TARGET:
                break
            await self.pause(4)

        winner = min(self.seats, key=lambda s: self.scores[s])
        await self.refresh(f"\N{TROPHY} **{winner.name}** wins with **{self.scores[winner]}** points!\n{self.standings()}")

    async def play_hand(self, pass_mode: int) -> None:
        deck = new_deck()
        self.hands = {seat: sort_hand(deck[i * HAND_SIZE : (i + 1) * HAND_SIZE]) for i, seat in enumerate(self.seats)}
        self.taken = dict.fromkeys(self.seats, 0)
        self.trick = []
        self.trick_no = 0
        self.hearts_broken = False

        if pass_mode < len(PASS_DIRECTIONS):
            await self.pass_cards(*PASS_DIRECTIONS[pass_mode])

        leader = next(seat for seat in self.seats if TWO_CLUBS in self.hands[seat])
        for trick_no in range(1, HAND_SIZE + 1):
            self.trick_no = trick_no
            leader = await self.play_trick(leader)

        await self.score_hand()

    async def pass_cards(self, direction: str, shift: int) -> None:
        self.passing = direction
        await self.refresh(f"Hand **{self.hand_no}** - pass three cards to the **{direction}**.")
        picks = await asyncio.gather(*(self.choose_pass(seat) for seat in self.seats))
        self.passing = None

        moved = [[self.hands[seat][i] for i in indices] for seat, indices in zip(self.seats, picks, strict=True)]
        for index, seat in enumerate(self.seats):
            target = self.seats[(index + shift) % len(self.seats)]
            for card in moved[index]:
                self.hands[seat].remove(card)
                self.hands[target].append(card)
        for seat in self.seats:
            self.hands[seat] = sort_hand(self.hands[seat])
        await self.refresh(f"Cards passed to the **{direction}**. Whoever holds the 2\N{BLACK CLUB SUIT} leads.")

    async def choose_pass(self, seat: Seat) -> tuple[int, ...]:
        hand = self.hands[seat]

        def build() -> PromptSpec:
            return PromptSpec(
                cards=hand,
                caption=f"Pass **three** cards to the **{self.passing}**. High spades and hearts are the usual suspects.",
                select=SelectSpec("Pick three cards to pass", PASS_COUNT, PASS_COUNT, [(i, label(c)) for i, c in enumerate(hand)], "Pass"),
            )

        def validate(action: Action) -> str | None:
            kind, picks = action
            if kind != "select" or len(set(picks)) != PASS_COUNT or any(not 0 <= i < len(hand) for i in picks):
                return "Pick exactly three cards."
            return None

        def ai() -> Action:
            spades = sum(suit_of(c) == "S" for c in hand)

            def danger(card: str) -> float:
                rank, suit = rank_of(card), suit_of(card)
                if card == QUEEN:
                    return 50 if spades < 4 else 20
                if suit == "S" and rank > QUEEN_RANK:
                    return 40 if spades < 4 else 15
                if suit == "H":
                    return rank * 2
                return rank + (6 if sum(suit_of(c) == suit for c in hand) <= 2 else 0)

            ranked = sorted(range(len(hand)), key=lambda i: danger(hand[i]), reverse=True)
            return ("select", tuple(ranked[:PASS_COUNT]))

        action = await self.decide(seat, caption=None, build=build, validate=validate, ai=ai, refresh=False)
        return action[1]

    async def play_trick(self, leader: Seat) -> Seat:
        self.trick = []
        start = self.seats.index(leader)
        for seat in self.seats[start:] + self.seats[:start]:
            self.turn = seat
            card = await self.choose_card(seat)
            self.hands[seat].remove(card)
            self.trick.append((seat, card))
            if suit_of(card) == "H":
                self.hearts_broken = True
            if seat.is_bot:
                await self.refresh(f"**{seat.name}** plays {label(card)}.")

        led = suit_of(self.trick[0][1])
        winner, _ = max((entry for entry in self.trick if suit_of(entry[1]) == led), key=lambda entry: rank_of(entry[1]))
        gained = sum(points(card) for _, card in self.trick)
        self.taken[winner] += gained
        self.turn = None
        suffix = f" and **{gained}** point{'s' if gained != 1 else ''}" if gained else ""
        await self.refresh(f"**{winner.name}** takes trick {self.trick_no}{suffix}.")
        await self.pause(2.5 if gained else 1.5)
        return winner

    def legal(self, seat: Seat) -> list[str]:
        hand = self.hands[seat]
        if not self.trick:
            if self.trick_no == 1:
                return [TWO_CLUBS]
            if not self.hearts_broken and (safe := [c for c in hand if suit_of(c) != "H"]):
                return safe
            return list(hand)

        led = suit_of(self.trick[0][1])
        follow = [c for c in hand if suit_of(c) == led]
        if follow:
            return follow
        if self.trick_no == 1 and (safe := [c for c in hand if not is_point(c)]):
            return safe
        return list(hand)

    async def choose_card(self, seat: Seat) -> str:
        hand = self.hands[seat]
        legal = self.legal(seat)

        def build() -> PromptSpec:
            played = " ".join(label(card) for _, card in self.trick) or "*you lead*"
            caption = (
                f"Trick **{self.trick_no}/{HAND_SIZE}** \N{MIDDLE DOT} on the table: {played}\n"
                f"**Your score** {self.scores[seat]} \N{MIDDLE DOT} taken this hand: {self.taken[seat]}"
            )
            return PromptSpec(
                cards=hand,
                caption=caption,
                select=SelectSpec("Play a card", 1, 1, [(i, label(c)) for i, c in enumerate(hand) if c in legal]),
                dimmed={i for i, c in enumerate(hand) if c not in legal},
            )

        def validate(action: Action) -> str | None:
            kind, picks = action
            if kind != "select" or len(picks) != 1 or not 0 <= picks[0] < len(hand) or hand[picks[0]] not in legal:
                return "That card can't be played right now."
            return None

        def ai() -> Action:
            return ("select", (hand.index(self.bot_card(seat, legal)),))

        action = await self.decide(seat, caption=f"{seat.mention}'s turn - trick {self.trick_no}/{HAND_SIZE}.", build=build, validate=validate, ai=ai)
        return hand[action[1][0]]

    def bot_card(self, seat: Seat, legal: list[str]) -> str:
        queen_out = any(QUEEN in self.hands[s] for s in self.seats)
        if not self.trick:
            return self._bot_lead(legal, queen_out)
        led = suit_of(self.trick[0][1])
        following = [c for c in legal if suit_of(c) == led]
        if following:
            return self._bot_follow(following, led)
        return self._bot_dump(legal, queen_out)

    @staticmethod
    def _bot_lead(legal: list[str], queen_out: bool) -> str:
        safe = [c for c in legal if not (queen_out and suit_of(c) == "S" and rank_of(c) >= QUEEN_RANK)] or legal
        quiet = [c for c in safe if suit_of(c) != "H"] or safe
        return min(quiet, key=rank_of)

    def _bot_follow(self, following: list[str], led: str) -> str:
        winning = max((card for _, card in self.trick if suit_of(card) == led), key=rank_of)
        lower = [c for c in following if rank_of(c) < rank_of(winning)]
        if QUEEN in lower:
            return QUEEN
        if lower:
            return max(lower, key=rank_of)
        points_on_table = any(is_point(card) for _, card in self.trick)
        if len(self.trick) == LAST_TO_PLAY and not points_on_table:
            return max(following, key=rank_of)
        return min((c for c in following if c != QUEEN), key=rank_of, default=QUEEN)

    @staticmethod
    def _bot_dump(legal: list[str], queen_out: bool) -> str:
        if QUEEN in legal:
            return QUEEN
        hearts = [c for c in legal if suit_of(c) == "H"]
        if hearts:
            return max(hearts, key=rank_of)
        return max(legal, key=lambda c: (queen_out and suit_of(c) == "S" and rank_of(c) > QUEEN_RANK, rank_of(c)))

    async def score_hand(self) -> None:
        shooter = next((seat for seat, taken in self.taken.items() if taken == MOON), None)
        for seat in self.seats:
            self.scores[seat] += (0 if seat is shooter else MOON) if shooter else self.taken[seat]

        headline = f"\N{CRESCENT MOON} **{shooter.name}** shot the moon!" if shooter else f"Hand **{self.hand_no}** is over."
        await self.refresh(f"{headline}\n{self.standings()}")

    def standings(self) -> str:
        ordered = sorted(self.seats, key=lambda s: self.scores[s])
        return "\n".join(f"-# {i}. {seat.name} - {self.scores[seat]} points" for i, seat in enumerate(ordered, 1))

    def table_view(self) -> TableView:
        played = dict(self.trick)
        seats = [
            SeatView(
                seat.tag,
                sub=f"{self.scores.get(seat, 0)} pts",
                cards=len(self.hands.get(seat, [])),
                played=played.get(seat),
                active=seat is self.turn or seat in self.pendings,
                badge=f"+{self.taken[seat]}" if self.taken.get(seat) else None,
                badge_kind="bad",
            )
            for seat in self.seats
        ]
        if self.passing:
            note = f"Passing {self.passing}"
        elif self.trick_no:
            note = f"Trick {self.trick_no}/{HAND_SIZE}" + (" \N{MIDDLE DOT} Hearts broken" if self.hearts_broken else "")
        else:
            note = f"Hand {self.hand_no}" if self.hand_no else "Dealing"
        return TableView(seats, note=note)

    def hand_of(self, seat: Seat) -> list[str]:
        return self.hands.get(seat, [])

    def idle_caption(self, seat: Seat) -> str:
        return f"**Your score** {self.scores.get(seat, 0)} \N{MIDDLE DOT} taken this hand: {self.taken.get(seat, 0)}. Waiting for your turn."
