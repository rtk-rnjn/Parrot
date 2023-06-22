from __future__ import annotations

import asyncio
import base64
import binascii
import colorsys
import datetime
import functools
import html
import io
import itertools
import json
import math
import operator
import os
import random
import re
import string
import time
import urllib
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
from random import choice, randint
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import aiohttp
import rapidfuzz  # type: ignore
from aiohttp import request  # type: ignore
from colorama import Fore
from PIL import Image, ImageColor

import discord
from core import Cog, Context, Parrot
from discord.ext import commands, tasks
from emojis.db.db import EMOJI_DB, Emoji
from utilities import spookifications
from utilities.constants import NEGATIVE_REPLIES, Colours, EmbeddedActivity
from utilities.converters import from_bottom, to_bottom
from utilities.img import imagine, timecard
from utilities.paginator import PaginationView

from ._effects import PfpEffects
from ._flags import Category, TriviaFlag
from ._fun_constants import (
    DEFAULT_QUESTION_LIMIT,
    DYNAMIC_QUESTIONS_FORMAT_FUNCS,
    IMAGES,
    MAX_ERROR_FETCH_TRIES,
    MAX_SQUARES,
    RESPONSES,
    RULES,
    STANDARD_VARIATION_TOLERANCE,
    THUMBNAIL_SIZE,
    TIME_LIMIT,
    TRIVIA_QUIZ_ICON,
    UWU_WORDS,
    WIKI_FEED_API_URL,
    WRONG_ANS_RESPONSE,
    QuizEntry,
)
from ._fun_utils import AnagramGame, file_safe_name, replace_many, suppress_links

COMIC_FORMAT = re.compile(r"latest|[0-9]+")
BASE_URL = "https://xkcd.com"

with open(
    Path("extra/truth.txt"), "r", encoding="utf-8", errors="ignore"
) as f:  # noqa: E741
    _truth = f.read()

with open(
    Path("extra/dare.txt"), "r", encoding="utf-8", errors="ignore"
) as g:  # noqa: E741
    _dare = g.read()

with open(Path("extra/lang.json"), "r", encoding="utf-8", errors="ignore") as lang:
    lg = json.load(lang)

with open(
    Path("extra/wyr.txt"), "r", encoding="utf-8", errors="ignore"
) as h:  # noqa: E741
    _wyr = h.read()

with open(
    Path("extra/nhi.txt"), "r", encoding="utf-8", errors="ignore"
) as i:  # noqa: E741
    _nhi = i.read()

with open(
    Path("extra/twister.txt"), "r", encoding="utf-8", errors="ignore"
) as k:  # noqa: E741
    _twister = k.read()

with open(
    Path("extra/anagram.json"), "r", encoding="utf-8", errors="ignore"
) as l:  # noqa: E741
    ANAGRAMS_ALL = json.load(l)

with open(
    Path("extra/random_sentences.txt"), "r", encoding="utf-8", errors="ignore"
) as m:
    _random_sentences = m.read().split("\n")


T = TypeVar("T")


ALL_WORDS = Path("extra/hangman_words.txt").read_text().splitlines()
GENDER_OPTIONS: Dict[str, Any] = json.loads(
    Path(r"extra/gender_options.json").read_text("utf8")
)


