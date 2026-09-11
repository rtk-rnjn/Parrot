from __future__ import annotations

import math
import random
from collections import Counter
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

import discord
from discord.ext import commands
from jishaku.functools import executor_function
from PIL import Image, ImageDraw, ImageFont

from core.constants import BLACK_JACK_CARDS, CARD_BACK

from .utils import DEFAULT_COLOR, BaseView, DiscordColor

if TYPE_CHECKING:
    from core import Parrot


class CardDeck:
    RANKS: ClassVar[tuple[str, ...]] = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "0", "J", "Q", "K")
    SUITS: ClassVar[tuple[str, ...]] = ("C", "D", "H", "S")

    def __init__(self, decks: int = 1) -> None:
        self.cards = [f"{rank}{suit}" for _ in range(decks) for suit in self.SUITS for rank in self.RANKS]
        random.shuffle(self.cards)

    def draw(self) -> str:
        if not self.cards:
            raise RuntimeError("The deck is empty.")
        return self.cards.pop()


def card_emoji(card: str) -> str:
    emoji = BLACK_JACK_CARDS.get(card)
    if emoji is None:
        message = f"No card emoji registered for {card!r}"
        raise KeyError(message)
    return str(emoji)


def cards_text(cards: list[str]) -> str:
    return "".join(card_emoji(card) for card in cards) or "-"


def rank_value(card: str) -> int:
    rank = card[0]
    if rank == "A":
        return 14
    if rank in {"0", "J", "Q", "K"}:
        return {"0": 10, "J": 11, "Q": 12, "K": 13}[rank]
    return int(rank)


def _straight_high(values: list[int]) -> int:
    unique = sorted(set(values))
    if len(unique) != 5:
        return 0
    if unique == [2, 3, 4, 5, 14]:
        return 5
    return unique[-1] if unique[-1] - unique[0] == 4 else 0


def _poker_score_from_groups(
    values: list[int],
    counts: Counter[int],
    groups: list[tuple[int, int]],
    straight_high: int,
    flush: bool,
) -> tuple[int, list[int]]:
    if straight_high and flush:
        return 8, [straight_high]
    if groups[0][0] == 4:
        return 7, [groups[0][1], groups[1][1]]
    if groups[0][0] == 3 and groups[1][0] == 2:
        return 6, [groups[0][1], groups[1][1]]
    if flush:
        return 5, values
    if straight_high:
        return 4, [straight_high]
    if groups[0][0] == 3:
        kickers = sorted((value for value, count in counts.items() if count == 1), reverse=True)
        return 3, [groups[0][1], *kickers]
    pairs = sorted((value for value, count in counts.items() if count == 2), reverse=True)
    if len(pairs) == 2:
        kicker = next(value for value, count in counts.items() if count == 1)
        return 2, [*pairs, kicker]
    if len(pairs) == 1:
        kickers = sorted((value for value, count in counts.items() if count == 1), reverse=True)
        return 1, [pairs[0], *kickers]
    return 0, values


def poker_score(cards: list[str]) -> tuple[int, list[int]]:
    values = sorted((rank_value(card) for card in cards), reverse=True)
    counts = Counter(values)
    groups = sorted(((count, value) for value, count in counts.items()), reverse=True)
    straight_high = _straight_high(values)
    flush = len({card[1] for card in cards}) == 1
    return _poker_score_from_groups(values, counts, groups, straight_high, flush)


def teen_patti_score(cards: list[str]) -> tuple[int, list[int]]:
    values = sorted((rank_value(card) for card in cards), reverse=True)
    counts = Counter(values)
    groups = sorted(((count, value) for value, count in counts.items()), reverse=True)
    flush = len({card[1] for card in cards}) == 1
    unique = sorted(set(values))
    is_sequence = len(unique) == 3 and unique[-1] - unique[0] == 2

    if unique == [2, 3, 14]:
        sequence_values = [3, 2, 14]
        is_sequence = True
    else:
        sequence_values = values

    if groups[0][0] == 3:
        return 6, [groups[0][1]]
    if flush and is_sequence:
        return 5, sequence_values
    if is_sequence:
        return 4, sequence_values
    if flush:
        return 3, values
    if groups[0][0] == 2:
        pair = groups[0][1]
        kicker = next(value for value, count in counts.items() if count == 1)
        return 2, [pair, kicker]
    return 1, values


