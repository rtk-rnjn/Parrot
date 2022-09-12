from __future__ import annotations

import asyncio
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import (
    Awaitable,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    overload,
)

import discord
from discord.ext import commands

from .cards import Card, create_deck
from .emojis import COLORS
from .enums import CardType, Color

E = TypeVar("E", bound="Hand")


@dataclass
class RuleSet:
    stacking: bool = True
    progressive: bool = True
    seven_o: bool = False
    jump_in: bool = False
    no_u: bool = False


class RuleSetChoice(NamedTuple):
    name: str
    description: str = "No description provided."


class HostOnlyView(discord.ui.View):
    def __init__(self, host: discord.Member, *, timeout: float = 360) -> None:
        super().__init__(timeout=timeout)
        self._view_owner: discord.Member = host

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user != self._view_owner:
            await interaction.response.send_message(
                "You are not the host of this game.", ephemeral=True
            )
            return False
        return True


class RuleSetPrompt(discord.ui.Select["RuleSetPromptingView"]):
    CHOICES = {
        "stacking": RuleSetChoice(
            "Stacking",
            "Allows the play of multiple cards that have the same value/type at once.",
        ),
        "progressive": RuleSetChoice(
            "Progressive",
            "Draw cards can be progressively stacked until one must draw.",
        ),
        "seven_o": RuleSetChoice(
            "Seven-O",
            "If you play a 7, you can swap hands. When a 0 is played, everyone passes their hands to their left.",
        ),
        "jump_in": RuleSetChoice(
            "Jump In",
            "Immediately play a card that is a duplicate of the current card, even if it isn't your turn.",
        ),
        "no_u": RuleSetChoice(
            "No U",
            "Playing a reverse card on a draw card will require the opponent to draw the cards instead.",
        ),
    }

    def __init__(self, game: UNO) -> None:
        self.game: UNO = game

        super().__init__(
            min_values=0,
            max_values=len(self.CHOICES),
            options=[
                discord.SelectOption(
                    label=v.name,
                    value=k,
                    description=v.description,
                    default=getattr(self.game.rule_set, k, False),
                )
                for k, v in self.CHOICES.items()
            ],
            placeholder="Select game rules...",
        )

    async def callback(self, interaction: discord.Interaction, /) -> None:
        values = interaction.data["values"]
        for value in self.CHOICES:
            setattr(self.game.rule_set, value, value in values)

        await interaction.response.defer()