class Fun(Cog):
    """Parrot gives you huge amount of fun commands, so that you won't get bored"""

    def __init__(self, bot: Parrot):
        self.bot = bot

        self.game_status: Dict[
            int, bool
        ] = {}  # A variable to store the game status: either running or not running.
        self.game_owners: Dict[
            int, discord.Member
        ] = (
            {}
        )  # A variable to store the person's ID who started the quiz game in a channel.
        with open(Path(r"extra/ryanzec_colours.json")) as f:
            self.colour_mapping: dict = json.load(f)
            del self.colour_mapping["_"]  # Delete source credit entry
        self.questions = self.load_questions()
        self.question_limit = 0
        self.games: Dict[int, AnagramGame] = {}

        self.player_scores = defaultdict(
            int
        )  # A variable to store all player's scores for a bot session.
        self.game_player_scores: Dict[
            int, Dict[discord.Member, int]
        ] = {}  # A variable to store temporary game player's scores.
        self.latest_comic_info: Dict[str, Union[int, str]] = {}
        self.categories = {
            "general": "Test your general knowledge.",
            "retro": "Questions related to retro gaming.",
            "math": "General questions about mathematics ranging from grade 8 to grade 12.",
            "science": "Put your understanding of science to the test!",
            "cs": "A large variety of computer science questions.",
            "python": "Trivia on our amazing language, Python!",
            "wikipedia": "Guess the title of random wikipedia passages.",
        }
        self.get_latest_comic_info.start()
        self.get_wiki_questions.start()

        self.ON_TESTING = False

    async def send_colour_response(
        self, ctx: Context, rgb: Tuple[int, int, int]
    ) -> None:
        """Create and send embed from user given colour information."""
        name = self._rgb_to_name(rgb)
        try:
            colour_or_color = ctx.invoked_parents[0]
        except IndexError:
            colour_or_color = "colour"

        colour_mode = ctx.invoked_with
        if colour_mode == "random":
            colour_mode = colour_or_color
            input_colour = name
        elif colour_mode in ("colour", "color"):
            input_colour = ctx.kwargs["colour_input"]
        elif colour_mode == "name":
            input_colour = ctx.kwargs["user_colour_name"]
        elif colour_mode == "hex":
            input_colour = ctx.args[2:][0]
            if len(input_colour) > 7:
                input_colour = input_colour[:-2]
        else:
            input_colour = tuple(ctx.args[2:])

        if colour_mode not in ("name", "hex", "random", "color", "colour"):
            colour_mode = colour_mode.upper()
        else:
            colour_mode = colour_mode.title()

        colour_embed = discord.Embed(
            title=f"{name or input_colour}",
            description=f"{colour_or_color.title()} information for {colour_mode} `{input_colour or name}`.",
            colour=discord.Color.from_rgb(*rgb),
        )
        colour_conversions = self.get_colour_conversions(rgb)
        for colour_space, value in colour_conversions.items():
            colour_embed.add_field(name=colour_space, value=f"`{value}`", inline=True)

        thumbnail = Image.new("RGB", THUMBNAIL_SIZE, color=rgb)
        buffer = io.BytesIO()

        await ctx.bot.func(thumbnail.save, buffer, "PNG")
        await ctx.bot.func(buffer.seek, 0)
        thumbnail_file = discord.File(buffer, filename="colour.png")

        colour_embed.set_thumbnail(url="attachment://colour.png")

        msg: Optional[discord.Message] = await ctx.send(
            file=thumbnail_file, embed=colour_embed
        )

        assert msg is not None

        if isinstance(msg, discord.Message):
            await msg.add_reaction("\N{HAMMER AND PICK}")

        def check(r: discord.Reaction, u: discord.User) -> bool:
            return (
                u.id == ctx.author.id
                and str(r.emoji) == "\N{HAMMER AND PICK}"
                and r.message.id == msg.id
            )

        try:
            await ctx.wait_for("reaction_add", timeout=30, check=check)
            res = await ctx.prompt("Do you want to create a role of that color?")
            if res and colour_embed.title is not None:
                await self._create_role_on_clr(
                    ctx=ctx, rgb=rgb, color_name=colour_embed.title
                )
            else:
                return
        except asyncio.TimeoutError:
            return

    def get_colour_conversions(self, rgb: Tuple[int, int, int]) -> Dict[str, Any]:
        """Create a dictionary mapping of colour types and their values."""
        colour_name = self._rgb_to_name(rgb)
        if colour_name is None:
            colour_name = "No match found"
        return {
            "RGB": rgb,
            "HSV": self._rgb_to_hsv(rgb),
            "HSL": self._rgb_to_hsl(rgb),
            "CMYK": self._rgb_to_cmyk(rgb),
            "Hex": self._rgb_to_hex(rgb),
            "Name": colour_name,
        }

    @staticmethod
    def _rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Convert RGB values to HSV values."""
        rgb_list = [val / 255 for val in rgb]
        h, s, v = colorsys.rgb_to_hsv(*rgb_list)
        return round(h * 360), round(s * 100), round(v * 100)

    @staticmethod
    def _rgb_to_hsl(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Convert RGB values to HSL values."""
        rgb_list = [val / 255.0 for val in rgb]
        h, l, s = colorsys.rgb_to_hls(*rgb_list)  # noqa: E741
        return round(h * 360), round(s * 100), round(l * 100)

    @staticmethod
    def _rgb_to_cmyk(rgb: Tuple[int, int, int]) -> Tuple[int, int, int, int]:
        """Convert RGB values to CMYK values."""
        rgb_list = [val / 255.0 for val in rgb]
        if not any(rgb_list):
            return 0, 0, 0, 100
        k = 1 - max(rgb_list)
        c = round((1 - rgb_list[0] - k) * 100 / (1 - k))
        m = round((1 - rgb_list[1] - k) * 100 / (1 - k))
        y = round((1 - rgb_list[2] - k) * 100 / (1 - k))
        return c, m, y, round(k * 100)

    @staticmethod
    def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB values to HEX code."""
        hex_ = "".join([hex(val)[2:].zfill(2) for val in rgb])
        return f"#{hex_}".upper()

    def _rgb_to_name(self, rgb: Tuple[int, int, int]) -> Optional[str]:
        """Convert RGB values to a fuzzy matched name."""
        input_hex_colour = self._rgb_to_hex(rgb)
        try:
            match, certainty, _ = rapidfuzz.process.extractOne(
                query=input_hex_colour,
                choices=self.colour_mapping.values(),
                score_cutoff=80,
            )
            colour_name = [
                name
                for name, hex_code in self.colour_mapping.items()
                if hex_code == match
            ][0]
        except TypeError:
            colour_name = None
        return colour_name

    def match_colour_name(self, ctx: Context, input_colour_name: str) -> Optional[str]:
        """Convert a colour name to HEX code."""
        try:
            match, certainty, _ = rapidfuzz.process.extractOne(
                query=input_colour_name,
                choices=self.colour_mapping.keys(),
                score_cutoff=80,
            )
        except (ValueError, TypeError):
            return None
        return f"#{self.colour_mapping[match]}"

    async def cog_unload(self) -> None:
        """Cancel `get_wiki_questions` task when Cog will unload."""
        self.get_wiki_questions.cancel()
        self.get_latest_comic_info.cancel()

    @staticmethod
    def create_embed(tries: int, user_guess: str) -> discord.Embed:
        """
        Helper method that creates the embed where the game information is shown.
        This includes how many letters the user has guessed so far, and the hangman photo itself.
        """
        hangman_embed = discord.Embed(
            title="Hangman",
            color=Colours.python_blue,
        )
        hangman_embed.set_image(url=IMAGES[tries])
        hangman_embed.add_field(
            name=f"You've guessed `{user_guess}` so far.",
            value="Guess the word by sending a message with a letter!",
        )
        hangman_embed.set_footer(
            text=f"Tries remaining: {tries} | You have 60s to guess."
        )
        return hangman_embed

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="fun", id=892432619374014544)

    async def _get_discord_message(
        self, ctx: Context, text: str
    ) -> Union[discord.Message, str, None]:
        """
        Attempts to convert a given `text` to a discord Message object and return it.
        Conversion will succeed if given a discord Message ID or link.
        Returns `text` if the conversion fails.
        """
        try:
            msg = await commands.MessageConverter().convert(ctx, text)
        except commands.BadArgument:
            msg = await self.bot.get_or_fetch_message(ctx.channel, text, partial=False)
            return msg if msg is not None else text  # type: ignore
        return msg

    async def _get_text_and_embed(
        self, ctx: Context, text: str
    ) -> Tuple[str, Optional[discord.Embed]]:
        embed = None

        assert isinstance(ctx.author, discord.Member)

        msg = await self._get_discord_message(ctx, text)
        # Ensure the user has read permissions for the channel the message is in
        if (
            isinstance(msg, discord.Message)
            and msg.channel.permissions_for(ctx.author).read_messages
        ):
            text = msg.clean_content
            # Take first embed because we can't send multiple embeds
            if msg.embeds:
                embed = msg.embeds[0]

        return (text, embed)

    def _convert_embed(
        self,
        func: Callable[[str], str],
        embed: discord.Embed,
    ) -> discord.Embed:
        """
        Converts the text in an embed using a given conversion function, then return the embed.
        Only modifies the following fields: title, description, footer, fields
        """
        embed_dict = embed.to_dict()

        embed_dict["title"] = func(embed_dict.get("title", ""))
        embed_dict["description"] = func(embed_dict.get("description", ""))

        if "footer" in embed_dict:
            embed_dict["footer"]["text"] = func(embed_dict["footer"].get("text", ""))

        if "fields" in embed_dict:
            for field in embed_dict["fields"]:
                field["name"] = func(field.get("name", ""))
                field["value"] = func(field.get("value", ""))

        return discord.Embed.from_dict(embed_dict)

    @tasks.loop(minutes=30)
    async def get_latest_comic_info(self) -> None:
        """Refreshes latest comic's information ever 30 minutes. Also used for finding a random comic."""
        async with self.bot.http_session.get(f"{BASE_URL}/info.0.json") as resp:
            if resp.status == 200:
                self.latest_comic_info = await resp.json()

    @tasks.loop(hours=24.0)
    async def get_wiki_questions(self) -> None:
        """Get yesterday's most read articles from wikipedia and format them like trivia questions."""
        error_fetches = 0
        wiki_questions = []
        # trivia_quiz.json follows a pattern, every new category starts with the next century.
        start_id = 501
        yesterday = datetime.datetime.strftime(
            datetime.datetime.now() - datetime.timedelta(1), "%Y/%m/%d"
        )

        while error_fetches < MAX_ERROR_FETCH_TRIES:
            async with self.bot.http_session.get(
                url=WIKI_FEED_API_URL.format(date=yesterday)
            ) as r:
                if r.status != 200:
                    error_fetches += 1
                    continue
                raw_json = await r.json()
                articles_raw = raw_json["mostread"]["articles"]

                for article in articles_raw:
                    question = article.get("extract")
                    if not question:
                        continue

                    # Normalize the wikipedia article title to remove all punctuations from it
                    for word in re.split(r"[\s-]", title := article["normalizedtitle"]):
                        cleaned_title = re.sub(
                            rf"\b{word.strip(string.punctuation)}\b",
                            word,
                            title,
                            flags=re.IGNORECASE,
                        )

                    # Since the extract contains the article name sometimes this would replace all the matching words
                    # in that article with *** of that length.
                    # NOTE: This removes the "answer" for 99% of the cases, but sometimes the wikipedia article is
                    # very different from the words in the extract, for example the title would be the nickname of a
                    # person (Bob Ross) whereas in the extract it would the full name (Robert Norman Ross) so it comes
                    # out as (Robert Norman ****) and (Robert Norman Ross) won't be a right answer :(
                    for word in re.split(r"[\s-]", cleaned_title):
                        word = word.strip(string.punctuation)
                        secret_word = r"\*" * len(word)
                        question = re.sub(
                            rf"\b{word}\b",
                            f"**{secret_word}**",
                            question,
                            flags=re.IGNORECASE,
                        )

                    formatted_article_question = {
                        "id": start_id,
                        "question": f"Guess the title of the Wikipedia article.\n\n{question}",
                        "answer": cleaned_title,
                        "info": article["extract"],
                    }
                    start_id += 1
                    wiki_questions.append(formatted_article_question)

                # If everything has gone smoothly until now, we can break out of the while loop
                break

        if error_fetches < MAX_ERROR_FETCH_TRIES:
            self.questions["wikipedia"] = wiki_questions.copy()
        else:
            del self.categories["wikipedia"]

    @staticmethod
    def load_questions() -> dict:
        """Load the questions from the JSON file."""
        with open(r"extra/trivia_questions.json") as f:
            return json.load(f)

    @commands.command(name="xkcd")
    async def fetch_xkcd_comics(self, ctx: Context, comic: Optional[str]) -> None:
        """
        Getting an xkcd comic's information along with the image.
        To get a random comic, don't type any number as an argument. To get the latest, type 'latest'.
        """
        embed = discord.Embed(title=f"XKCD comic '{comic}'")

        embed.colour = Colours.soft_red

        if comic and (comic := re.match(COMIC_FORMAT, comic)) is None:
            embed.description = (
                "Comic parameter should either be an integer or 'latest'."
            )
            await ctx.send(embed=embed)
            return

        comic = randint(1, self.latest_comic_info["num"]) if comic is None else comic[0]

        if comic == "latest":
            info = self.latest_comic_info
        else:
            async with self.bot.http_session.get(
                f"{BASE_URL}/{comic}/info.0.json"
            ) as resp:
                if resp.status == 200:
                    info = await resp.json()
                else:
                    embed.title = f"XKCD comic #{comic}"
                    embed.description = (
                        f"{resp.status}: Could not retrieve xkcd comic #{comic}."
                    )
                    await ctx.send(embed=embed)
                    return

        embed.title = f"XKCD comic #{info['num']}"
        embed.description = f"{info['alt']}"  # fuck you pycord
        embed.url = f"{BASE_URL}/{info['num']}"

        if info["img"][-3:] in ("jpg", "png", "gif"):
            embed.set_image(url=info["img"])
            date = f"{info['year']}/{info['month']}/{info['day']}"
            embed.set_footer(text=f"{date} - #{info['num']}, '{info['safe_title']}'")
            embed.colour = Colours.soft_green
        else:
            embed.description = (
                "The selected comic is interactive, and cannot be displayed within an embed.\n"
                f"Comic can be viewed [here](https://xkcd.com/{info['num']})."
            )

        await ctx.send(embed=embed)

    @commands.command(name="anagram", aliases=("anag", "gram", "ag"))
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def anagram_command(self, ctx: Context) -> None:
        """
        Given shuffled letters, rearrange them into anagrams.
        Show an embed with scrambled letters which if rearranged can form words.
        After a specific amount of time, list the correct answers and whether someone provided a
        correct answer.
        """
        if self.games.get(ctx.channel.id):
            await ctx.send("An anagram is already being solved in this channel!")
            return

        scrambled_letters, correct = random.choice(list(ANAGRAMS_ALL.items()))

        game = AnagramGame(scrambled_letters, correct)
        self.games[ctx.channel.id] = game

        anagram_embed = discord.Embed(
            title=f"Find anagrams from these letters: '{scrambled_letters.upper()}'",
            description=f"You have {TIME_LIMIT} seconds to find correct words.",
            colour=Colours.purple,
        )

        await ctx.send(embed=anagram_embed)
        await ctx.release(TIME_LIMIT)

        if game.winners:
            win_list = ", ".join(game.winners)
            content = f"Well done {win_list} for getting it right!"
        else:
            content = "Nobody got it right."

        answer_embed = discord.Embed(
            title=f"The words were:  `{'`, `'.join(ANAGRAMS_ALL[game.scrambled])}`!",
            colour=Colours.pink,
        )

        await ctx.send(content, embed=answer_embed)

        # Game is finished, let's remove it from the dict
        self.games.pop(ctx.channel.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Check a message for an anagram attempt and pass to an ongoing game."""
        if message.author.bot or not message.guild:
            return

        if game := self.games.get(message.channel.id):
            await game.message_creation(message)
        else:
            return

    async def __issue_trivia_token(self, ctx: Context) -> Optional[str]:
        request_token = await self.bot.http_session.get(
            "https://opentdb.com/api_token.php?command=request"
        )
        if request_token.status != 200:
            await ctx.send(
                f"{ctx.author.mention} Could not get a token from the API. Please try again later"
            )
            return None
        _data = await request_token.json()
        token = _data["token"]
        try:
            await ctx.author.send(
                f"Your session Token: `{token}`\n"
                "Session Tokens are unique keys that will help keep track of the questions.\n"
                "Bot will never give you the same question twice. If you use token as flag.\n"
                f"> Usage: `{ctx.clean_prefix}trivia --token {token}`\n"
                "Token will be reset in 6hour of inactivity",
                delete_after=300,
                view=ctx.send_view(label=f"Sent from {ctx.guild}"),
            )
        except discord.Forbidden:
            await ctx.send(
                f"{ctx.author.mention} Could not send you a message. Please check your privacy settings."
            )
            return None

        return token

    @commands.group(
        name="trivia",
        invoke_without_command=True,
    )
    async def triva_quiz(self, ctx: Context, *, flag: TriviaFlag) -> None:
        """Trivia quiz commands.

        Available flags:
            `--token`: Token to use in the quiz.
            `--category`: Category to use in the quiz.
            `--difficulty`: Difficulty to use in the quiz.
            `--type`: Type of question to use in the quiz.
            `--amount`: Amount of questions to use in the quiz.
        """
        if ctx.channel.id not in self.game_status:
            self.game_status[ctx.channel.id] = False

        if ctx.channel.id not in self.game_player_scores:
            self.game_player_scores[ctx.channel.id] = {}

        # Stop game if running.
        if self.game_status[ctx.channel.id]:
            await ctx.send(f"Game is already running... do `{ctx.prefix}quiz stop`")
            return

        # token = flag.token or await self.__issue_trivia_token(ctx)

        PAYLOAD: Dict[str, Any] = {}

        # if token is not None:
        #     PAYLOAD["token"] = token

        if flag.category:
            if cat := getattr(Category, flag.category.replace(" ", "_").title()):
                PAYLOAD["category"] = cat

        if flag.difficulty:
            PAYLOAD["difficulty"] = flag.difficulty

        if flag._type:
            PAYLOAD["type"] = flag._type

        if flag.number:
            PAYLOAD["amount"] = flag.number
            self.question_limit = flag.number

        res = await self.bot.http_session.get(
            "https://opentdb.com/api.php",
            params=PAYLOAD,
            headers={
                "Accept": "application/json",
                "User-Agent": f"Discord Bot '{self.bot.user}' @ {self.bot.github}",
            },
        )
        if res.status != 200:
            return await ctx.error(
                f"{ctx.author.mention} Could not get a question from the API. Please try again later"
            )

        data = await res.json()
        if data["response_code"] in {3, 4}:
            # token expired or invalid
            return await ctx.error(
                f"{ctx.author.mention} Token expired or invalid. Please try again."
            )

        if data["response_code"] in {1, 2}:
            # invalid parameter(s) or no questions found
            return await ctx.error(
                f"{ctx.author.mention} no questions found (possible reason: Invalid Parameter(s)). Please try again."
            )

        self.game_status[ctx.channel.id] = True
        self.game_owners[ctx.channel.id] = ctx.author

        embed = self.make_start_embed(PAYLOAD.get("category", "Any"))
        await ctx.send(embed=embed)
        await ctx.release(10)
        for index, question_data in enumerate(data["results"], start=1):
            if not self.game_status[ctx.channel.id]:
                break

            _option: List[str] = question_data["incorrect_answers"]
            _option.append(question_data["correct_answer"])
            options = _option.copy()
            random.shuffle(options)
            question = html.escape(question_data["question"], quote=False)

            _value_str = ""
            for i in options:
                _value_str += f"\N{BULLET}`{html.escape(i, quote=False)}`\n"

            embed = (
                discord.Embed(
                    title=f"Question #{index}",
                    description=question,
                )
                .add_field(
                    name="Options",
                    value=_value_str,
                    inline=False,
                )
                .set_footer(text=f"{ctx.author.name}")
                .set_thumbnail(url=TRIVIA_QUIZ_ICON)
            )
            await ctx.send(embed=embed)

            def check(m: discord.Message) -> bool:
                return (m.channel.id == ctx.channel.id) and rapidfuzz.fuzz.ratio(
                    question_data["correct_answer"].lower(), m.content.lower()
                ) > 75

            try:
                msg: discord.Message = await ctx.wait_for(
                    "message",
                    timeout=30,
                    check=check,
                )
            except asyncio.TimeoutError:
                if not self.game_status[ctx.channel.id]:
                    break

                embed = discord.Embed(
                    title="Correct answere is `{}`".format(
                        question_data["correct_answer"]
                    ),
                )
                await ctx.send(embed=embed)
                continue

            embed: discord.Embed = discord.Embed(
                title="You got it! The correct answer is `{}`".format(
                    question_data["correct_answer"]
                )
            )
            if ctx.channel.id in self.game_player_scores:
                if msg.author in self.game_player_scores[ctx.channel.id]:
                    self.game_player_scores[ctx.channel.id][msg.author] += 100
                else:
                    self.game_player_scores[ctx.channel.id][msg.author] = 100
            else:
                self.game_player_scores[ctx.channel.id] = {msg.author: 100}

            if msg.author in self.player_scores:
                self.player_scores[msg.author] += 100
            else:
                self.player_scores[msg.author] = 100

            await ctx.send(embed=embed)
            await ctx.send(
                f"{msg.author.mention} got the correct answer :tada: 100 points!"
            )
            await self.send_score(ctx.channel, self.game_player_scores[ctx.channel.id])
            await ctx.release()
        else:
            await self.declare_winner(
                ctx.channel, self.game_player_scores[ctx.channel.id]
            )

        self.game_status[ctx.channel.id] = False
        self.game_player_scores[ctx.channel.id] = {}
        with suppress(KeyError):
            del self.game_owners[ctx.channel.id]

    @triva_quiz.command(name="reset_token", aliases=["reset", "reset-token"])
    async def trivia_token(self, ctx: Context, *, token: str) -> None:
        """Reset a token.

        This will reset the token to be used in the quiz.
        """
        res = await self.bot.http_session.get(
            f"https://opentdb.com/api_token.php?command=reset&token={token}",
        )
        data = await res.json()
        if data is None:
            await ctx.error(
                f"{ctx.author.mention} Could not reset token. Please try again later"
            )
        if data["response_code"] == 0:
            await ctx.send(
                f"{ctx.author.mention} Token reset successfully. You can now use it in the quiz."
            )
        else:
            await ctx.error(
                f"{ctx.author.mention} Could not reset token. Please try again later"
            )

    @triva_quiz.command(name="new_token", aliases=["new", "new-token", "token"])
    async def new_trivia_token(self, ctx: Context) -> None:
        """Register a new token for trivia"""
        await self.__issue_trivia_token(ctx)

    @triva_quiz.command(name="stop", aliases=["end", "cancel"])
    async def trivia_stop(self, ctx: Context) -> None:
        """Stop the quiz."""
        await self.stop_quiz(ctx)

    @commands.group(name="quiz", invoke_without_command=True, hidden=True)
    async def quiz_game(
        self,
        ctx: Context,
        category: Optional[str] = None,
        questions: Optional[int] = None,
    ) -> None:
        """
        Start a quiz!
        Questions for the quiz can be selected from the following categories:
        - general: Test your general knowledge.
        - retro: Questions related to retro gaming.
        - math: General questions about mathematics ranging from grade 8 to grade 12.
        - science: Put your understanding of science to the test!
        - cs: A large variety of computer science questions.
        - python: Trivia on our amazing language, Python!
        - wikipedia: Guess the title of random wikipedia passages.
        (More to come!)
        """
        if ctx.channel.id not in self.game_status:
            self.game_status[ctx.channel.id] = False

        if ctx.channel.id not in self.game_player_scores:
            self.game_player_scores[ctx.channel.id] = {}

        # Stop game if running.
        if self.game_status[ctx.channel.id]:
            await ctx.send(f"Game is already running... do `{ctx.prefix}quiz stop`")
            return

        # Send embed showing available categories if inputted category is invalid.
        if category is None:
            category = random.choice(list(self.categories))

        category = category.lower()
        if category not in self.categories:
            embed = self.category_embed()
            await ctx.send(embed=embed)
            return

        topic = self.questions[category]
        topic_length = len(topic)

        if questions is None:
            self.question_limit = min(DEFAULT_QUESTION_LIMIT, topic_length)
        else:
            if questions > topic_length:
                await ctx.send(
                    embed=self.make_error_embed(
                        f"This category only has {topic_length} questions. "
                        "Please input a lower value!"
                    )
                )
                return

            if questions < 1:
                await ctx.send(
                    embed=self.make_error_embed(
                        "You must choose to complete at least one question. "
                        f"(or enter nothing for the default value of {DEFAULT_QUESTION_LIMIT} questions)"
                    )
                )
                return

            self.question_limit = questions

        # Start game if not running.
        if not self.game_status[ctx.channel.id]:
            self.game_owners[ctx.channel.id] = ctx.author
            self.game_status[ctx.channel.id] = True
            start_embed = self.make_start_embed(category)

            await ctx.send(embed=start_embed)  # send an embed with the rules
            await ctx.release(5)

        done_questions: List[int] = []
        hint_no = 0
        quiz_entry: QuizEntry = None  # type: ignore

        while self.game_status[ctx.channel.id]:
            # Exit quiz if number of questions for a round are already sent.
            if len(done_questions) == self.question_limit and hint_no == 0:
                await ctx.send("The round has ended.")
                await self.declare_winner(
                    ctx.channel, self.game_player_scores[ctx.channel.id]
                )

                self.game_status[ctx.channel.id] = False
                del self.game_owners[ctx.channel.id]
                self.game_player_scores[ctx.channel.id] = {}

                break

            # If no hint has been sent or any time alert. Basically if hint_no = 0  means it is a new question.
            if hint_no == 0:
                # Select a random question which has not been used yet.
                while True:
                    question_dict = random.choice(topic)
                    if question_dict["id"] not in done_questions:
                        done_questions.append(question_dict["id"])
                        break
                    await ctx.release(0)

                if "dynamic_id" not in question_dict:
                    quiz_entry = QuizEntry(
                        question_dict["question"],
                        quiz_answers
                        if isinstance(quiz_answers := question_dict["answer"], list)
                        else [quiz_answers],
                        STANDARD_VARIATION_TOLERANCE,
                    )
                else:
                    format_func = DYNAMIC_QUESTIONS_FORMAT_FUNCS[
                        question_dict["dynamic_id"]
                    ]
                    quiz_entry = format_func(
                        question_dict["question"],
                        question_dict["answer"],
                    )

                embed = discord.Embed(
                    colour=Colours.gold,
                    title=f"Question #{len(done_questions)}",
                    description=f"{quiz_entry.question}",  # fuck you pycord
                )

                if img_url := question_dict.get("img_url"):
                    embed.set_image(url=img_url)

                await ctx.send(embed=embed)

            def check(m: discord.Message) -> bool:
                return (m.channel.id == ctx.channel.id) and any(
                    rapidfuzz.fuzz.ratio(answer.lower(), m.content.lower())
                    > quiz_entry.var_tol
                    for answer in quiz_entry.answers
                )

            try:
                msg: discord.Message = await ctx.wait_for(
                    "message", check=check, timeout=10
                )
            except asyncio.TimeoutError:
                # In case of TimeoutError and the game has been stopped, then do nothing.
                if not self.game_status[ctx.channel.id]:
                    break

                if hint_no < 2:
                    hint_no += 1

                    if "hints" in question_dict:
                        hints = question_dict["hints"]

                        await ctx.send(f"**Hint #{hint_no}\n**{hints[hint_no - 1]}")
                    else:
                        await ctx.send(f"{30 - hint_no * 10}s left!")

                # Once hint or time alerts has been sent 2 times, the hint_no value will be 3
                # If hint_no > 2, then it means that all hints/time alerts have been sent.
                # Also means that the answer is not yet given and the bot sends the answer and the next question.
                else:
                    if self.game_status[ctx.channel.id] is False:
                        break

                    response = random.choice(WRONG_ANS_RESPONSE)
                    await ctx.send(response)

                    await self.send_answer(
                        ctx.channel,
                        quiz_entry.answers,
                        False,
                        question_dict,
                        self.question_limit - len(done_questions),
                    )
                    await ctx.release(1)

                    hint_no = 0  # Reset the hint counter so that on the next round, it's in the initial state

                    await self.send_score(
                        ctx.channel, self.game_player_scores[ctx.channel.id]
                    )
                    await ctx.release(2)
            else:
                if self.game_status[ctx.channel.id] is False:
                    break

                points = 100 - 25 * hint_no
                if msg.author in self.game_player_scores[ctx.channel.id]:
                    self.game_player_scores[ctx.channel.id][msg.author] += points
                else:
                    self.game_player_scores[ctx.channel.id][msg.author] = points

                # Also updating the overall scoreboard.
                if msg.author in self.player_scores:
                    self.player_scores[msg.author] += points
                else:
                    self.player_scores[msg.author] = points

                hint_no = 0

                await ctx.send(
                    f"{msg.author.mention} got the correct answer :tada: {points} points!"
                )

                await self.send_answer(
                    ctx.channel,
                    quiz_entry.answers,
                    True,
                    question_dict,
                    self.question_limit - len(done_questions),
                )
                await self.send_score(
                    ctx.channel, self.game_player_scores[ctx.channel.id]
                )

                await ctx.release(2)
            await ctx.release()

    def make_start_embed(self, category: str) -> discord.Embed:
        """Generate a starting/introduction embed for the quiz."""
        rules = "\n".join(
            [f"{index}: {rule}" for index, rule in enumerate(RULES, start=1)]
        )

        start_embed = discord.Embed(
            title="Quiz game Starting!!",
            description=(
                f"Each game consists of {self.question_limit} questions.\n"
                f"**Rules :**\n{rules}"
                f"\n **Category** : {category}"
            ),
            colour=Colours.blue,
        )
        start_embed.set_thumbnail(url=TRIVIA_QUIZ_ICON)

        return start_embed

    @staticmethod
    def make_error_embed(desc: str) -> discord.Embed:
        """Generate an error embed with the given description."""
        return discord.Embed(
            colour=Colours.soft_red,
            title=random.choice(NEGATIVE_REPLIES),
            description=f"{desc}",  # fuck you pycord
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def hangman(
        self,
        ctx: Context,
        min_length: Optional[int] = 0,
        max_length: Optional[int] = 25,
        min_unique_letters: Optional[int] = 0,
        max_unique_letters: Optional[int] = 25,
    ) -> None:
        """
        Play hangman against the bot, where you have to guess the word it has provided!
        The arguments for this command mean:
        - min_length: the minimum length you want the word to be (i.e. 2)
        - max_length: the maximum length you want the word to be (i.e. 5)
        - min_unique_letters: the minimum unique letters you want the word to have (i.e. 4)
        - max_unique_letters: the maximum unique letters you want the word to have (i.e. 7)
        """
        # Filtering the list of all words depending on the configuration
        filtered_words = [
            word
            for word in ALL_WORDS
            if min_length < len(word) < max_length
            and min_unique_letters < len(set(word)) < max_unique_letters
        ]

        if not filtered_words:
            filter_not_found_embed = discord.Embed(
                title=choice(NEGATIVE_REPLIES),
                description="No words could be found that fit all filters specified.",
                color=Colours.soft_red,
            )
            await ctx.send(
                content=f"{ctx.author.mention}", embed=filter_not_found_embed
            )
            return

        word = choice(filtered_words)
        # `pretty_word` is used for comparing the indices where the guess of the user is similar to the word
        # The `user_guess` variable is prettified by adding spaces between every dash, and so is the `pretty_word`
        pretty_word = "".join([f"{letter} " for letter in word])[:-1]
        user_guess = ("_ " * len(word))[:-1]
        tries = 6
        guessed_letters = set()

        def check(msg: discord.Message) -> bool:
            return msg.author == ctx.author and msg.channel == ctx.channel

        original_message: discord.Message = await ctx.send(
            content=f"{ctx.author.mention}",
            embed=discord.Embed(
                title="Hangman", description="Loading game...", color=Colours.soft_green
            ),
        )

        # Game loop
        while user_guess.replace(" ", "") != word:
            # Edit the message to the current state of the game
            await original_message.edit(
                content=f"{ctx.author.mention}",
                embed=self.create_embed(tries, user_guess),
            )

            try:
                message: discord.Message = await ctx.wait_for(
                    "message", timeout=60.0, check=check
                )
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="Looks like the bot timed out! You must send a letter within 60 seconds.",
                    color=Colours.soft_red,
                )
                await original_message.edit(
                    content=f"{ctx.author.mention}", embed=timeout_embed
                )
                return

            # If the user enters a capital letter as their guess, it is automatically converted to a lowercase letter
            normalized_content = message.content.lower()
            # The user should only guess one letter per message
            if len(normalized_content) > 1:
                letter_embed = discord.Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="You can only send one letter at a time, try again!",
                    color=Colours.dark_green,
                )
                await ctx.send(
                    content=f"{ctx.author.mention}", embed=letter_embed, delete_after=4
                )
                continue

            # Checks for repeated guesses
            if normalized_content in guessed_letters:
                already_guessed_embed = discord.Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description=f"You have already guessed `{normalized_content}`, try again!",
                    color=Colours.dark_green,
                )
                await ctx.send(
                    content=f"{ctx.author.mention}",
                    embed=already_guessed_embed,
                    delete_after=4,
                )
                continue

            # Checks for correct guesses from the user
            if normalized_content in word:
                positions = {
                    idx
                    for idx, letter in enumerate(pretty_word)
                    if letter == normalized_content
                }
                user_guess = "".join(
                    [
                        normalized_content if index in positions else dash
                        for index, dash in enumerate(user_guess)
                    ]
                )

            else:
                tries -= 1

                if tries <= 0:
                    losing_embed = discord.Embed(
                        title="You lost.",
                        description=f"The word was `{word}`.",
                        color=Colours.soft_red,
                    )
                    await original_message.edit(
                        content=f"{ctx.author.mention}",
                        embed=self.create_embed(tries, user_guess),
                    )
                    await ctx.send(content=f"{ctx.author.mention}", embed=losing_embed)
                    await ctx.database_game_update("hangman", loss=True)
                    return

            guessed_letters.add(normalized_content)

        # The loop exited meaning that the user has guessed the word
        await original_message.edit(
            content=f"{ctx.author.mention}", embed=self.create_embed(tries, user_guess)
        )
        win_embed = discord.Embed(
            title="You won!",
            description=f"The word was `{word}`.",
            color=Colours.grass_green,
        )
        await ctx.send(content=f"{ctx.author.mention}", embed=win_embed)
        await ctx.database_game_update("hangman", win=True)
        return

    @quiz_game.command(name="stop")
    async def stop_quiz(self, ctx: Context) -> None:
        """Stop a quiz game if its running in the channel.
        Note: Only mods or the owner of the quiz can stop it."""
        try:
            if self.game_status[ctx.channel.id]:
                # Check if the author is the game starter or a moderator.
                if ctx.author == self.game_owners[ctx.channel.id]:
                    self.game_status[ctx.channel.id] = False
                    del self.game_owners[ctx.channel.id]
                    self.game_player_scores[ctx.channel.id] = {}

                    await ctx.send("Quiz stopped.")
                    await self.declare_winner(
                        ctx.channel, self.game_player_scores[ctx.channel.id]
                    )

                else:
                    await ctx.send(
                        f"{ctx.author.mention}, you are not authorised to stop this game :ghost:!"
                    )
            else:
                await ctx.send("No quiz running.")
        except KeyError:
            await ctx.send("No quiz running.")

    @quiz_game.command(name="leaderboard")
    async def leaderboard(self, ctx: Context) -> None:
        """View everyone's score for this bot session."""
        await self.send_score(ctx.channel, self.player_scores)

    @staticmethod
    async def send_score(channel: discord.TextChannel, player_data: dict) -> None:
        """Send the current scores of players in the game channel."""
        if not player_data:
            await channel.send("No one has made it onto the leaderboard yet.")
            return

        embed = discord.Embed(
            colour=Colours.blue,
            title="Score Board",
            description="",
        )
        embed.set_thumbnail(url=TRIVIA_QUIZ_ICON)

        sorted_dict = sorted(
            player_data.items(), key=operator.itemgetter(1), reverse=True
        )
        for item in sorted_dict:
            embed.description += f"{item[0]}: {item[1]}\n"  # type: ignore

        await channel.send(embed=embed)

    @staticmethod
    async def declare_winner(channel: discord.TextChannel, player_data: dict) -> None:
        """Announce the winner of the quiz in the game channel."""
        if player_data:
            highest_points = max(list(player_data.values()))
            no_of_winners = list(player_data.values()).count(highest_points)

            # Check if more than 1 player has highest points.
            if no_of_winners > 1:
                winners: List[discord.Member] = []
                points_copy = list(player_data.values()).copy()

                for _ in range(no_of_winners):
                    index = points_copy.index(highest_points)
                    winners.append(list(player_data.keys())[index])
                    points_copy[index] = 0

                winners_mention = " ".join(winner.mention for winner in winners)
            else:
                author_index = list(player_data.values()).index(highest_points)
                winner = list(player_data.keys())[author_index]
                winners_mention = winner.mention

            await channel.send(
                f"{winners_mention} Congratulations "
                f"on winning this quiz game with a grand total of {highest_points} points :tada:"
            )

    def category_embed(self) -> discord.Embed:
        """Build an embed showing all available trivia categories."""
        embed = discord.Embed(
            colour=Colours.blue,
            title="The available question categories are:",
            description="",
        )

        embed.set_footer(
            text="If a category is not chosen, a random one will be selected."
        )

        for cat, description in self.categories.items():
            embed.description += (
                f"**- {cat.capitalize()}**\n" f"{description.capitalize()}\n"
            )

        return embed

    @staticmethod
    async def send_answer(
        channel: discord.TextChannel,
        answers: List[str],
        answer_is_correct: bool,
        question_dict: dict,
        q_left: int,
    ) -> None:
        """Send the correct answer of a question to the game channel."""
        info = question_dict.get("info")

        plurality = " is" if len(answers) == 1 else "s are"

        embed = discord.Embed(
            color=Colours.bright_green,
            title=(
                ("You got it! " if answer_is_correct else "")
                + f"The correct answer{plurality} **`{', '.join(answers)}`**\n"
            ),
            description="",
        )

        # Don't check for info is not None, as we want to filter out empty strings.
        if info:
            embed.description += f"**Information**\n{info}\n\n"

        embed.description += (
            "Let's move to the next question." if q_left > 0 else ""
        ) + f"\nRemaining questions: {q_left}"
        await channel.send(embed=embed)

    @commands.command(name="8ball")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def _8ball(self, ctx: Context, *, question: commands.clean_content):
        """8ball Magic, nothing to say much"""
        await ctx.reply(
            f"Question: **{question}**\nAnswer: **{random.choice(RESPONSES)}**"
        )

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def choose(self, ctx: Context, *, options: commands.clean_content):
        """Confuse something with your decision? Let Parrot choose from your choice.
        NOTE: The `Options` should be seperated by commas `,`."""
        options = options.split(",")
        await ctx.reply(f"{ctx.author.mention} I choose {choice(options)}")

    async def _create_role_on_clr(
        self, *, ctx: Context, rgb: Tuple[int, int, int], color_name: str
    ):
        if ctx.author.guild_permissions.manage_roles:
            await ctx.guild.create_role(
                name=f"COLOR {color_name.upper()}",
                color=discord.Color.from_rgb(*rgb),
                reason=f"Action requested by {ctx.author}",
                permissions=discord.Permissions(0),
            )
            await ctx.tick()
        else:
            await ctx.error(
                f"{ctx.author.mention} you don't have permission to create role"
            )

    @commands.group(aliases=("color",), invoke_without_command=True)
    async def colour(self, ctx: Context, *, colour_input: Optional[str] = None) -> None:
        """
        Create an embed that displays colour information.

        If no subcommand is called, a randomly selected colour will be shown.
        """
        if colour_input is None:
            await self.random(ctx)
            return

        try:
            extra_colour = ImageColor.getrgb(colour_input)
            await self.send_colour_response(ctx, extra_colour)
        except ValueError:
            await self.bot.invoke_help_command(ctx)

    @colour.command()
    async def rgb(self, ctx: Context, red: int, green: int, blue: int) -> None:
        """Create an embed from an RGB input."""
        if any(c not in range(256) for c in (red, green, blue)):
            raise commands.BadArgument(
                message=f"RGB values can only be from 0 to 255. User input was: `{red, green, blue}`."
            )
        rgb_tuple = (red, green, blue)
        await self.send_colour_response(ctx, rgb_tuple)

    @colour.command()
    async def hsv(self, ctx: Context, hue: int, saturation: int, value: int) -> None:
        """Create an embed from an HSV input."""
        if (hue not in range(361)) or any(
            c not in range(101) for c in (saturation, value)
        ):
            raise commands.BadArgument(
                message="Hue can only be from 0 to 360. Saturation and Value can only be from 0 to 100. "
                f"User input was: `{hue, saturation, value}`."
            )
        hsv_tuple = ImageColor.getrgb(f"hsv({hue}, {saturation}%, {value}%)")
        await self.send_colour_response(ctx, hsv_tuple)

    @colour.command()
    async def hsl(
        self, ctx: Context, hue: int, saturation: int, lightness: int
    ) -> None:
        """Create an embed from an HSL input."""
        if (hue not in range(361)) or any(
            c not in range(101) for c in (saturation, lightness)
        ):
            raise commands.BadArgument(
                message="Hue can only be from 0 to 360. Saturation and Lightness can only be from 0 to 100. "
                f"User input was: `{hue, saturation, lightness}`."
            )
        hsl_tuple = ImageColor.getrgb(f"hsl({hue}, {saturation}%, {lightness}%)")
        await self.send_colour_response(ctx, hsl_tuple)

    @colour.command()
    async def cmyk(
        self, ctx: Context, cyan: int, magenta: int, yellow: int, key: int
    ) -> None:
        """Create an embed from a CMYK input."""
        if any(c not in range(101) for c in (cyan, magenta, yellow, key)):
            raise commands.BadArgument(
                message=f"CMYK values can only be from 0 to 100. User input was: `{cyan, magenta, yellow, key}`."
            )
        r = round(255 * (1 - (cyan / 100)) * (1 - (key / 100)))
        g = round(255 * (1 - (magenta / 100)) * (1 - (key / 100)))
        b = round(255 * (1 - (yellow / 100)) * (1 - (key / 100)))
        await self.send_colour_response(ctx, (r, g, b))

    @colour.command()
    async def hex(self, ctx: Context, hex_code: str) -> None:
        """Create an embed from a HEX input."""
        if hex_code[0] != "#":
            hex_code = f"#{hex_code}"

        if len(hex_code) not in (4, 5, 7, 9) or any(
            digit not in string.hexdigits for digit in hex_code[1:]
        ):
            raise commands.BadArgument(
                message=f"Cannot convert `{hex_code}` to a recognizable Hex format. "
                "Hex values must be hexadecimal and take the form *#RRGGBB* or *#RGB*."
            )

        hex_tuple = ImageColor.getrgb(hex_code)
        if len(hex_tuple) == 4:
            hex_tuple = hex_tuple[
                :-1
            ]  # Colour must be RGB. If RGBA, we remove the alpha value
        await self.send_colour_response(ctx, hex_tuple)

    @colour.command()
    async def name(self, ctx: Context, *, user_colour_name: str) -> None:
        """Create an embed from a name input."""
        hex_colour = self.match_colour_name(ctx, user_colour_name)
        if hex_colour is None:
            name_error_embed = discord.Embed(
                title="No colour match found.",
                description=f"No colour found for: `{user_colour_name}`",
                colour=discord.Color.dark_red(),
            )
            await ctx.send(embed=name_error_embed)
            return
        hex_tuple = ImageColor.getrgb(hex_colour)
        await self.send_colour_response(ctx, hex_tuple)

    @colour.command()
    async def random(self, ctx: Context) -> None:
        """Create an embed from a randomly chosen colour."""
        hex_colour = random.choice(list(self.colour_mapping.values()))
        hex_tuple = ImageColor.getrgb(f"#{hex_colour}")
        await self.send_colour_response(ctx, hex_tuple)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def decode(self, ctx: Context, *, string: str):
        """Decode the code to text from Base64 encryption"""
        base64_string = string
        try:
            base64_bytes = base64_string.encode("ascii")

            sample_string_bytes = base64.b64decode(base64_bytes)
            sample_string = sample_string_bytes.decode("ascii")
        except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error):
            await ctx.send(
                f"{ctx.author.mention} The string you entered is not valid Base64. Please try again."
            )
            return

        await ctx.reply(f"{ctx.author.mention} {sample_string}")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def encode(self, ctx: Context, *, string: str):
        """Encode the text to Base64 Encryption"""
        sample_string = string
        sample_string_bytes = sample_string.encode("ascii")
        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string = base64_bytes.decode("ascii")

        await ctx.reply(f"{ctx.author.mention} {base64_string}")

    @commands.command(name="fact")
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def animal_fact(self, ctx: Context, *, animal: str):
        """Return a random Fact. It's useless command, I know

        NOTE: Available animals - Dog, Cat, Panda, Fox, Bird, Koala"""
        if (animal := animal.lower()) not in (
            "dog",
            "cat",
            "panda",
            "fox",
            "bird",
            "koala",
        ):
            return
        fact_url = f"https://some-random-api.ml/facts/{animal}"
        image_url = (
            f"https://some-random-api.ml/img/{'birb' if animal == 'bird' else animal}"
        )

        async with request("GET", image_url, headers={}) as response:
            if response.status == 200:
                data = await response.json()
                image_link = data.get("link")

        async with request("GET", fact_url, headers={}) as response:
            if response.status == 200:
                data = await response.json()

                embed = discord.Embed(
                    title=f"{animal.title()} fact",
                    description=data["fact"],
                    colour=ctx.author.colour,
                )
                if image_link is not None:
                    embed.set_image(url=image_link)
                    return await ctx.reply(embed=embed)

                return await ctx.reply(
                    f"{ctx.author.mention} API returned a {response.status} status."
                )

            return await ctx.reply(
                f"{ctx.author.mention} no facts are available for that animal. Available animals: `dog`, `cat`, `panda`, `fox`, `bird`, `koala`"
            )

    @commands.command(aliases=["insult"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def roast(self, ctx: Context, *, member: discord.Member = None):
        """Insult your enemy, Ugh!"""
        member = member or ctx.author

        response = await self.bot.http_session.get(
            "https://insult.mattbas.org/api/insult"
        )
        insult = await response.text()
        await ctx.reply(f"**{member.name}** {insult}")

    @commands.command(aliases=["its-so-stupid"])
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def itssostupid(self, ctx: Context, *, comment: str):
        """:| I don't know what is this, I think a meme generator."""
        member = ctx.author
        if len(comment) > 20:
            comment = comment[:19:]
        async with self.bot.http_session.get(
            f"https://some-random-api.ml/canvas/its-so-stupid?avatar={member.display_avatar.url}&dog={comment}"
        ) as itssostupid:  # get users avatar as png with 1024 size
            imageData = io.BytesIO(await itssostupid.read())  # read the image/bytes

            await ctx.reply(
                file=discord.File(imageData, "itssostupid.png")
            )  # replying the file

    @commands.command(name="meme")
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def meme(
        self, ctx: Context, count: Optional[int] = 1, *, subreddit: str = "memes"
    ):
        """Random meme generator."""
        link = "https://meme-api.herokuapp.com/gimme/{}/{}".format(subreddit, count)

        while True:
            response = await self.bot.http_session.get(link)
            if response.status <= 300:
                res = await response.json()
                if "message" in res:
                    await ctx.reply(res["message"])
                    return
            if not any(x["nsfw"] for x in res["memes"]):
                break

            await ctx.release(0)

        def make_embed(res) -> discord.Embed:
            title = res["title"]
            ups = res["ups"]
            sub = res["subreddit"]

            embed = discord.Embed(
                title=f"{title}", description=f"{sub}", timestamp=discord.utils.utcnow()
            )
            embed.set_image(url=res["url"])
            embed.set_footer(text=f"Upvotes: {ups}")
            return embed

        em: List[discord.Embed] = []
        for _res in res["memes"]:
            em.append(make_embed(_res))
        p = PaginationView(em)
        await p.start(ctx)

    @commands.command(aliases=["fakeprofile"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def fakepeople(self, ctx: Context):
        """Fake Identity generator."""
        link = "https://randomuser.me/api/"
        response = await self.bot.http_session.get(link)
        if response.status == 200:
            res = await response.json()
        else:
            return
        res = res["results"][0]
        name = f"{res['name']['title']} {res['name']['first']} {res['name']['last']}"
        address = f"{res['location']['street']['number']}, {res['location']['street']['name']}, {res['location']['city']}, {res['location']['state']}, {res['location']['country']}, {res['location']['postcode']}"
        cords = f"{res['location']['coordinates']['latitude']}, {res['location']['coordinates']['longitude']}"
        tz = f"{res['location']['timezone']['offset']}, {res['location']['timezone']['description']}"
        email = res["email"]
        usrname = res["login"]["username"]
        pswd = res["login"]["password"]
        age = res["dob"]["age"]
        phone = f"{res['phone']}, {res['cell']}"
        pic = res["picture"]["large"]

        em = discord.Embed(
            title=f"{name}",
            description=f"```\n{address} {cords}```",
            timestamp=discord.utils.utcnow(),
        )
        em.add_field(name="Timezone", value=f"{tz}", inline=False)
        em.add_field(
            name="Email & Password",
            value=f"**Username:** {usrname}\n**Email:** {email}\n**Password:** {pswd}",
            inline=False,
        )
        em.add_field(name="Age", value=f"{age}", inline=False)
        em.set_thumbnail(url=pic)
        em.add_field(name="Phone", value=f"{phone}", inline=False)
        em.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=em)

    @commands.command(aliases=["trans"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def translate(self, ctx: Context, model: str, *, message: str):
        """Translates a message to English (default). using My Memory"""

        # from the docs
        IBM_END_POINT = os.environ["IBM_END_POINT"]
        URL = f"{IBM_END_POINT}/v3/translate?version=2018-05-01"
        HEADER = {"Content-Type": "application/json"}
        AUTH = aiohttp.BasicAuth("apikey", os.environ["IBM_KEY"])

        DATA = {"text": [message], "model_id": model}
        res = await self.bot.http_session.post(
            URL,
            json=DATA,
            auth=AUTH,
            headers=HEADER,
        )
        if res.status != 200:
            return await ctx.error(
                f"{ctx.author.mention} somthing not right! Please try again later or check the `model`"
            )

        data = await res.json()
        for i in data.get("translations", []):
            result = i["translation"]
            return await ctx.send(f"{ctx.author.mention} Translated: {result}")

        return await ctx.send(f"{ctx.author.mention} no translation found")

    @commands.command(aliases=["def", "urban"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def urbandictionary(self, ctx: Context, *, text: commands.clean_content):
        """LOL. This command is insane."""
        t = text
        BRACKETED = re.compile(r"(\[(.+?)\])")

        def cleanup_definition(definition, *, regex=BRACKETED) -> str:
            def repl(m):
                word = m.group(2)
                return f'[{word}](http://{word.replace(" ", "-")}.urbanup.com)'

            ret = regex.sub(repl, definition)
            return f"{ret[:2000]} [...]" if len(ret) >= 2048 else ret

        # Thanks Danny

        response = await self.bot.http_session.get(
            f"http://api.urbandictionary.com/v0/define?term={urllib.parse.quote(text)}"
        )
        if response.status == 200:
            res = await response.json()
        else:
            return
        if not res["list"]:
            return await ctx.reply(
                f"{ctx.author.mention} **{t}** means nothings. Try something else"
            )
        em_list = []
        for i in range(len(res["list"])):
            _def = res["list"][i]["definition"]
            _link = res["list"][i]["permalink"]
            thumbs_up = res["list"][i]["thumbs_up"]
            thumbs_down = res["list"][i]["thumbs_down"]
            author = res["list"][i]["author"]
            example = res["list"][i]["example"]
            word = res["list"][i]["word"].capitalize()
            embed = discord.Embed(
                title=f"{word}",
                description=f"{cleanup_definition(_def)}",
                url=f"{_link}",
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="Example", value=f"{example[:250:]}...")
            embed.set_author(name=f"Author: {author}")
            embed.set_footer(
                text=f"\N{THUMBS UP SIGN} {thumbs_up} \N{BULLET} \N{THUMBS DOWN SIGN} {thumbs_down}"
            )
            em_list.append(embed)

        await PaginationView(em_list).start(ctx=ctx)

    @commands.command(aliases=["youtube-comment", "youtube_comment"])
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def ytcomment(self, ctx: Context, *, comment: str):
        """Makes a comment in YT. Best ways to fool your fool friends. :')"""
        member = ctx.author
        if len(comment) > 1000:
            comment = comment[:999:]
        name = member.name[:20:] if len(member.name) > 20 else member.name
        async with self.bot.http_session.get(
            f"https://some-random-api.ml/canvas/youtube-comment?avatar={member.display_avatar.url}&username={name}&comment={comment}"
        ) as ytcomment:  # get users avatar as png with 1024 size
            imageData = io.BytesIO(await ytcomment.read())  # read the image/bytes

            await ctx.reply(
                file=discord.File(imageData, "ytcomment.png")
            )  # replying the file

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def dare(self, ctx: Context, *, member: discord.Member = None):
        """I dared you to use this command."""
        dare = _dare.split("\n")
        if member is None:
            em = discord.Embed(
                title="Dare",
                description=f"{random.choice(dare)}",
                timestamp=discord.utils.utcnow(),
            )
        else:
            em = discord.Embed(
                title=f"{member.name} Dared",
                description=f"{random.choice(dare)}",
                timestamp=discord.utils.utcnow(),
            )

        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command(aliases=["wyr"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def wouldyourather(self, ctx: Context, *, member: discord.Member = None):
        """A classic `Would you Rather...?` game"""
        wyr = _wyr.split("\n")
        if member is None:
            em = discord.Embed(
                title="Would you Rather...?",
                description=f"{random.choice(wyr)}",
                timestamp=discord.utils.utcnow(),
            )
        else:
            em = discord.Embed(
                title=f"{member.name} Would you Rather...?",
                description=f"{random.choice(wyr)}",
                timestamp=discord.utils.utcnow(),
            )

        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command(aliases=["nhie"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def neverhaveiever(self, ctx: Context, *, member: discord.Member = None):
        """A classic `Never Have I ever...` game"""
        nhi = _nhi.split("\n")
        if member is None:
            em = discord.Embed(
                title="Never Have I ever...",
                description=f"{random.choice(nhi)}",
                timestamp=discord.utils.utcnow(),
            )
        else:
            em = discord.Embed(
                title=f"{member.name} Never Have I ever...",
                description=f"{random.choice(nhi)}",
                timestamp=discord.utils.utcnow(),
            )

        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def truth(self, ctx: Context, *, member: discord.Member = None):
        """Truth: Who is your crush?"""
        t = _truth.split("\n")
        if member is None:
            em = discord.Embed(
                title="Truth",
                description=f"{random.choice(t)}",
                timestamp=discord.utils.utcnow(),
            )
        else:
            em = discord.Embed(
                title=f"{member.name} reply!",
                description=f"{random.choice(t)}",
                timestamp=discord.utils.utcnow(),
            )
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def twister(self, ctx: Context, *, member: discord.Member = None):
        """I scream, you scream, we all scream for ice-cream"""
        t = _twister.split("\n")
        if member is None:
            em = discord.Embed(
                title="Say",
                description=f"{random.choice(t)}",
                timestamp=discord.utils.utcnow(),
            )
        else:
            em = discord.Embed(
                title=f"{member} reply!",
                description=f"{random.choice(t)}",
                timestamp=discord.utils.utcnow(),
            )
        em.set_footer(text=f"{ctx.author}")
        await ctx.reply(embed=em)

    @commands.group(aliases=["https"], invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def http(self, ctx: Context, *, status_code: int):
        """To understand HTTP Errors, try: `http 404`"""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                embed=discord.Embed(
                    timestamp=discord.utils.utcnow(), color=ctx.author.color
                )
                .set_image(url=f"https://http.cat/{status_code}")
                .set_footer(text=f"{ctx.author}")
            )

    @http.command(name="dog")
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def http_dog(self, ctx: Context, *, status_code: int):
        """To understand HTTP Errors, in dog format"""
        await ctx.reply(
            embed=discord.Embed(
                timestamp=discord.utils.utcnow(), color=ctx.author.color
            )
            .set_image(url=f"https://httpstatusdogs.com/img/{status_code}.jpg")
            .set_footer(text=f"{ctx.author}")
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def shear(
        self, ctx: Context, member: discord.Member = None, axis: str = None
    ):
        """Shear image generation"""
        member = member or ctx.author
        params = {"image_url": member.display_avatar.url, "axis": axis or "X"}
        r = await self.bot.http_session.get(
            f"https://api.jeyy.xyz/image/{ctx.command.name}", params=params
        )
        file_obj = discord.File(
            io.BytesIO(await r.read()), f"{ctx.command.qualified_name}.gif"
        )
        await ctx.reply(file=file_obj)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def scrapbook(self, ctx: Context, *, text: commands.clean_content):
        """ScrapBook Text image generation"""
        params = {"text": text[:20:]}
        r = await self.bot.http_session.get(
            f"https://api.jeyy.xyz/image/{ctx.command.name}", params=params
        )
        file_obj = discord.File(
            io.BytesIO(await r.read()), f"{ctx.command.qualified_name}.gif"
        )
        await ctx.reply(file=file_obj)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def uwuify(self, ctx: Context, *, text: commands.clean_content):
        """Converts a given `text` into it's uwu equivalent."""
        conversion_func = functools.partial(
            replace_many, replacements=UWU_WORDS, ignore_case=True, match_case=True
        )
        text, embed = await self._get_text_and_embed(ctx, text)
        # Convert embed if it exists
        if embed is not None:
            embed = self._convert_embed(conversion_func, embed)
        converted_text = conversion_func(text)
        converted_text = suppress_links(converted_text)
        # Don't put >>> if only embed present
        if converted_text:
            converted_text = f">>> {converted_text.lstrip('> ')}"
        await ctx.send(content=converted_text, embed=embed)

    @commands.command(aliases=["cointoss", "cf", "ct"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def coinflip(self, ctx: Context, *, choose: str = None):
        """Coin Flip, It comes either HEADS or TAILS"""
        choose = "tails" if choose.lower() in {"tails", "tail", "t"} else "heads"
        msg: discord.Message = await ctx.send(
            f"{ctx.author.mention} you choose **{choose}**. And coin <a:E_CoinFlip:923477401806196786> landed on ..."
        )
        await ctx.release(1.5)
        await msg.edit(
            content=f"{ctx.author.mention} you choose **{choose}**. And coin <a:E_CoinFlip:923477401806196786> landed on **{random.choice(['HEADS', 'TAILS'])}**"
        )

    @commands.command(aliases=["slot"])
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def slots(self, ctx: Context):
        """Basic Slots game"""
        CHOICE = [
            "\N{BANKNOTE WITH DOLLAR SIGN}",
            "\N{FIRST PLACE MEDAL}",
            "\N{HUNDRED POINTS SYMBOL}",
            "\N{GEM STONE}",
        ]
        e = discord.PartialEmoji(
            name="SlotsEmoji", id=923478531873325076, animated=True
        )
        msg: discord.Message = await ctx.send(
            f"""{ctx.author.mention} your slots results:
> {e} {e} {e}"""
        )
        await ctx.release(1.5)
        _1 = random.choice(CHOICE)
        await msg.edit(
            content=f"""{ctx.author.mention} your slots results:
> {_1} {e} {e}"""
        )
        await ctx.release(1.5)
        _2 = random.choice(CHOICE)
        await msg.edit(
            content=f"""{ctx.author.mention} your slots results:
> {_1} {_2} {e}"""
        )
        await ctx.release(1.5)
        _3 = random.choice(CHOICE)
        await msg.edit(
            content=f"""{ctx.author.mention} your slots results:
> {_1} {_2} {_3}"""
        )

    async def _fetch_user(self, user_id: int) -> Optional[discord.User]:
        """
        Fetches a user and handles errors.
        This helper function is required as the member cache doesn't always have the most up to date
        profile picture. This can lead to errors if the image is deleted from the Discord CDN.
        fetch_member can't be used due to the avatar url being part of the user object, and
        some weird caching that D.py does
        """
        return await self.bot.getch(self.bot.get_user, self.bot.fetch_user, user_id)

    @commands.command(
        name="8bitify",
    )
    async def eightbit_command(self, ctx: Context):
        """Pixelates your avatar and changes the palette to an 8bit one."""

        user = await self._fetch_user(ctx.author.id)
        if not user:
            await ctx.send(f"{ctx.author.mention} Could not get user info.")
            return

        image_bytes = await user.display_avatar.replace(size=1024).read()
        file_name = file_safe_name("eightbit_avatar", ctx.author.display_name)

        file = await self.bot.func(
            PfpEffects.apply_effect,
            image_bytes,
            PfpEffects.eight_bitify_effect,
            file_name,
        )

        embed = discord.Embed(
            title="Your 8-bit avatar",
            description="Here is your avatar. I think it looks all cool and 'retro'.",
        )

        embed.set_image(url=f"attachment://{file_name}")
        embed.set_footer(
            text=f"Made by {ctx.author.display_name}.",
            icon_url=user.display_avatar.url,
        )

        await ctx.send(embed=embed, file=file)

    @commands.command(
        name="reverseimg",
    )
    async def reverse(self, ctx: Context, *, text: Optional[str]):
        """
        Reverses the sent text.
        If no text is provided, the user's profile picture will be reversed.
        """
        if text:
            await ctx.send(
                f"> {text[::-1]}", allowed_mentions=discord.AllowedMentions.none()
            )
            return

        async with ctx.typing():
            user = await self._fetch_user(ctx.author.id)
            if not user:
                await ctx.send(f"{ctx.author.mention} Could not get user info.")
                return

            image_bytes = await user.display_avatar.replace(size=1024).read()
            filename = file_safe_name("reverse_avatar", ctx.author.display_name)

            file = await self.bot.func(
                PfpEffects.apply_effect, image_bytes, PfpEffects.flip_effect, filename
            )

            embed = discord.Embed(
                title="Your reversed avatar.",
                description="Here is your reversed avatar. I think it is a spitting image of you.",
            )

            embed.set_image(url=f"attachment://{filename}")
            embed.set_footer(
                text=f"Made by {ctx.author.display_name}.",
                icon_url=user.display_avatar.url,
            )

            await ctx.send(embed=embed, file=file)

    @commands.command(
        aliases=("easterify",),
    )
    async def avatareasterify(self, ctx: Context, *colours: Union[discord.Colour, str]):
        """
        This "Easterifies" the user's avatar.
        Given colours will produce a personalised egg in the corner, similar to the egg_decorate command.
        If colours are not given, a nice little chocolate bunny will sit in the corner.
        Colours are split by spaces, unless you wrap the colour name in double quotes.
        Discord colour names, HTML colour names, XKCD colour names and hex values are accepted.
        """

        async def send(*args, **kwargs) -> str:
            """
            This replaces the original ctx.send.
            When invoking the egg decorating command, the egg itself doesn't print to to the channel.
            Returns the message content so that if any errors occur, the error message can be output.
            """
            if args:
                return args[0]

        async with ctx.typing():
            user = await self._fetch_user(ctx.author.id)
            if not user:
                await ctx.send(f"{ctx.author.mention} Could not get user info.")
                return

            egg = None
            if colours:
                send_message = ctx.send
                ctx.send = send  # Assigns ctx.send to a fake send
                egg = await ctx.invoke(self.bot.get_command("eggdecorate"), *colours)
                if isinstance(egg, str):  # When an error message occurs in eggdecorate.
                    await send_message(egg)
                    return
                ctx.send = send_message  # Reassigns ctx.send

            image_bytes = await user.display_avatar.replace(size=256).read()
            file_name = file_safe_name("easterified_avatar", ctx.author.display_name)

            file = await self.bot.func(
                PfpEffects.apply_effect,
                image_bytes,
                PfpEffects.easterify_effect,
                file_name,
                egg,
            )

            embed = discord.Embed(
                title="Your Lovely Easterified Avatar!",
                description="Here is your lovely avatar, all bright and colourful\nwith Easter pastel colours. Enjoy :D",
            )
            embed.set_image(url=f"attachment://{file_name}")
            embed.set_footer(
                text=f"Made by {ctx.author.display_name}.",
                icon_url=user.display_avatar.url,
            )

        await ctx.send(file=file, embed=embed)

    @staticmethod
    async def send_pride_image(
        ctx: Context, image_bytes: bytes, pixels: int, flag: str, option: str
    ):
        """Gets and sends the image in an embed. Used by the pride commands."""
        async with ctx.typing():
            file_name = file_safe_name("pride_avatar", ctx.author.display_name)

            file = await ctx.bot.func(
                PfpEffects.apply_effect,
                image_bytes,
                PfpEffects.pridify_effect,
                file_name,
                pixels,
                flag,
            )

            embed = discord.Embed(
                title="Your Lovely Pride Avatar!",
                description=f"Here is your lovely avatar, surrounded by\n a beautiful {option} flag. Enjoy :D",
            )
            embed.set_image(url=f"attachment://{file_name}")
            embed.set_footer(
                text=f"Made by {ctx.author.display_name}.",
                icon_url=ctx.author.display_avatar.url,
            )
            await ctx.send(file=file, embed=embed)

    @commands.group(
        aliases=("avatarpride", "pridepfp", "prideprofile"),
    )
    async def prideavatar(self, ctx: Context, option: str = "lgbt", pixels: int = 64):
        """
        This surrounds an avatar with a border of a specified LGBT flag.
        This defaults to the LGBT rainbow flag if none is given.
        The amount of pixels can be given which determines the thickness of the flag border.
        This has a maximum of 512px and defaults to a 64px border.
        The full image is 1024x1024.
        """
        option = option.lower()
        pixels = max(0, min(512, pixels))
        flag = GENDER_OPTIONS.get(option)
        if flag is None:
            await ctx.send("I don't have that flag!")
            return

        async with ctx.typing():
            user = await self._fetch_user(ctx.author.id)
            if not user:
                await ctx.send(f"{ctx.author.mention} Could not get user info.")
                return
            image_bytes = await user.display_avatar.replace(size=1024).read()
            await self.send_pride_image(ctx, image_bytes, pixels, flag, option)

    @prideavatar.command()
    async def flags(self, ctx: Context):
        """This lists the flags that can be used with the prideavatar command."""
        choices = sorted(set(GENDER_OPTIONS.values()))
        options = "\N{BULLET} " + "\n\N{BULLET} ".join(choices)
        embed = discord.Embed(
            title="I have the following flags:",
            description=options,
            colour=Colours.soft_red,
        )
        await ctx.send(embed=embed)

    @commands.command(
        aliases=["spookify"],
    )
    async def spookyavatar(self, ctx: Context):
        """This "spookifies" the user's avatar, with a random *spooky* effect."""
        user = await self._fetch_user(ctx.author.id)
        if not user:
            await ctx.send(f"{ctx.author.mention} Could not get user info.")
            return

        async with ctx.typing():
            image_bytes = await user.display_avatar.replace(size=1024).read()

            file_name = file_safe_name("spooky_avatar", ctx.author.display_name)

            file = await self.bot.func(
                PfpEffects.apply_effect,
                image_bytes,
                spookifications.get_random_effect,
                file_name,
            )

            embed = discord.Embed(
                title="Is this you or am I just really paranoid?",
                colour=Colours.soft_red,
            )
            embed.set_image(url=f"attachment://{file_name}")
            embed.set_footer(
                text=f"Made by {ctx.author.display_name}.",
                icon_url=ctx.author.display_avatar.url,
            )

            await ctx.send(file=file, embed=embed)

    @commands.command(name="activity")
    @commands.bot_has_guild_permissions(
        create_instant_invite=True,
        use_embedded_activities=True,
    )
    @commands.has_guild_permissions(use_embedded_activities=True)
    async def activity(self, ctx: Context, *, name: str):
        """To create embed activity within your server"""
        if not ctx.author.voice:
            return await ctx.error(
                f"{ctx.author.mention} you must be in the voice channel to use the activity"
            )

        INT = EmbeddedActivity.get(name.lower().replace(" ", "_"))
        if INT is None:
            return await ctx.error(f"{ctx.author.mention} no activity named {name}")

        inv = await ctx.author.voice.channel.create_invite(
            target_type=discord.InviteTarget.embedded_application,
            target_application_id=INT,
            max_age=120,
            reason=f"Activity requested by: {ctx.author} ({ctx.author.id})",
        )
        await ctx.send(
            embed=discord.Embed(
                title="Activity",
                description=f"{ctx.author.mention} [Click Here]({inv}). **The invite link will be expired in 120 seconds**",
                timestamp=ctx.message.created_at,
            ).set_footer(text=f"Requested by: {ctx.author}")
        )

    @commands.command(
        name="mosaic",
    )
    async def mosaic_command(self, ctx: Context, squares: int = 16):
        """Splits your avatar into x squares, randomizes them and stitches them back into a new image!"""
        async with ctx.typing():
            user = await self._fetch_user(ctx.author.id)
            if not user:
                await ctx.send(f"{ctx.author.mention} Could not get user info.")
                return

            if not 1 <= squares <= MAX_SQUARES:
                raise commands.BadArgument(
                    f"Squares must be a positive number less than or equal to {MAX_SQUARES:,}."
                )

            sqrt = math.sqrt(squares)

            if not sqrt.is_integer():
                squares = math.ceil(sqrt) ** 2  # Get the next perfect square

            file_name = file_safe_name("mosaic_avatar", ctx.author.display_name)

            img_bytes = await user.display_avatar.replace(size=1024).read()

            file = await self.bot.func(
                PfpEffects.apply_effect,
                img_bytes,
                PfpEffects.mosaic_effect,
                file_name,
                squares,
            )

            if squares == 1:
                title = "Hooh... that was a lot of work"
                description = "I present to you... Yourself!"
            elif squares == MAX_SQUARES:
                title = "Testing the limits I see..."
                description = "What a masterpiece. :star:"
            else:
                title = "Your mosaic avatar"
                description = f"Here is your avatar. I think it looks a bit *puzzling*\nMade with {squares} squares."

            embed = discord.Embed(
                title=title, description=description, colour=Colours.blue
            )

            embed.set_image(url=f"attachment://{file_name}")
            embed.set_footer(
                text=f"Made by {ctx.author.display_name}",
                icon_url=user.display_avatar.url,
            )

            await ctx.send(file=file, embed=embed)

    @commands.command(name="cathi")
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_cathi(self, ctx: Context, text: Optional[str] = None):
        """Make a cat say something"""
        m: discord.Message = await ctx.reply("starting")
        text = text or "Hi..."

        FWLL = "\N{FULLWIDTH LOW LINE}"
        LL = "\N{LOW LINE}"
        IGS = "\N{IDEOGRAPHIC SPACE}"
        FWS = "\N{FULLWIDTH SOLIDUS}"
        FWRS = "\N{FULLWIDTH REVERSE SOLIDUS}"
        FM = "\N{FULLWIDTH MACRON}"
        LA = "\N{LOGICAL AND}"

        FACE = "\N{ACUTE ACCENT}\N{HALFWIDTH KATAKANA MIDDLE DOT}\N{GREEK SMALL LETTER OMEGA}\N{HALFWIDTH KATAKANA MIDDLE DOT}\N{GRAVE ACCENT}"
        ls = [
            f". {IGS}{IGS}{IGS}{FWLL}{FWLL}{LL}{FWLL}{FWLL}\n"
            f"{IGS}{IGS}{FWS}{IGS}{FWS}{IGS}  {FWS}|\n"
            f"{IGS}{IGS}|{FM}{FM}{FM}{FM}|{IGS}|\n"
            f"{IGS}{IGS}|{IGS}{IGS}{IGS}{IGS}|{FWS}\n"
            f"{IGS}{IGS}{FM}{FM}{FM}{FM}",
            f". {IGS}{IGS}{IGS}{text}\n"
            f"{IGS}   {IGS} {LA}{FWLL}{LA}{FWLL}_\n"
            f"{IGS}{IGS}{FWS}({FACE})  {FWS}{FWRS}\n"
            f"{IGS}{FWS}|{FM}{FM}{FM}{FM}|{FWRS}{FWS}\n"
            f"{IGS}{IGS}|{IGS}{IGS}{IGS}{IGS}|{FWS}\n"
            f"{IGS}{IGS}{FM}{FM}{FM}{FM}",
        ]
        for _, cat in itertools.product(range(3), ls):
            await m.edit(content=cat)
            await ctx.release(1)

    @commands.command(name="flop")
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_flop(self, ctx: Context):
        """Flop"""
        m = await ctx.send("Starting...")
        DEGREE_SIGN = "\N{DEGREE SIGN}"
        WHITE_SQUARE = "\N{WHITE SQUARE}"
        EM_DASH = "\N{EM DASH}"
        HAND_UP = "\N{BOX DRAWINGS LIGHT ARC UP AND LEFT}"
        CURVE_DOWN = "\N{PRESENTATION FORM FOR VERTICAL LEFT PARENTHESIS}"

        ls = (
            rf"(   {DEGREE_SIGN} - {DEGREE_SIGN}) (' - '   )",
            rf"(\{DEGREE_SIGN} - {DEGREE_SIGN})\ (' - '   )",
            rf"({EM_DASH}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){EM_DASH} (' - '   )",
            rf"({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}(' - '   )",
            rf"({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}{CURVE_DOWN}(\\ .o.)\\",
        )
        for i in ls:
            await m.edit(content=i)
            await ctx.release(1.5)

    @commands.command(name="poof", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_poof(self, ctx: Context):
        """Poof"""
        m: discord.Message = await ctx.send("...")
        ls = ("(   ' - ')", r"' \- ')", r"\- ')", "')", ")", "*poofness*")
        for i in ls:
            await m.edit(content=discord.utils.escape_markdown(i))
            await ctx.release(1.5)

    @commands.command(name="virus", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_virus(
        self, ctx: Context, user: discord.Member = None, virus: str = "trojan"
    ):
        """Insert a virus to yourself or someone else"""
        m = await ctx.send("...")
        user = user or ctx.author
        DARK_SHADE = "\N{DARK SHADE}"

        PREFIX = "```asni\n"
        SUFFIX = "\n```"

        SHIFTER = 24

        def D(n: int) -> str:
            return DARK_SHADE * n + " " * (SHIFTER - n)

        rotator = itertools.cycle(["/", "-", "\\", "|"])
        dot_rotator = itertools.cycle([".", "..", "..."])

        ls = [
            rf"{PREFIX}{Fore.WHITE}[{Fore.GREEN}{D(i)}{Fore.WHITE}] {Fore.YELLOW}{next(rotator)} "
            rf"{Fore.BLUE}{virus}-virus.exe Packing files{next(dot_rotator)}{SUFFIX}"
            for i in range(3, SHIFTER, 3)
        ]
        ls.append(
            f"{PREFIX}{Fore.WHITE}[{Fore.GREEN}{'Successfully downloaded':<24}{Fore.WHITE}] "
            rf"{Fore.YELLOW}{next(rotator)} {Fore.BLUE}{virus}-virus.exe{SUFFIX}"
        )
        for _ in range(3):
            ls.append(
                f"{PREFIX}{Fore.WHITE}[{Fore.RED}{f'Injecting virus{next(dot_rotator)}':<24}{Fore.WHITE}] "
                f"{Fore.YELLOW}{next(rotator)} {Fore.BLUE}{virus}-virus.exe{SUFFIX}"
            )
        ls.append(
            f"{PREFIX}{Fore.GREEN}Successfully {Fore.WHITE}Injected {Fore.RED}{virus}-virus.exe into {Fore.YELLOW}{user.name}{SUFFIX}",
        )
        for i in ls:
            await m.edit(content=i)
            await ctx.release(1)

    @commands.command(name="boom", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_boom(self, ctx: Context):
        """Booms a message!"""
        m = await ctx.send("THIS MESSAGE WILL SELFDESTRUCT IN 5")
        await ctx.release(1)
        ls = (
            "THIS MESSAGE WILL SELFDESTRUCT IN 4",
            "THIS MESSAGE WILL SELFDESTRUCT IN 3",
            "THIS MESSAGE WILL SELFDESTRUCT IN 2",
            "THIS MESSAGE WILL SELFDESTRUCT IN 1",
            "THIS MESSAGE WILL SELFDESTRUCT IN 0",
            "\N{BOMB}",
            "\N{COLLISION SYMBOL}",
        )
        for i in ls:
            await m.edit(content=i)
            await ctx.release(1)

    @commands.command(name="table", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_table(self, ctx: Context):
        # Thanks `CutieRei#5211`(830248412904947753)
        DEGREE_SIGN = "\N{DEGREE SIGN}"
        WHITE_SQUARE = "\N{WHITE SQUARE}"
        HAND_UP = "\N{BOX DRAWINGS LIGHT ARC UP AND LEFT}"

        TOP = "\N{HANGUL LETTER YU}"
        RIGHT = "\N{HANGUL LETTER YEO}"
        DOWN = "\N{HANGUL LETTER YO}"
        LEFT = "\N{HANGUL LETTER YA}"

        m: discord.Message = await ctx.send(rf"`(\{DEGREE_SIGN}-{DEGREE_SIGN})\  {TOP}`")
        lst = (
            rf"`(\{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN})\  {TOP}`",
            rf"`(-{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN})-  {TOP}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}  {RIGHT}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}    {DOWN}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}      {LEFT}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}        {TOP}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}          {RIGHT}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}            {DOWN}`",
            rf"`({HAND_UP}{DEGREE_SIGN}{WHITE_SQUARE}{DEGREE_SIGN}){HAND_UP}              {LEFT}`",
            rf"`(\{DEGREE_SIGN}-{DEGREE_SIGN})\                 {TOP}`",
        )

        for k in lst:
            await m.edit(content=k)
            await ctx.release(0.5)

    @commands.command(name="funwarn", hidden=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def fun_animation_warning(self, ctx: Context):
        msg = await ctx.send("...")
        IDEA_GRAPHIC_FULL_STOP = "\N{HALFWIDTH IDEOGRAPHIC FULL STOP}"
        IDEA_GRAPHIC = "\N{CJK UNIFIED IDEOGRAPH-76CA}"
        KATAKANA_MIDDLE_DOT = "\N{HALFWIDTH KATAKANA MIDDLE DOT}"
        MACRON = "\N{MACRON}"

        FACE = f"{MACRON}\\({IDEA_GRAPHIC_FULL_STOP}{KATAKANA_MIDDLE_DOT}{IDEA_GRAPHIC}{KATAKANA_MIDDLE_DOT})/{MACRON}"

        ls = (
            "```diff\n- OAD !! WARNING !! SYSTEM OVERL -\n```",
            "```diff\n- D !! WARNING !! SYSTEM OVERLOA -\n```",
            "```diff\n- !! WARNING !! SYSTEM OVERLOAD  -\n```",
            "```diff\n-  WARNING !! SYSTEM OVERLOAD !! -\n```",
            "```diff\n- ARNING !! SYSTEM OVERLOAD !! W -\n```",
            "```diff\n- NING !! SYSTEM OVERLOAD !! WAR -\n```",
            "```diff\n- NG !! SYSTEM OVERLOAD !! WARNI -\n```",
            "```diff\n-  !! SYSTEM OVERLOAD !! WARNING -\n```",
            "```diff\n- ! SYSTEM OVERLOAD !! WARNING ! -\n```",
            "```diff\n- IMMINENT SHUT-DOWN IN 0.5 SEC! -\n```",
            "```diff\n- WARNING !! SYSTEM OVERLOAD !!  -\n```",
            "```diff\n- IMMINENT SHUT-DOWN IN 0.2 SEC! -\n```",
            "```diff\n- SYSTEM OVERLOAD !! WARNING !!  -\n```",
            "```diff\n- IMMINENT SHUT-DOWN IN 0.01 SEC! -\n```",
            f"```diff\n- SHUT-DOWN EXIT ERROR {FACE} -\n```",
            "```diff\n- CTRL + R FOR MANUAL OVERRIDE... -\n```",
        )

        for i in ls:
            await msg.edit(content=i)
            await ctx.release(1)

    @commands.command(name="imagine")
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def _imagine_a_place(self, ctx: Context, *, text: commands.clean_content):
        """Generates a Image in discord styling"""
        await ctx.send(file=await imagine(text))

    @commands.command(name="timecard")
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def _timecard_spn(self, ctx: Context, *, text: commands.clean_content):
        """Generates a timecard"""
        await ctx.send(file=await timecard(text))

    @commands.command(name="typingtest")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def typing_test(
        self,
        ctx: Context,
    ):
        """Test your typing skills"""
        confirm: discord.Message = await ctx.send(
            f"{ctx.author.mention} click on \N{WHITE HEAVY CHECK MARK} to start"
        )
        await confirm.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        def check1(r: discord.Reaction, u: discord.User):
            return (
                u.id == ctx.author.id and str(r.emoji) == "\N{WHITE HEAVY CHECK MARK}"
            )

        try:
            await ctx.wait_for("reaction_add", check=check1, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.message.add_reaction("\N{ALARM CLOCK}")

        line = random.choice(_random_sentences)
        main = "\u200b".join(line)
        await ctx.send(
            f"{ctx.author.mention} typing test started. Type the following phrase: ```ini\n[{main}]```"
        )

        def check2(m: discord.Message) -> bool:
            return (
                m.author.id == ctx.author.id
                and m.channel.id == ctx.channel.id
                and (rapidfuzz.fuzz.ratio(m.content, line) >= 75)
            )

        ini = time.perf_counter()

        try:
            msg: discord.Message = await ctx.wait_for(
                "message", check=check2, timeout=300
            )
        except asyncio.TimeoutError:
            return await ctx.message.add_reaction("\N{ALARM CLOCK}")
        fin = time.perf_counter()

        fakecontent = msg.content.replace(",", "").replace(".", "").replace("!", "")

        accuracy = rapidfuzz.fuzz.ratio(msg.content, line)
        wpm = round(len(fakecontent.split(" ")) / (fin - ini) * 60, 2)

        await ctx.database_game_update(
            "typing_test", set={"speed": fin - ini, "accuracy": accuracy, "wpm": wpm}
        )
        await ctx.send(
            f"{ctx.author.mention} your accuracy is `{accuracy}`%. "
            f"You typed in `{round(fin - ini, 2)}` seconds. "
            f"Words per minute: `{wpm}`"
        )

    @commands.command(name="reactiontest")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def reaction_test(self, ctx: Context):
        """Reaction test, REACT AS FAST AS POSSIBLE"""
        EMOJIS: List[Emoji] = random.sample(EMOJI_DB, 5)
        emoji = random.choice(EMOJIS)
        confirm: discord.Message = await ctx.send(
            f"{ctx.author.mention} click on \N{WHITE HEAVY CHECK MARK} to start."
        )
        await confirm.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        def check_1(r: discord.Reaction, u: discord.User):
            return (
                u.id == ctx.author.id and str(r.emoji) == "\N{WHITE HEAVY CHECK MARK}"
            )

        try:
            await ctx.wait_for("reaction_add", check=check_1, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.message.add_reaction("\N{ALARM CLOCK}")

        await ctx.bulk_add_reactions(confirm, *[e.emoji for e in EMOJIS])
        await ctx.release(random.uniform(1.5, 2.5))
        await confirm.edit(
            content=f"{ctx.author.mention} React as fast as possible on {emoji.emoji} **NOW**."
        )

        def check_2(reaction: discord.Reaction, user: discord.Member) -> bool:
            return (
                (str(reaction.emoji) == emoji.emoji)
                and (reaction.message.id == confirm.id)
                and (user.id == ctx.author.id)
            )

        start = time.perf_counter()
        await ctx.wait_for("reaction_add", check=check_2)
        end = time.perf_counter()

        await confirm.edit(content=f"{ctx.author.mention} reacted on {end-start:.2f}s")

        await self.bot.game_collections.update_one(
            {"_id": ctx.author.id},
            {
                "$set": {"game_reaction_test_time": end - start},
                "$inc": {"game_reaction_test_played": 1},
            },
            upsert=True,
        )

    @commands.command(name="bottomify", aliases=["bottom"])
    async def _bottomify(self, ctx: Context, *, text: commands.clean_content):
        """Bottomify your text"""
        text = await self.bot.func(to_bottom, text)
        if len(text) > 2000:
            await ctx.reply(text[:2000])
        else:
            await ctx.reply(text)

    @commands.command(name="debottomify", aliases=["debottom"])
    async def _debottomify(self, ctx: Context, *, text: commands.clean_content):
        """Debottomify your text"""
        text = await self.bot.func(from_bottom, text)
        if len(text) > 2000:
            await ctx.reply(text[:2000])
        else:
            await ctx.reply(text)
