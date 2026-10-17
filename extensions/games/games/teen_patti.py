from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import discord

from .card_core import ButtonSpec, CardGame, PromptSpec, SeatView, TableView, new_deck, rank_of, sort_hand, suit_of

if TYPE_CHECKING:
    from .card_core import Action, Seat

HAND_NAMES = {6: "Trail", 5: "Pure Sequence", 4: "Sequence", 3: "Color", 2: "Pair", 1: "High Card"}


def rank_hand(cards: list[str]) -> tuple:
    """Rank a three card hand: trail > pure sequence > sequence > color > pair > high card."""
    ranks = sorted((rank_of(c) for c in cards), reverse=True)
    flush = len({suit_of(c) for c in cards}) == 1

    if ranks[0] == ranks[2]:
        return (6, ranks[0])

    sequence: float | None = None
    if ranks[0] - ranks[1] == 1 and ranks[1] - ranks[2] == 1:
        sequence = ranks[0]
    elif ranks == [14, 3, 2]:
        sequence = 13.5
    if sequence is not None:
        return (5 if flush else 4, sequence)

    if flush:
        return (3, *ranks)
    if ranks[0] == ranks[1]:
        return (2, ranks[0], ranks[2])
    if ranks[1] == ranks[2]:
        return (2, ranks[1], ranks[0])
    return (1, *ranks)


def strength(cards: list[str]) -> float:
    rank = rank_hand(cards)
    base = {6: 0.97, 5: 0.92, 4: 0.8, 3: 0.62, 2: 0.38, 1: 0.05}[rank[0]]
    spread = {6: 0.03, 5: 0.05, 4: 0.1, 3: 0.15, 2: 0.2, 1: 0.25}[rank[0]]
    return base + spread * min(1.0, rank[1] / 14)


@dataclass(slots=True)
class PlayerState:
    chips: int
    hand: list[str] = field(default_factory=list)
    seen: bool = False
    packed: bool = True
    playing: bool = False