class RuleSetPromptingView(HostOnlyView):
    def __init__(self, game: UNO) -> None:
        super().__init__(game.host, timeout=360)
        self.add_item(RuleSetPrompt(game))
        self.game: UNO = game

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success, row=1)
    async def _continue(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await self.game.queue_players()
        self.stop()


class PlayerQueueingView(discord.ui.View):
    OPENING_MESSAGE = (
        'Click the "Join" button to join this UNO game.\n'
        "Starting in 3 minutes, or if 10 players join.\n"
        "The host can also start early."
    )

    def __init__(self, game: UNO) -> None:
        self.game: UNO = game
        self.players: Set[discord.Member] = game.players
        game.players.add(self.game.host)  # Just in case
        super().__init__(timeout=180)

    async def _update(self) -> None:
        self.immediate_start.disabled = len(self.players) < 2

        await self.game._send(
            self.OPENING_MESSAGE
            + "\n\n**Players:**\n"
            + "\n".join(str(player) for player in self.players),
            view=self,
        )

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def join(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        if interaction.user in self.players:
            return await interaction.response.send_message(
                "You are already in this game.", ephemeral=True
            )

        self.players.add(interaction.user)
        await self._update()

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        if interaction.user not in self.players:
            return await interaction.response.send_message(
                "You are not in this game.", ephemeral=True
            )

        if interaction.user == self.game.host:
            return await interaction.response.send_message(
                "You cannot leave this game as you are the host.", ephemeral=True
            )

        self.players.remove(interaction.user)
        await self._update()

    @discord.ui.button(label="Start!", style=discord.ButtonStyle.primary, disabled=True)
    async def immediate_start(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        if interaction.user != self.game.host:
            return await interaction.response.send_message(
                "Only the host can start this game.", ephemeral=True
            )

        if len(self.players) < 2:
            return await interaction.response.send_message(
                "There must be at least 2 players in order to start this game.",
                ephemeral=True,
            )

        self.stop()


class WildCardSubview(discord.ui.View):
    def __init__(self, game: UNO, hand: Hand, cards: List[Card]) -> None:
        self.game: UNO = game
        self.hand: Hand = hand
        self.cards: List[Card] = cards
        super().__init__(timeout=360)

    def _update(self, color: Color) -> None:
        self.game._wild_card_color_store = color
        self.game.turn += self.game.direction
        self.game.current = self.cards[-1]

    async def handle(
        self, color: Color, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self._update(color)

        for card in self.cards:
            self.hand.remove(card)

        await self.game._update(
            f'{interaction.user.name} plays {" ".join(card.emoji for card in self.cards)}. '
            f"Color is now {button.emoji}!"
        )
        self.stop()

    @discord.ui.button(emoji="\U0001f7e5")
    async def red(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.handle(Color.red, button, interaction)

    @discord.ui.button(emoji="\U0001f7e6")
    async def blue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.handle(Color.blue, button, interaction)

    @discord.ui.button(emoji="\U0001f7e8")
    async def yellow(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.handle(Color.yellow, button, interaction)

    @discord.ui.button(emoji="\U0001f7e9")
    async def green(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.handle(Color.green, button, interaction)


class WildPlus4Subview(WildCardSubview):
    async def handle(
        self, color: Color, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self._update(color)

        for card in self.cards:
            self.hand.remove(card)
            self.game.draw_queue += 4

        await self.game._update(
            f'{interaction.user.name} plays {" ".join(card.emoji for card in self.cards)}. '
            f"Draw {self.game.draw_queue}! Color is now {button.emoji}."
        )


class CardButton(discord.ui.Button["DeckView"]):
    def __init__(self, game: UNO, card: Card, *, disabled: bool = True) -> None:
        super().__init__(emoji=card.emoji, disabled=disabled)
        self.game: UNO = game
        self.card: Card = card

    async def callback(self, interaction: discord.Interaction, /) -> None:
        await self.game.play(interaction, self.view.hand, self.card)


class DeckView(discord.ui.View):
    # This will be sent ephemerally, so
    # user checks won't be needed

    def __init__(self, game: UNO, hand: Hand) -> None:
        super().__init__(timeout=None)
        self.game: UNO = game
        self.hand: Hand = hand
        self._add_buttons()

    def _add_buttons(self) -> None:
        self.clear_items()

        for card in self.hand.cards[:25]:
            disabled = (  # TODO: Increase readability here?
                self.game.current_player != self.hand.player
                and not (self.game.rule_set.jump_in and self.game.current == card)
            ) or not self.game.can_play(card)

            self.add_item(CardButton(self.game, card, disabled=disabled))


class StackCardButton(discord.ui.Button["StackView"]):
    def __init__(self, card: Card) -> None:
        super().__init__(emoji=card.emoji)
        self.card: Card = card

    async def callback(self, interaction: discord.Interaction, /) -> None:
        # sourcery skip: invert-any-all
        self.view.cards.append(self.card)

        if total := sum(
            self.card.stackable_with(card)
            for card in self.view.hand._cards
            if not any(inner is card for inner in self.view.cards)
        ):
            term = "another card" if total == 1 else "more cards"
            view = StackView(self.view.game, self.view.hand, self.view.cards)

            await interaction.response.send_message(
                f"You can stack {term} on to your play. Click a card to "
                'stack, or "Play" to directly play without stacking further.',
                view=view,
                ephemeral=True,
            )
            await view.wait()

            self.view.cards = view.cards
            self.view.stop()
            return

        self.view.stop()


class StackDirectPlay(discord.ui.Button["StackView"]):
    def __init__(self) -> None:
        super().__init__(label="Play", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction, /) -> None:
        self.view.stop()


class StackView(discord.ui.View):
    # See comment in DeckView

    def __init__(self, game: UNO, hand: Hand, cards: List[Card]) -> None:
        super().__init__(timeout=None)
        self.game: UNO = game
        self.hand: Hand = hand
        self.cards: List[Card] = cards
        self._add_buttons()

    def _get_stackable_cards(self) -> Iterable[Card]:
        target = self.cards[-1]

        yield from (
            card
            for card in self.hand._cards
            if all(inner is not card for inner in self.cards)
            and target.stackable_with(card)
        )

    def _add_buttons(self) -> None:
        self.clear_items()

        for card in self._get_stackable_cards():
            self.add_item(StackCardButton(card))

        self.add_item(StackDirectPlay())


class ImmediatePlaySubview(discord.ui.View):
    def __init__(self, game: UNO, hand: Hand, card: Card) -> None:
        self.game: UNO = game
        self.hand: Hand = hand
        self.card: Card = card
        super().__init__(timeout=360)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.game.play(interaction, self.hand, self.card)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.game._update(f"{interaction.user.name} drew a card.")
        self.stop()


class VoteKickConfirmationView(discord.ui.View):
    def __init__(self, game: UNO, target: discord.Member) -> None:
        super().__init__(timeout=None)

        self.game: UNO = game
        self.target: discord.Member = target

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.game._vote_kicks[self.target].add(interaction.user)

        await interaction.response.send_message(
            f"{interaction.user.name} has voted to kick {self.target.name} out of this game. "
            f"({len(self.game._vote_kicks[self.target])}/{self.game.vote_kick_threshold})"
        )
        await self.game.handle_votekick(self.target)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message("Vote-kick cancelled.", ephemeral=True)
        self.stop()


class VoteKickSelect(discord.ui.Select["VoteKickView"]):
    def __init__(self, game: UNO, user: discord.Member) -> None:
        super().__init__(
            placeholder="Choose someone to vote-kick...",
            options=[
                discord.SelectOption(label=str(hand.player), value=hand.player.id)
                for hand in game.hands
                if hand.player != user
            ],
        )
        self.game: UNO = game

    async def callback(self, interaction: discord.Interaction) -> None:
        value = int(interaction.data["values"][0])
        target = discord.utils.get(self.game.hands, player__id=value).player

        if target in self.game._always_skip:
            return await interaction.response.send_message(
                "This person is not in the game.", ephemeral=True
            )

        if target in self.game._vote_kicks[target]:
            return await interaction.response.send_message(
                "You have already vote-kicked this person.", ephemeral=True
            )

        await interaction.response.send_message(
            f"Are you sure you would like like to vote-kick **{target}** out of this game?\n"
            "You cannot revoke your vote.",
            view=VoteKickConfirmationView(self.game, target),
            ephemeral=True,
        )

        self.view.stop()


class VoteKickView(discord.ui.View):
    def __init__(self, game: UNO, user: discord.Member) -> None:
        super().__init__(timeout=120)
        self.add_item(VoteKickSelect(game, user))


class GameView(discord.ui.View):
    def __init__(self, game: UNO) -> None:
        super().__init__(timeout=None)

        self._uno_lock: asyncio.Lock = asyncio.Lock()
        self.game: UNO = game

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            interaction.user not in self.game.players
            or interaction.user in self.game._always_skip
        ):
            await interaction.response.send_message(
                "You are not in this game!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="View cards")
    async def view_deck(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        await interaction.response.send_message(
            content="Click on a card button to play it.",
            view=DeckView(
                self.game, discord.utils.get(self.game.hands, player=interaction.user)
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="Draw", style=discord.ButtonStyle.green)
    async def draw(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        if self.game.current_player != interaction.user:
            return await interaction.response.send_message(
                "It isn't your turn!", ephemeral=True
            )

        hand = discord.utils.get(self.game.hands, player=interaction.user)

        # All unsafe players are now safe as they haven't been caught
        self.game._uno_safe = {
            hand.player for hand in self.game.hands if len(hand) <= 1
        }

        if self.game.draw_queue > 0:
            cards = hand.draw(self.game.draw_queue)
            if isinstance(cards, Card):
                cards = [cards]

            self.game.draw_queue = 0
            await interaction.response.send_message(
                f'You drew: {" ".join(card.emoji for card in cards)}', ephemeral=True
            )

            self.game.turn += self.game.direction
            await self.game._update(f"{interaction.user.name} drew {len(cards)} cards.")

        else:
            card = hand.draw()
            if self.game.current.match(card):
                return await interaction.response.send_message(
                    f"You drew a {card.emoji}. Would you like to play it?",
                    view=ImmediatePlaySubview(self.game, hand, card),
                    ephemeral=True,
                )

            self.game.turn += self.game.direction
            await interaction.response.send_message(
                f"You drew a {card.emoji}.", ephemeral=True
            )
            await self.game._update(f"{interaction.user.name} drew a card.")

    @discord.ui.button(label="UNO!", style=discord.ButtonStyle.primary)
    async def uno(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        async with self._uno_lock:
            if interaction.user in self.game._uno_safe:
                return await interaction.response.send_message(
                    "You are already safe from being called out!", ephemeral=True
                )

            hand = discord.utils.get(self.game.hands, player=interaction.user)
            if len(hand) != 1:
                return await interaction.response.send_message(
                    'You must only have one card in order to say "UNO".', ephemeral=True
                )

            self.game._uno_safe.add(interaction.user)
            await interaction.response.send_message(f"{interaction.user.name}: UNO!")

    @discord.ui.button(label="Call out", style=discord.ButtonStyle.primary)
    async def call_out(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        async with self._uno_lock:
            found = discord.utils.find(
                lambda hand: len(hand) == 1
                and hand.player not in self.game._uno_safe
                and hand.player != interaction.user,
                self.game.hands,
            )

            if not found:
                return await interaction.response.send_message(
                    "There is no one to call out.", ephemeral=True
                )

            await interaction.response.send_message(
                f"{interaction.user.name} calls out UNO for {found.player.name}."
            )

            found.draw(2)

    @discord.ui.button(label="Vote-kick", style=discord.ButtonStyle.danger)
    async def vote_kick(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        await interaction.response.send_message(
            "Choose the player you would like to vote-kick.",
            view=VoteKickView(self.game, interaction.user),
            ephemeral=True,
        )


class Deck:
    def __init__(self, game: UNO) -> None:
        self._internal_deck: List[Card] = []
        self.game: UNO = game
        self.reset()

    def __repr__(self) -> str:
        return f"<Deck cards={len(self)}>"

    def __len__(self) -> int:
        return len(self._internal_deck)

    def __iter__(self) -> Iterable[Card]:
        return iter(self._internal_deck)

    def shuffle(self) -> None:
        random.shuffle(self._internal_deck)

    def pop(self) -> Card:
        return self._internal_deck.pop(0)

    def reset(self) -> None:
        self._internal_deck = create_deck()


class Hand:
    def __init__(self, game: UNO, player: discord.Member) -> None:
        self.game: UNO = game
        self.player: discord.Member = player
        self._cards: List[Card] = []

    def __repr__(self) -> str:
        return f"<Hand player={self.player!r} cards={len(self)}>"

    def __len__(self) -> int:
        return len(self._cards)

    def __eq__(self: E, other: E) -> bool:
        if isinstance(other, self.__class__):
            return other.player == self.player and other.game == self.game
        return False

    def _draw_one(self) -> Card:
        card = self.game.deck.pop()
        self._cards.append(card)
        return card

    @overload
    def draw(self, amount: Literal[1] = 1, /) -> Card:
        ...

    @overload
    def draw(self, amount: int = 1, /) -> List[Card]:
        ...

    def draw(self, amount: int = 1, /) -> Union[List[Card], Card]:
        if amount == 1:
            return self._draw_one()

        return [self._draw_one() for _ in range(amount)]

    def remove(self, card: Card, /) -> None:
        self._cards.remove(card)

    @staticmethod
    def _card_sort_key(card: Card, /) -> Tuple[int, int, int]:
        return card.color.value, card.type.value, card.value or 0

    @property
    def cards(self) -> List[Card]:
        return sorted(self._cards, key=self._card_sort_key)


class UNO:
    def __init__(
        self,
        ctx: commands.Context,
        *,
        host: discord.Member = None,
        rule_set: RuleSet = None,
        players: Iterable[discord.Member] = (),
    ) -> None:
        self.ctx: commands.Context = ctx
        self.host: discord.Member = host or ctx.author

        self.rule_set: RuleSet = rule_set  # This could be None on init
        self.players: Set[discord.Member] = set(players)

        self.deck: Deck = Deck(self)
        self.hands: List[Hand] = []  # This will also determine order

        self.draw_queue: int = 0
        self.direction: int = 1

        self._turn: int = 0
        self._previous_content: str = None
        self._internal_view: GameView = None
        self._message: discord.Message = None
        self._wild_card_color_store: Color = None

        self._discard_pile: List[Card] = []
        self._uno_safe: Set[discord.Member] = set()
        self._always_skip: Set[discord.Member] = set()  # Will show as strikethrough
        self._vote_kicks: Dict[discord.Member, Set[discord.Member]] = defaultdict(set)

    def __repr__(self) -> str:
        return f"<UNO players={len(self.players)} turn={self.turn} rule_set={self.rule_set!r}>"

    @property
    def turn(self) -> int:
        return self._turn

    @turn.setter
    def turn(self, new: int) -> None:
        diff = new - self.turn

        if diff == 0:
            return

        method = int.__add__ if diff > 0 else int.__sub__

        for _ in range(abs(diff)):
            self._turn = method(self._turn, 1)

            while (
                self.current_player in self._always_skip
            ):  # Imagine if Python had do-while loops
                self._turn = method(self._turn, 1)

    @property
    def current(self) -> Optional[Card]:
        try:
            return self._discard_pile[-1]
        except IndexError:
            return None  # For readability

    @current.setter
    def current(self, new: Card) -> None:
        self._discard_pile.append(new)

    @property
    def current_hand(self) -> Hand:
        return self.hands[self.turn % len(self.hands)]

    @property
    def current_player(self) -> discord.Member:
        return self.current_hand.player

    @property
    def winner(self) -> Optional[discord.Member]:
        hand = discord.utils.find(lambda hand: len(hand) <= 0, self.hands)
        if hand is not None:
            return hand.player

    @property
    def vote_kick_threshold(self) -> int:
        # We want more than half
        return math.ceil(len(self.hands) / 2)

    def get_hand(self, user: discord.Member, /) -> Hand:
        return discord.utils.get(self.hands, player=user)

    async def _send(self, content: str = None, **kwargs) -> discord.Message:
        self._previous_content = content

        async def fallback() -> discord.Message:
            self._message = res = await self.ctx.send(content, **kwargs)
            return res

        if self._message is None:
            return await fallback()

        try:
            await self._message.edit(content=content, **kwargs)
        except discord.NotFound:
            return await fallback()

        return self._message

    async def _resend(self, content: str = None, **kwargs) -> discord.Message:
        await self._message.delete()
        return await self._send(content, **kwargs)

    async def choose_rule_set(self) -> None:
        self.rule_set = RuleSet()
        content = f"{self.host.mention}, choose the game rules you would like to use."
        view = RuleSetPromptingView(self)

        await self._send(content=content, view=view)
        await view.wait()

    async def queue_players(self) -> None:
        view = PlayerQueueingView(self)
        await self._send(content=PlayerQueueingView.OPENING_MESSAGE, view=view)
        await view._update()
        await view.wait()

        self.players = view.players

    def _deal_cards(self) -> None:
        for hand in self.hands:
            hand.draw(7)

    async def _run_initial_prompts(self) -> None:
        await self.choose_rule_set()
        self.hands = [Hand(self, player) for player in self.players]
        random.shuffle(self.hands)

    def _setup(self) -> None:
        self.deck.shuffle()
        self.current = self.deck.pop()
        self._deal_cards()
        self._internal_view = GameView(self)

    async def start(self) -> None:
        await self._run_initial_prompts()
        self._setup()
        await self._send(embed=self.build_embed(), view=self._internal_view)

    def wait(self) -> Awaitable[None]:
        return self._internal_view.wait()

    async def _update(self, content: str = None, **kwargs) -> None:
        if len(self.deck) <= 1:
            self.deck._internal_deck += self._discard_pile[:-1]
            self._discard_pile = [self._discard_pile[-1]]

        winner = self.winner
        if winner is not None:
            content = f"\U0001f389 {winner.name}: **UNO out!** {winner.mention} has won this game!"

            self._internal_view.stop()
            self._internal_view = None

        await self._resend(
            content, embed=self.build_embed(), view=self._internal_view, **kwargs
        )

    def can_play(self, card: Card, /) -> bool:
        if not self.current.match(card) and self.current.color is not Color.wild:
            return False

        if self.current.color is Color.wild and self._wild_card_color_store is not None:
            return card.color is self._wild_card_color_store or card.color is Color.wild

        return True

    def _embed_format(self, hand: Hand) -> None:
        fmt = "{}"

        if self.current_player == hand.player:
            fmt = "**{}**"
        if hand.player in self._always_skip:
            fmt = "~~{}~~"

        base = fmt.format(discord.utils.escape_markdown(hand.player.name))

        s = "s" if len(hand) != 1 else ""
        return f"{base} ({len(hand):,} card{s})"

    def build_embed(self) -> None:
        if self.current.color is not Color.wild or self._wild_card_color_store is None:
            color = COLORS[self.current.color]
        else:
            color = COLORS[self._wild_card_color_store]

        embed = discord.Embed(
            color=discord.Color.from_rgb(*color), timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=getattr(self.current, "image_url"))
        embed.description = "\n".join(map(self._embed_format, self.hands))

        embed.set_author(
            name=f"{self.current_player.name}'s turn!",
            icon_url=self.current_player.display_avatar.url,
        )

        if self.draw_queue > 0:
            if self.rule_set.progressive:
                content = f"Stack on or draw {self.draw_queue}"
            else:
                content = f"Draw {self.draw_queue}!"
            embed.set_footer(text=content)

        return embed

    async def _handle_stacks(
        self, interaction: discord.Interaction, hand: Hand, originator: Card
    ) -> List[Card]:
        if total := sum(
            originator.stackable_with(card)
            for card in hand._cards
            if card is not originator
        ):
            term = "a card" if total == 1 else "cards"
            view = StackView(self, hand, [originator])

            await interaction.response.send_message(
                f"You can stack {term} on to your play. Click a card to "
                'stack, or "Play" to directly play without stacking.',
                view=view,
                ephemeral=True,
            )

            await view.wait()
            return view.cards

        return [originator]

    async def play(
        self, interaction: discord.Interaction, hand: Hand, card: Card
    ) -> None:
        # sourcery skip: low-code-quality
        if self.current_player != hand.player:
            if self.rule_set.jump_in and self.current == card:
                await self.handle_jump_in(hand, card)
            else:
                return await interaction.response.send_message(
                    "It is not your turn.", ephemeral=True
                )

        if not self.can_play(card):
            return await interaction.response.send_message(
                "You cannot play this card.", ephemeral=True
            )

        if card not in hand._cards:
            return await interaction.response.send_message(
                "You have already discarded this card.", ephemeral=True
            )

        if self.draw_queue > 0:
            if not self.rule_set.progressive:
                return await interaction.response.send_message(
                    "You cannot play anything, you must draw instead.", ephemeral=True
                )

            can_play = (
                card.type is self.current.type is CardType.plus_2
                or card.type is CardType.plus_4
            )
            if not can_play:
                return await interaction.response.send_message(
                    "You must stack onto the draw, or draw yourself.", ephemeral=True
                )

        # All unsafe players are now safe as they haven't been caught
        self._uno_safe = {hand.player for hand in self.hands if len(hand) <= 1}

        if self.rule_set.stacking:
            cards = await self._handle_stacks(interaction, hand, card)
        else:
            cards = [card]

        if card.type is CardType.number:
            await self.handle_play(cards)

        elif card.type is CardType.reverse:
            await self.handle_reverse_card(cards)

        elif card.type is CardType.skip:
            await self.handle_skip_card(cards)

        elif card.type is CardType.plus_2:
            await self.handle_draw_2(cards)

        elif card.color is Color.wild:
            cls = WildCardSubview if card.type is CardType.wild else WildPlus4Subview
            kwargs = dict(
                content="What will the new color be?",
                view=cls(self, hand, cards),
                ephemeral=True,
            )

            try:
                await interaction.response.send_message(**kwargs)
            except (discord.InteractionResponded, discord.NotFound):
                await interaction.followup.send(**kwargs)

    # list to take care of stacks
    async def handle_play(self, cards: List[Card]) -> None:
        for card in cards:
            self.current_hand.remove(card)

        if len(cards) == 1:
            content = f"{self.current_player.name} plays a {cards[0].emoji}."
        else:
            content = f'{self.current_player.name} plays: {" ".join(card.emoji for card in cards)}'

        self.current = cards[-1]
        self.turn += self.direction
        await self._update(content)

    async def handle_jump_in(self, hand: Hand, card: Card) -> None:
        hand.remove(card)
        content = f"{hand.player.name} jumps in with a {card.emoji}."

        self.current = card
        self.turn = self.hands.index(hand)
        await self._update(content)

    async def handle_reverse_card(self, cards: List[Card]) -> None:
        for card in cards:
            self.current_hand.remove(card)

        extra = ""
        if len(cards) % 2 == 1:
            self.direction *= -1
            extra = " Direction is now reversed."

        if len(cards) == 1:
            content = f"{self.current_player.name} plays a {cards[0].emoji}."
        else:
            content = f'{self.current_player.name} plays: {" ".join(card.emoji for card in cards)}'

        self.current = cards[-1]
        self.turn += self.direction
        await self._update(content + extra)

    async def handle_skip_card(self, cards: List[Card]) -> None:
        extra = 0

        for card in cards:
            self.current_hand.remove(card)
            extra += self.direction

        if len(cards) == 1:
            content = f"{self.current_player.name} plays a {cards[0].emoji}."
        else:
            content = f'{self.current_player.name} plays: {" ".join(card.emoji for card in cards)}'

        self.current = cards[-1]
        self.turn += self.direction + extra
        await self._update(content)

    async def handle_draw_2(self, cards: List[Card]) -> None:
        for card in cards:
            self.current_hand.remove(card)
            self.draw_queue += 2

        extra = f"Draw {self.draw_queue}!"

        if len(cards) == 1:
            content = f"{self.current_player.name} plays a {cards[0].emoji}. "
        else:
            content = f'{self.current_player.name} plays: {" ".join(card.emoji for card in cards)}. '

        self.current = cards[-1]
        self.turn += self.direction
        await self._update(content + extra)

    async def handle_leave(self, hand: Hand) -> None:
        self._always_skip.add(hand.player)

        if self.current_player == hand.player:
            self.turn += self.direction

        # Put this user's cards back in the deck,
        # but don't remove them (as they will win)
        self.deck._internal_deck += hand._cards
        await self._update(self._previous_content)

    async def handle_votekick(self, user: discord.Member) -> None:
        if len(self._vote_kicks[user]) >= self.vote_kick_threshold:
            hand = discord.utils.get(self.hands, player=user)

            await self.ctx.send(f"{user.name} has been vote-kicked from the game.")
            await self.handle_leave(hand)
