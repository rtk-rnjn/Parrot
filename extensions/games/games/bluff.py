"""Bluff (the Indian take on Cheat): play cards face down, claim a rank, and call out the liars."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

import discord

from .card_core import RANK_ORDER, ButtonSpec, CardGame, PromptSpec, SeatView, SelectSpec, TableView, label, new_deck, sort_hand

if TYPE_CHECKING:
    from .blackjack_table import Kind
    from .card_core import Action, Seat

__all__ = ("Bluff",)

DISPLAY_ORDER = "A" + RANK_ORDER[:-1]  # A, 2 \N{HORIZONTAL ELLIPSIS} 10, J, Q, K
RANK_TEXT = {"0": "10", "J": "Jack", "Q": "Queen", "K": "King", "A": "Ace"}
SUIT_SIZE = 4


def rank_name(rank: str) -> str:
    return RANK_TEXT.get(rank, rank)


def plural(rank: str) -> str:
    return rank_name(rank) + "s"


@dataclass(slots=True)
class Play:
    seat: Seat
    cards: list[str]


@dataclass(slots=True)
class Status:
    text: str
    kind: Kind = "neutral"


class Bluff(CardGame):
    title = "Bluff"
    emoji = "\N{LYING FACE}"
    rules = (
        "The whole deck is dealt out. The starter puts **1\N{EN DASH}4 cards face down** and declares a rank, say *three Kings*. "
        "Each player after that must **play** more cards claiming the same rank, **pass**, or **call bluff** on the last play.\n"
        "When bluff is called the cards are flipped: if the claim was honest the caller picks up the whole pile, "
        "otherwise the liar does. The winner of the challenge starts a new round with any rank.\n"
        "If everyone passes, the pile is thrown away and the last player to play starts again. First to empty their hand wins."
    )
    min_players = 2
    max_players = 6
    fill_to = 4
    colour = discord.Colour.from_rgb(80, 60, 150)

    MAX_PLAY = 4
    MAX_TURNS = 400

    # Bot instincts: how often it calls, bluffs, and so on.
    BASE_SUSPICION = 0.12
    PER_CARD_SUSPICION = 0.12
    OVERCLAIM_SUSPICION = 0.3
    ENDGAME_SUSPICION = 0.25
    CAUTION = 0.1
    CALL_ON_EMPTY = 0.7
    BLUFF_CHANCE = 0.35
    DOUBLE_BLUFF_CHANCE = 0.3
    PAD_CHANCE = 0.5
    FEW_CARDS = 3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.hands: dict[Seat, list[str]] = {}
        self.pile: list[str] = []
        self.claim: str | None = None
        self.claimed = 0
        self.last: Play | None = None
        self.passes = 0
        self.reveal: tuple[str, ...] = ()
        self.status: dict[Seat, Status] = {}
        self.turn: Seat | None = None
        self.starter = 0
        self.turns = 0
        self.discarded = 0

    async def play(self) -> None:
        deck = new_deck()
        self.hands = {seat: [] for seat in self.seats}
        for index, card in enumerate(deck):
            self.hands[self.seats[index % len(self.seats)]].append(card)
        for seat in self.seats:
            self.hands[seat] = sort_hand(self.hands[seat])

        await self.refresh(f"Dealt. **{self.seats[0].name}** starts the first round.")
        await self.pause(2)

        winner: Seat | None = None
        while winner is None and self.turns < self.MAX_TURNS:
            winner = await self.play_round()
        if winner is None:
            winner = min(self.seats, key=lambda s: len(self.hands[s]))
            await self.refresh(f"Time's up! \N{TROPHY} **{winner.name}** wins with the fewest cards left.")
            return

        self.turn = None
        await self.refresh(f"\N{TROPHY} **{winner.name}** got rid of every card and wins!")

    async def play_round(self) -> Seat | None:
        self.claim = None
        self.claimed = 0
        self.last = None
        self.passes = 0
        self.pile = []
        self.reveal = ()
        self.status = {}

        index = self.starter
        while self.turns < self.MAX_TURNS:
            seat = self.seats[index % len(self.seats)]
            index += 1
            if not self.hands[seat]:
                continue

            self.turn = seat
            self.turns += 1
            kind, cards = await self.take_turn(seat)

            if kind == "call":
                return await self.resolve_call(seat)
            if kind == "pass":
                self.passes += 1
                self.status[seat] = Status("PASSED")
                await self.refresh(f"**{seat.name}** passes.")
                if self.passes >= len(self.seats) - 1 and self.last is not None:
                    return await self.everyone_passed()
                continue

            assert self.claim is not None
            self.pile += cards
            for card in cards:
                self.hands[seat].remove(card)
            self.last = Play(seat, cards)
            self.claimed += len(cards)
            self.passes = 0
            self.status = {seat: Status(f"PLAYED {len(cards)}", "info")}
            count = f"{len(cards)} card{'s' if len(cards) != 1 else ''}"
            await self.refresh(
                f"**{seat.name}** plays {count} as **{plural(self.claim)}**." + (" They have no cards left!" if not self.hands[seat] else "")
            )
        return None

    async def everyone_passed(self) -> Seat | None:
        assert self.last is not None
        leader = self.last.seat
        if not self.hands[leader]:
            return leader
        thrown, self.pile = len(self.pile), []
        self.discarded += thrown
        self.starter = self.seats.index(leader)
        await self.refresh(f"Everyone passed - the pile of **{thrown}** cards is thrown away. **{leader.name}** starts a new round.")
        await self.pause(2.5)
        return None

    async def resolve_call(self, caller: Seat) -> Seat | None:
        assert self.last is not None
        assert self.claim is not None
        accused, cards = self.last.seat, self.last.cards
        honest = all(card[0] == self.claim for card in cards)
        loser, winner = (caller, accused) if honest else (accused, caller)
        self.reveal = tuple(cards)
        self.status = {accused: Status("HONEST", "good") if honest else Status("CAUGHT", "bad"), caller: Status("CALLED", "info")}
        pile, self.pile = self.pile, []
        self.hands[loser] = sort_hand(self.hands[loser] + pile)

        shown = " ".join(label(card) for card in cards)
        verdict = "it was honest" if honest else "it was a bluff"
        await self.refresh(
            f"**{caller.name}** calls bluff on **{accused.name}**! The cards were {shown} - {verdict}. "
            f"**{loser.name}** picks up **{len(pile)}** cards."
        )
        await self.pause(4)
        if honest and not self.hands[accused]:
            return accused
        self.starter = self.seats.index(winner)
        return None

    async def take_turn(self, seat: Seat) -> tuple[str, list[str]]:
        hand = self.hands[seat]
        starting = self.claim is None
        waiting = self.last is not None and not self.hands[self.last.seat]  # the last player went out; only call or pass
        chosen: dict[str, str | None] = {"rank": None}

        def build() -> PromptSpec:
            rank = self.claim or chosen["rank"]
            buttons: list[ButtonSpec] = []
            local = {}
            if starting:
                for candidate in DISPLAY_ORDER:
                    style = discord.ButtonStyle.primary if candidate == chosen["rank"] else discord.ButtonStyle.secondary
                    buttons.append(ButtonSpec(f"rank:{candidate}", rank_name(candidate), style))
                    local[f"rank:{candidate}"] = lambda candidate=candidate: chosen.__setitem__("rank", candidate)
            else:
                buttons.append(ButtonSpec("pass", "Pass", discord.ButtonStyle.secondary))
            if self.last is not None:
                buttons.append(ButtonSpec("call", "Call Bluff!", discord.ButtonStyle.danger, emoji="\N{LYING FACE}"))

            select = None
            if not waiting:
                confirm = f"Play as {plural(rank)}" if rank else "Play"
                select = SelectSpec("Choose up to four cards", 1, self.MAX_PLAY, [(i, label(c)) for i, c in enumerate(hand)], confirm)

            if waiting:
                assert self.last is not None
                caption = f"**{self.last.seat.name}** has no cards left! Call their bluff now or **pass** to let them win."
            elif starting:
                caption = "You start the round: pick the **rank** you're claiming, choose the cards, then play."
            else:
                assert self.last is not None
                caption = f"Claim: **{plural(self.claim or '')}** \N{MIDDLE DOT} **{self.last.seat.name}** just played **{len(self.last.cards)}**."
            caption += f"\nPile: **{len(self.pile)}** cards \N{MIDDLE DOT} claimed so far: **{self.claimed}**"
            return PromptSpec(cards=hand, caption=caption, select=select, buttons=buttons, local=local)

        def validate(action: Action) -> str | None:
            kind, picks = action
            if kind == "call":
                return None if self.last is not None else "There's nothing to call yet."
            if kind == "pass":
                return "You start this round, so you have to play." if starting else None
            if waiting:
                return "You can only call bluff or pass right now."
            if not 1 <= len(set(picks)) <= self.MAX_PLAY or any(not 0 <= i < len(hand) for i in picks):
                return f"Pick between 1 and {self.MAX_PLAY} cards."
            if starting and chosen["rank"] is None:
                return "Pick the rank you're claiming first."
            return None

        def ai() -> Action:
            return self.bot_move(seat, chosen, starting=starting, waiting=waiting)

        action = await self.decide(seat, caption=f"{seat.mention}'s turn.", build=build, validate=validate, ai=ai)
        kind, picks = action
        if kind in {"call", "pass"}:
            return kind, []
        if starting:
            self.claim = chosen["rank"]
        return "play", [hand[i] for i in dict.fromkeys(picks)]

    def bot_move(self, seat: Seat, chosen: dict[str, str | None], *, starting: bool, waiting: bool) -> Action:
        hand = self.hands[seat]
        if waiting:
            return ("call", ()) if random.random() < self.CALL_ON_EMPTY else ("pass", ())

        if starting:
            counts = Counter(card[0] for card in hand)
            rank = max(counts, key=lambda r: (counts[r], random.random()))
            chosen["rank"] = rank
            picks = [i for i, card in enumerate(hand) if card[0] == rank][: self.MAX_PLAY]
            spare = [i for i in range(len(hand)) if i not in picks]
            if 0 < len(spare) <= self.MAX_PLAY - len(picks) and random.random() < self.PAD_CHANCE:
                picks += spare
            return ("select", tuple(picks))

        assert self.last is not None
        assert self.claim is not None
        held = [i for i, card in enumerate(hand) if card[0] == self.claim]
        played = len(self.last.cards)
        suspicion = self.BASE_SUSPICION + self.PER_CARD_SUSPICION * (played - 1)
        if len(held) + played > SUIT_SIZE:
            suspicion = 1.0
        elif self.claimed + len(held) > SUIT_SIZE:
            suspicion += self.OVERCLAIM_SUSPICION
        if len(self.hands[self.last.seat]) <= self.FEW_CARDS:
            suspicion += self.ENDGAME_SUSPICION
        if len(hand) <= self.FEW_CARDS:
            suspicion -= self.CAUTION
        if random.random() < suspicion:
            return ("call", ())
        if held:
            return ("select", tuple(held[: self.MAX_PLAY]))
        if random.random() < self.BLUFF_CHANCE:
            counts = Counter(card[0] for card in hand)
            loners = sorted(range(len(hand)), key=lambda i: counts[hand[i][0]])
            size = 2 if len(loners) > 1 and random.random() < self.DOUBLE_BLUFF_CHANCE else 1
            return ("select", tuple(loners[:size]))
        return ("pass", ())

    def table_view(self) -> TableView:
        seats = []
        for seat in self.seats:
            status = self.status.get(seat)
            seats.append(
                SeatView(
                    seat.tag,
                    sub=f"{len(self.hands.get(seat, []))} cards",
                    cards=len(self.hands.get(seat, [])),
                    active=seat is self.turn,
                    badge=status.text if status else None,
                    badge_kind=status.kind if status else "neutral",
                )
            )
        note = f"Claim: {plural(self.claim)} \N{MIDDLE DOT} {self.claimed} claimed" if self.claim else "New round" if self.hands else "Dealing"
        return TableView(seats, centre=self.reveal, stack=len(self.pile), note=note)

    def hand_of(self, seat: Seat) -> list[str]:
        return self.hands.get(seat, [])

    def idle_caption(self, seat: Seat) -> str:
        claim = f"Claim: **{plural(self.claim)}**" if self.claim else "A new round is about to start"
        return f"{claim} \N{MIDDLE DOT} pile **{len(self.pile)}** cards. Waiting for your turn."