class TeenPatti(CardGame):
    title = "Teen Patti"
    emoji = "\N{PLAYING CARD BLACK JOKER}"
    rules = (
        "Everyone puts in a **boot** and gets three cards. On your turn play **blind** (cards hidden) or **see** your cards.\n"
        "**Chaal** matches the stake (seen players pay double), **Raise** doubles the stake, **Pack** folds. "
        "With two players left either can pay for a **Show**; a tie goes against whoever asked.\n"
        "Ranking: Trail > Pure Sequence > Sequence > Color > Pair > High Card. A-K-Q is the top run, A-2-3 the second."
    )
    min_players = 2
    max_players = 6
    fill_to = 4

    START_CHIPS = 1000
    BOOT = 10
    MAX_STAKE = 160
    MAX_HANDS = 10

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state: dict[Seat, PlayerState] = {}
        self.pot = 0
        self.stake = self.BOOT
        self.turn: Seat | None = None
        self.reveal = False
        self.hand_no = 0

    async def play(self) -> None:
        self.state = {seat: PlayerState(self.START_CHIPS) for seat in self.seats}
        for hand_no in range(1, self.MAX_HANDS + 1):
            self.hand_no = hand_no
            players = [s for s in self.seats if self.state[s].chips >= self.BOOT]
            if len(players) < 2 or not any(s.user is not None and self.state[s].chips >= self.BOOT for s in self.seats):
                break
            await self.play_hand(players, hand_no - 1)
            await self.pause(3.5)

        winner = max(self.seats, key=lambda s: self.state[s].chips)
        self.turn = None
        await self.refresh(f"\N{TROPHY} **{winner.name}** wins the game with `${self.state[winner].chips}`!")

    async def play_hand(self, players: list[Seat], dealer: int) -> None:  # noqa: PLR0915
        deck = new_deck()
        self.pot = 0
        self.stake = self.BOOT
        self.reveal = False

        for seat, state in self.state.items():
            state.playing = seat in players
            state.packed = seat not in players
            state.seen = False
            state.hand = []
        for seat in players:
            state = self.state[seat]
            state.chips -= self.BOOT
            self.pot += self.BOOT
            state.hand = sort_hand([deck.pop() for _ in range(3)])

        start = (dealer + 1) % len(players)
        order = players[start:] + players[:start]
        index = 0
        await self.refresh(f"Hand **{self.hand_no}/{self.MAX_HANDS}** - everyone paid the boot of `${self.BOOT}`.")

        while True:
            live = [s for s in order if not self.state[s].packed]
            if len(live) == 1:
                winner = live[0]
                self.state[winner].chips += self.pot
                self.turn = None
                await self.refresh(f"\N{TROPHY} **{winner.name}** wins `${self.pot}` - everyone else packed.")
                return

            seat = order[index % len(order)]
            index += 1
            if self.state[seat].packed:
                continue

            self.turn = seat
            kind = await self.take_turn(seat, live)
            state = self.state[seat]
            chaal, raise_cost, new_stake = self.costs(state)

            if kind == "pack":
                state.packed = True
                message = f"**{seat.name}** packed."
            elif kind == "chaal":
                state.chips -= chaal
                self.pot += chaal
                message = f"**{seat.name}** played {'chaal' if state.seen else 'blind'} for `${chaal}`."
            elif kind == "raise":
                state.chips -= raise_cost
                self.pot += raise_cost
                self.stake = new_stake
                message = f"**{seat.name}** raised the stake to `${new_stake}`."
            else:
                state.chips -= chaal
                self.pot += chaal
                other = next(s for s in live if s is not seat)
                mine, theirs = rank_hand(state.hand), rank_hand(self.state[other].hand)
                winner = seat if mine > theirs else other
                self.state[winner].chips += self.pot
                self.reveal = True
                self.turn = None
                names = f"{HAND_NAMES[mine[0]]} vs {HAND_NAMES[theirs[0]]}"
                await self.refresh(f"**{seat.name}** asked for a show - {names}. \N{TROPHY} **{winner.name}** wins `${self.pot}`!")
                return

            await self.refresh(message)

    def costs(self, state: PlayerState) -> tuple[int, int, int]:
        multiplier = 2 if state.seen else 1
        new_stake = min(self.stake * 2, self.MAX_STAKE)
        return self.stake * multiplier, new_stake * multiplier, new_stake

    async def take_turn(self, seat: Seat, live: list[Seat]) -> str:
        state = self.state[seat]

        def allowed() -> set[str]:
            chaal, raise_cost, _ = self.costs(state)
            out = {"pack"}
            if chaal <= state.chips:
                out.add("chaal")
                if len(live) == 2:
                    out.add("show")
            if self.stake < self.MAX_STAKE and raise_cost <= state.chips:
                out.add("raise")
            return out

        def build() -> PromptSpec:
            chaal, raise_cost, _ = self.costs(state)
            ok = allowed()
            prefix = "" if state.seen else "Blind "
            buttons = []
            if not state.seen:
                buttons.append(ButtonSpec("see", "See cards", emoji="\N{EYES}"))
            buttons += [
                ButtonSpec("chaal", f"{prefix}Chaal ${chaal}", discord.ButtonStyle.success, disabled="chaal" not in ok),
                ButtonSpec("raise", f"{prefix}Raise ${raise_cost}", discord.ButtonStyle.primary, disabled="raise" not in ok),
            ]
            if len(live) == 2:
                buttons.append(ButtonSpec("show", f"Show ${chaal}", disabled="show" not in ok))
            buttons.append(ButtonSpec("pack", "Pack", discord.ButtonStyle.danger))

            status = f"Your hand: **{HAND_NAMES[rank_hand(state.hand)[0]]}**" if state.seen else "You are playing **blind** - cards hidden."
            caption = f"**Pot** `${self.pot}` \N{MIDDLE DOT} **Stake** `${self.stake}` \N{MIDDLE DOT} **Your chips** `${state.chips}`\n{status}"
            return PromptSpec(
                cards=state.hand,
                caption=caption,
                hidden=not state.seen,
                buttons=buttons,
                local={"see": lambda: setattr(state, "seen", True)},
            )

        def validate(action: Action) -> str | None:
            return None if action[0] in allowed() else "You can't do that right now."

        def ai() -> Action:
            if not state.seen and (self.stake > self.BOOT * 2 or random.random() < 0.3):
                state.seen = True
            ok = allowed()  # after deciding whether to see: seen players pay double

            choice = "chaal"
            if state.seen:
                power = strength(state.hand)
                if power < 0.25 and (self.stake >= self.BOOT * 2 or random.random() < 0.5):
                    choice = "pack"
                elif power > 0.85 and "raise" in ok and random.random() < 0.6:
                    choice = "raise"
                elif power > 0.55 and "show" in ok and random.random() < 0.5:
                    choice = "show"
            elif "raise" in ok and random.random() < 0.1:
                choice = "raise"
            elif "show" in ok and random.random() < 0.25:
                choice = "show"

            return (choice if choice in ok else "pack", ())

        action = await self.decide(
            seat,
            caption=f"{seat.mention}'s turn - pot `${self.pot}`, stake `${self.stake}`.",
            build=build,
            validate=validate,
            ai=ai,
        )
        return action[0]

    def table_view(self) -> TableView:
        seats: list[SeatView] = []
        for seat in self.seats:
            state = self.state.get(seat)
            if state is None:
                seats.append(SeatView(seat.tag))
                continue

            if not state.playing:
                badge, kind = "OUT", "neutral"
            elif state.packed:
                badge, kind = "PACKED", "neutral"
            elif state.seen:
                badge, kind = "SEEN", "info"
            else:
                badge, kind = "BLIND", "good"

            in_play = state.playing and not state.packed
            seats.append(
                SeatView(
                    seat.tag,
                    sub=f"${state.chips}",
                    cards=3 if in_play and not self.reveal else 0,
                    shown=tuple(state.hand) if self.reveal and in_play else (),
                    active=seat is self.turn,
                    dim=not in_play,
                    badge=badge,
                    badge_kind=kind,
                )
            )
        return TableView(seats, note=f"Pot ${self.pot} \N{MIDDLE DOT} Stake ${self.stake}")

    def hand_of(self, seat: Seat) -> list[str]:
        state = self.state.get(seat)
        return state.hand if state else []

    def hand_hidden(self, seat: Seat) -> bool:
        state = self.state.get(seat)
        return state is not None and not state.seen

    def idle_caption(self, seat: Seat) -> str:
        state = self.state.get(seat)
        if state is None or not state.playing:
            return "You're not in this hand."
        status = "playing **blind**" if not state.seen else "cards seen"
        return f"**Pot** `${self.pot}` \N{MIDDLE DOT} **Chips** `${state.chips}` \N{MIDDLE DOT} {status}. Waiting for your turn."