class CasinoButton(discord.ui.Button["CasinoView"]):
    def __init__(self, action: str, label: str, *, style: discord.ButtonStyle = discord.ButtonStyle.primary) -> None:
        super().__init__(label=label, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        view = self.view
        if view is None or interaction.user.id != view.player.id:
            await interaction.response.send_message("This is not your game.", ephemeral=True)
            return
        if view.game.finished:
            await interaction.response.send_message("This game has already ended.", ephemeral=True)
            return
        await view.play(interaction, self.action)


class CasinoView(BaseView):
    def __init__(self, game: CasinoGame, *, timeout: float | None = 120) -> None:
        super().__init__(timeout=timeout)
        self.game = game
        self.player = game.player
        self.message: discord.Message | None = None

    async def play(self, interaction: discord.Interaction[Parrot], action: str) -> None:
        self.game.play(action)
        self.disable_all()
        await interaction.response.edit_message(embed=self.game.embed(), view=self)
        self.stop()

    async def on_timeout(self) -> None:
        if not self.game.finished:
            self.game.finished = True
            self.disable_all()
            if self.message is not None:
                await self.message.edit(embed=self.game.embed(), view=self)


class CasinoGame:
    title = "Casino"

    def __init__(self, player: discord.abc.User, *, color: DiscordColor = DEFAULT_COLOR) -> None:
        self.player = player
        self.color = color
        self.finished = False
        self.view: CasinoView | None = None
        self.message: discord.Message | None = None

    def embed(self) -> discord.Embed:
        return discord.Embed(title=self.title, color=self.color, description="Game over.")

    def play(self, action: str) -> None:
        raise NotImplementedError

    async def start(self, ctx: commands.Context[Parrot]) -> discord.Message:
        self.deal()
        if self.finished:
            self.message = await ctx.reply(embed=self.embed())
            return self.message

        self.view = CasinoView(self)
        self.message = await ctx.reply(embed=self.embed(), view=self.view)
        self.view.message = self.message
        await self.view.wait()
        return self.message

    def deal(self) -> None:
        raise NotImplementedError


class PokerGame(CasinoGame):
    title = "Five-Card Poker"
    HAND_NAMES = ("High card", "Pair", "Two pair", "Three of a kind", "Straight", "Flush", "Full house", "Four of a kind", "Straight flush")

    def deal(self) -> None:
        self.deck = CardDeck()
        self.player_cards = [self.deck.draw() for _ in range(5)]
        self.dealer_cards = [self.deck.draw() for _ in range(5)]

    async def start(self, ctx: commands.Context[Parrot]) -> discord.Message:
        self.deal()
        self.view = CasinoView(self)
        self.view.add_item(CasinoButton("draw", "Draw"))
        self.message = await ctx.reply(embed=self.embed(), view=self.view)
        self.view.message = self.message
        await self.view.wait()
        return self.message

    def play(self, action: str) -> None:
        if action == "draw":
            discard_count = min(3, max(0, 5 - len({rank_value(card) for card in self.player_cards})))
            for index in sorted(range(5), key=lambda item: rank_value(self.player_cards[item]))[:discard_count]:
                self.player_cards[index] = self.deck.draw()
            dealer_discards = sorted(range(5), key=lambda item: rank_value(self.dealer_cards[item]))[:2]
            for index in dealer_discards:
                self.dealer_cards[index] = self.deck.draw()
        self.finished = True

    def embed(self) -> discord.Embed:
        player_score = poker_score(self.player_cards)
        dealer_score = poker_score(self.dealer_cards)
        description = "Press Draw to replace up to three low cards." if not self.finished else f"**{self.result(dealer_score, player_score)}**"
        embed = discord.Embed(title=self.title, color=self.color, description=description)
        embed.add_field(name=f"Your hand \N{EM DASH} {self.HAND_NAMES[player_score[0]]}", value=cards_text(self.player_cards), inline=False)
        embed.add_field(
            name=f"Dealer hand \N{EM DASH} {self.HAND_NAMES[dealer_score[0]] if self.finished else 'hidden'}",
            value=cards_text(self.dealer_cards) if self.finished else str(CARD_BACK),
            inline=False,
        )
        return embed

    @staticmethod
    def result(dealer: tuple[int, list[int]], player: tuple[int, list[int]]) -> str:
        if player > dealer:
            return "You beat the dealer."
        if player < dealer:
            return "The dealer wins."
        return "Push: equal hands."


class TeenPattiGame(CasinoGame):
    title = "Teen Patti"
    HAND_NAMES = ("", "High card", "Pair", "Color", "Sequence", "Pure sequence", "Trail")

    def deal(self) -> None:
        self.deck = CardDeck()
        self.player_cards = [self.deck.draw() for _ in range(3)]
        self.dealer_cards = [self.deck.draw() for _ in range(3)]

    async def start(self, ctx: commands.Context[Parrot]) -> discord.Message:
        self.deal()
        self.view = CasinoView(self)
        self.view.add_item(CasinoButton("show", "Show Cards"))
        self.message = await ctx.reply(embed=self.embed(), view=self.view)
        self.view.message = self.message
        await self.view.wait()
        return self.message

    def play(self, action: str) -> None:
        if action != "show":
            raise ValueError("Unknown Teen Patti action.")
        self.finished = True

    def embed(self) -> discord.Embed:
        player_score = teen_patti_score(self.player_cards)
        dealer_score = teen_patti_score(self.dealer_cards)
        description = "Press Show Cards to reveal the dealer's hand." if not self.finished else f"**{self.result(dealer_score, player_score)}**"
        embed = discord.Embed(title=self.title, color=self.color, description=description)
        embed.add_field(name=f"Your hand \N{EM DASH} {self.HAND_NAMES[player_score[0]]}", value=cards_text(self.player_cards), inline=False)
        embed.add_field(
            name=f"Dealer hand \N{EM DASH} {self.HAND_NAMES[dealer_score[0]] if self.finished else 'hidden'}",
            value=cards_text(self.dealer_cards) if self.finished else str(CARD_BACK),
            inline=False,
        )
        return embed

    @staticmethod
    def result(dealer: tuple[int, list[int]], player: tuple[int, list[int]]) -> str:
        if player > dealer:
            return "You beat the dealer."
        if player < dealer:
            return "The dealer wins."
        return "Push: equal hands."


class BaccaratGame(CasinoGame):
    title = "Baccarat"

    def deal(self) -> None:
        deck = CardDeck(8)
        self.player_cards = [deck.draw(), deck.draw()]
        self.dealer_cards = [deck.draw(), deck.draw()]
        self.player_total = sum(min(rank_value(card), 10) for card in self.player_cards) % 10
        self.dealer_total = sum(min(rank_value(card), 10) for card in self.dealer_cards) % 10
        self.finished = True

    def play(self, action: str) -> None:
        return

    def embed(self) -> discord.Embed:
        if self.player_total > self.dealer_total:
            result = "Player wins."
        elif self.player_total < self.dealer_total:
            result = "Banker wins."
        else:
            result = "Tie."
        embed = discord.Embed(title=self.title, color=self.color, description=f"**{result}**")
        embed.add_field(name=f"Player \N{EM DASH} {self.player_total}", value=cards_text(self.player_cards), inline=False)
        embed.add_field(name=f"Banker \N{EM DASH} {self.dealer_total}", value=cards_text(self.dealer_cards), inline=False)
        return embed


class WarGame(CasinoGame):
    title = "War"

    def deal(self) -> None:
        deck = CardDeck()
        self.player_card = deck.draw()
        self.dealer_card = deck.draw()
        self.finished = True

    def play(self, action: str) -> None:
        return

    def embed(self) -> discord.Embed:
        player = rank_value(self.player_card)
        dealer = rank_value(self.dealer_card)
        result = "You win." if player > dealer else "Dealer wins." if player < dealer else "War: tie."
        embed = discord.Embed(title=self.title, color=self.color, description=f"**{result}**")
        embed.add_field(name="You", value=card_emoji(self.player_card))
        embed.add_field(name="Dealer", value=card_emoji(self.dealer_card))
        return embed


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Attempts to load a standard system font for large text, falling back to default."""
    common_fonts = [
        "arialbd.ttf",  # Windows Bold
        "DejaVuSans-Bold.ttf",  # Linux Bold
        "Helvetica-Bold.ttf",  # Mac Bold
        "arial.ttf",
        "tahoma.ttf",
    ]
    for font_name in common_fonts:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


@executor_function
def roulette_image(number: int) -> BytesIO:  # noqa: PLR0915
    # Set up a wide canvas for both Wheel and Board
    width, height = 1200, 500
    image = Image.new("RGB", (width, height), (15, 75, 40))  # Casino felt green
    draw = ImageDraw.Draw(image)

    # Colors
    GOLD = (212, 175, 55)
    RED = (227, 41, 51)
    BLACK = (35, 35, 35)
    GREEN = (0, 140, 50)
    WHITE = (245, 245, 245)
    BOARD_LINE = (200, 200, 200)

    # Fonts
    font_large = get_font(30)
    font_med = get_font(20)
    font_small = get_font(16)

    RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

    # Official European Roulette Sequence
    SEQUENCE = [
        0,
        32,
        15,
        19,
        4,
        21,
        2,
        25,
        17,
        34,
        6,
        27,
        13,
        36,
        11,
        30,
        8,
        23,
        10,
        5,
        24,
        16,
        33,
        1,
        20,
        14,
        31,
        9,
        22,
        18,
        29,
        7,
        28,
        12,
        35,
        3,
        26,
    ]

    # --- 1. DRAW THE WHEEL (Left Side) ---
    center_x, center_y = 280, 250
    radius = 210

    # Wooden Outer Rim
    draw.ellipse((center_x - radius - 15, center_y - radius - 15, center_x + radius + 15, center_y + radius + 15), fill=(80, 40, 20))
    draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), fill=GOLD)

    angle_per_slice = 360 / 37
    ball_angle_rad = 0

    for i, num in enumerate(SEQUENCE):
        start_angle = i * angle_per_slice - 90
        end_angle = (i + 1) * angle_per_slice - 90

        slice_color = GREEN if num == 0 else (RED if num in RED_NUMBERS else BLACK)

        # Draw Slice
        draw.pieslice(
            (center_x - radius + 5, center_y - radius + 5, center_x + radius - 5, center_y + radius - 5),
            start=start_angle,
            end=end_angle,
            fill=slice_color,
            outline=GOLD,
        )

        # Draw Number on Wheel
        mid_angle_rad = math.radians(start_angle + (angle_per_slice / 2))
        text_x = center_x + (radius - 35) * math.cos(mid_angle_rad)
        text_y = center_y + (radius - 35) * math.sin(mid_angle_rad)
        draw.text((text_x, text_y), str(num), fill=WHITE, font=font_small, anchor="mm")

        # Save ball position if this is the winning number
        if num == number:
            ball_angle_rad = mid_angle_rad

    # Inner wheel mechanics
    inner_rad = radius * 0.6
    draw.ellipse((center_x - inner_rad, center_y - inner_rad, center_x + inner_rad, center_y + inner_rad), fill=(40, 40, 40), outline=GOLD, width=3)
    draw.ellipse((center_x - 30, center_y - 30, center_x + 30, center_y + 30), fill=GOLD)

    # Draw the ball on the winning segment
    ball_distance = radius * 0.75
    ball_x = center_x + ball_distance * math.cos(ball_angle_rad)
    ball_y = center_y + ball_distance * math.sin(ball_angle_rad)
    draw.ellipse((ball_x - 8, ball_y - 8, ball_x + 8, ball_y + 8), fill=WHITE, outline=(200, 200, 200))

    # --- 2. DRAW THE BETTING BOARD (Right Side) ---
    board_start_x = 550
    board_start_y = 70
    cell_w, cell_h = 45, 75

    def draw_chip(cx, cy):
        """Draws a casino chip to highlight the winning spot"""
        draw.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(25, 100, 200), outline=WHITE, width=2)
        draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), outline=WHITE, width=1)

    # Draw Zero
    zero_x, zero_y = board_start_x, board_start_y
    draw.rectangle([zero_x, zero_y, zero_x + cell_w, zero_y + (cell_h * 3)], fill=GREEN, outline=BOARD_LINE, width=2)
    draw.text((zero_x + cell_w / 2, zero_y + (cell_h * 1.5)), "0", fill=WHITE, font=font_large, anchor="mm")
    if number == 0:
        draw_chip(zero_x + cell_w / 2, zero_y + (cell_h * 1.5))

    # Draw Numbers 1-36
    grid_x_start = board_start_x + cell_w
    for i in range(1, 37):
        col = (i - 1) // 3
        # Row 0 is top (3, 6, 9...), Row 2 is bottom (1, 4, 7...)
        row = 2 - ((i - 1) % 3)

        x1 = grid_x_start + col * cell_w
        y1 = board_start_y + row * cell_h
        x2 = x1 + cell_w
        y2 = y1 + cell_h

        bg_color = RED if i in RED_NUMBERS else BLACK
        draw.rectangle([x1, y1, x2, y2], fill=bg_color, outline=BOARD_LINE, width=2)
        draw.text(((x1 + x2) / 2, (y1 + y2) / 2), str(i), fill=WHITE, font=font_med, anchor="mm")

        if i == number:
            draw_chip((x1 + x2) / 2, (y1 + y2) / 2)

    # Draw 2:1 Columns (Right edge)
    col_x = grid_x_start + 12 * cell_w
    for row in range(3):
        y1 = board_start_y + row * cell_h
        draw.rectangle([col_x, y1, col_x + cell_w, y1 + cell_h], fill=(30, 90, 50), outline=BOARD_LINE, width=2)
        draw.text((col_x + cell_w / 2, y1 + cell_h / 2), "2:1", fill=WHITE, font=font_small, anchor="mm")

    # Draw Dozens (Bottom)
    dozen_y = board_start_y + 3 * cell_h
    dozen_w = cell_w * 4
    for d in range(3):
        x1 = grid_x_start + d * dozen_w
        draw.rectangle([x1, dozen_y, x1 + dozen_w, dozen_y + 50], fill=(30, 90, 50), outline=BOARD_LINE, width=2)
        label = "1st 12" if d == 0 else "2nd 12" if d == 1 else "3rd 12"
        draw.text((x1 + dozen_w / 2, dozen_y + 25), label, fill=WHITE, font=font_med, anchor="mm")

    # Draw Halves / Outside Bets (Bottommost)
    half_y = dozen_y + 50
    half_w = cell_w * 2
    outside_bets = ["1-18", "EVEN", "RED", "BLACK", "ODD", "19-36"]
    for i, bet in enumerate(outside_bets):
        x1 = grid_x_start + i * half_w
        fill_color = RED if bet == "RED" else (BLACK if bet == "BLACK" else (30, 90, 50))
        draw.rectangle([x1, half_y, x1 + half_w, half_y + 50], fill=fill_color, outline=BOARD_LINE, width=2)
        draw.text((x1 + half_w / 2, half_y + 25), bet, fill=WHITE, font=font_med, anchor="mm")

    # Return as BytesIO
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


class RouletteGame(CasinoGame):
    title = "Roulette"
    RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

    def deal(self) -> None:
        self.number: int | None = None
        self.result_color = "green"

    def play(self, action: str) -> None:
        self.number = random.randint(0, 36)
        self.result_color = "green" if self.number == 0 else "red" if self.number in self.RED_NUMBERS else "black"
        self.bet = action
        self.finished = True

    def embed(self) -> discord.Embed:
        if self.number is None:
            description = "Choose a colour to spin the wheel."
        else:
            outcome = "Win" if self.bet == self.result_color else "Lose"
            description = f"**{outcome}** \N{EM DASH} the wheel landed on `{self.number}` {self.result_color}."
        embed = discord.Embed(title=self.title, color=self.color, description=description)
        if self.number is not None:
            embed.set_image(url="attachment://roulette.png")
        return embed

    async def start(self, ctx: commands.Context[Parrot]) -> discord.Message:
        self.view = CasinoView(self)
        self.view.add_item(CasinoButton("red", "Red", style=discord.ButtonStyle.danger))
        self.view.add_item(CasinoButton("black", "Black"))
        self.view.add_item(CasinoButton("green", "Green", style=discord.ButtonStyle.success))
        self.deal()
        self.message = await ctx.reply(embed=self.embed(), view=self.view)
        self.view.message = self.message
        await self.view.wait()
        if self.number is not None and self.message is not None:
            await self.message.edit(
                embed=self.embed(),
                view=self.view,
                attachments=[discord.File(await roulette_image(self.number), filename="roulette.png")],
            )
        return self.message
