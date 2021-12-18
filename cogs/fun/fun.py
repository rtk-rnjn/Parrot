from __future__ import annotations
import functools

import discord, random, io, base64, datetime, aiohttp, urllib, asyncio, time, json, re, string
from discord.ext import commands, tasks
from pathlib import Path
from discord.ext.commands import command, guild_only, bot_has_permissions, cooldown, BucketType
from random import choice
from discord import Embed 
from dataclasses import dataclass
from collections import defaultdict
from utilities.database import parrot_db
from aiohttp import request
import operator
from rapidfuzz import fuzz
from utilities.paginator import Paginator, PaginationView
from core import Parrot, Context, Cog
from typing import Callable, Optional, Union

with open("extra/truth.txt") as f:
  _truth = f.read()

with open("extra/dare.txt") as g:
  _dare = g.read()

with open("extra/lang.json") as lang:
    lg = json.load(lang)

from typing import List, Optional

with open(Path("extra/anagram.json"), "r") as f:
    ANAGRAMS_ALL = json.load(f)

def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message

ALL_WORDS = Path("extra/hangman_words.txt").read_text().splitlines()

IMAGES = {
    6: "https://cdn.discordapp.com/attachments/859123972884922418/888133201497837598/hangman0.png",
    5: "https://cdn.discordapp.com/attachments/859123972884922418/888133595259084800/hangman1.png",
    4: "https://cdn.discordapp.com/attachments/859123972884922418/888134194474139688/hangman2.png",
    3: "https://cdn.discordapp.com/attachments/859123972884922418/888133758069395466/hangman3.png",
    2: "https://cdn.discordapp.com/attachments/859123972884922418/888133786724859924/hangman4.png",
    1: "https://cdn.discordapp.com/attachments/859123972884922418/888133828831477791/hangman5.png",
    0: "https://cdn.discordapp.com/attachments/859123972884922418/888133845449338910/hangman6.png",
}


response = ["All signs point to yes...",
            "Yes!", 
            "My sources say nope.", 
            "You may rely on it.", 
            "Concentrate and ask again...", 
            "Outlook not so good...", 
            "It is decidedly so!", 
            "Better not tell you.", 
            "Very doubtful.", 
            "Yes - Definitely!", 
            "It is certain!", 
            "Most likely.", 
            "Ask again later.", 
            "No!", 
            "Outlook good.", 
            "Don't count on it.", 
            "Why not", 
            "Probably", 
            "Can't say", 
            "Well well..."
]

NEGATIVE_REPLIES = [
    "Noooooo!!",
    "Nope.",
    "I'm sorry Dave, I'm afraid I can't do that.",
    "I don't think so.",
    "Not gonna happen.",
    "Out of the question.",
    "Huh? No.",
    "Nah.",
    "Naw.",
    "Not likely.",
    "No way, José.",
    "Not in a million years.",
    "Fat chance.",
    "Certainly not.",
    "NEGATORY.",
    "Nuh-uh.",
    "Not in my house!",
]

UWU_WORDS = {
        "fi": "fwi",
        "l": "w",
        "r": "w",
        "some": "sum",
        "th": "d",
        "thing": "fing",
        "tho": "fo",
        "you're": "yuw'we",
        "your": "yur",
        "you": "yuw",
    }

DEFAULT_QUESTION_LIMIT = 7
STANDARD_VARIATION_TOLERANCE = 88
DYNAMICALLY_GEN_VARIATION_TOLERANCE = 97
TIME_LIMIT = 60
MAX_ERROR_FETCH_TRIES = 3

WRONG_ANS_RESPONSE = [
    "No one answered correctly!",
    "Better luck next time...",
]

RULES = (
    "No cheating and have fun!",
    "Points for each question reduces by 25 after 10s or after a hint. Total time is 30s per question"
)

WIKI_FEED_API_URL = "https://en.wikipedia.org/api/rest_v1/feed/featured/{date}"
TRIVIA_QUIZ_ICON = (
    "https://raw.githubusercontent.com/python-discord/branding/main/icons/trivia_quiz/trivia-quiz-dist.png"
)

@dataclass(frozen=True)
class QuizEntry:
    """Stores quiz entry (a question and a list of answers)."""

    question: str
    answers: list[str]
    var_tol: int

class AnagramGame:
    """
    Used for creating instances of anagram games.
    Once multiple games can be run at the same time, this class' instances
    can be used for keeping track of each anagram game.
    """

    def __init__(self, scrambled: str, correct: list[str]) -> None:
        self.scrambled = scrambled
        self.correct = set(correct)

        self.winners = set()

    async def message_creation(self, message: discord.Message) -> None:
        """Check if the message is a correct answer and remove it from the list of answers."""
        if message.content.lower() in self.correct:
            self.winners.add(message.author.mention)
            self.correct.remove(message.content.lower())


class DynamicQuestionGen:
    """Class that contains functions to generate math/science questions for TriviaQuiz Cog."""

    N_PREFIX_STARTS_AT = 5
    N_PREFIXES = [
        "penta", "hexa", "hepta", "octa", "nona",
        "deca", "hendeca", "dodeca", "trideca", "tetradeca",
    ]

    PLANETS = [
        ("1st", "Mercury"),
        ("2nd", "Venus"),
        ("3rd", "Earth"),
        ("4th", "Mars"),
        ("5th", "Jupiter"),
        ("6th", "Saturn"),
        ("7th", "Uranus"),
        ("8th", "Neptune"),
    ]

    TAXONOMIC_HIERARCHY = [
        "species", "genus", "family", "order",
        "class", "phylum", "kingdom", "domain",
    ]

    UNITS_TO_BASE_UNITS = {
        "hertz": ("(unit of frequency)", "s^-1"),
        "newton": ("(unit of force)", "m*kg*s^-2"),
        "pascal": ("(unit of pressure & stress)", "m^-1*kg*s^-2"),
        "joule": ("(unit of energy & quantity of heat)", "m^2*kg*s^-2"),
        "watt": ("(unit of power)", "m^2*kg*s^-3"),
        "coulomb": ("(unit of electric charge & quantity of electricity)", "s*A"),
        "volt": ("(unit of voltage & electromotive force)", "m^2*kg*s^-3*A^-1"),
        "farad": ("(unit of capacitance)", "m^-2*kg^-1*s^4*A^2"),
        "ohm": ("(unit of electric resistance)", "m^2*kg*s^-3*A^-2"),
        "weber": ("(unit of magnetic flux)", "m^2*kg*s^-2*A^-1"),
        "tesla": ("(unit of magnetic flux density)", "kg*s^-2*A^-1"),
    }

    @classmethod
    def linear_system(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a system of linear equations with two unknowns."""
        x, y = random.randint(2, 5), random.randint(2, 5)
        answer = a_format.format(x, y)

        coeffs = random.sample(range(1, 6), 4)

        question = q_format.format(
            coeffs[0],
            coeffs[1],
            coeffs[0] * x + coeffs[1] * y,
            coeffs[2],
            coeffs[3],
            coeffs[2] * x + coeffs[3] * y,
        )

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def mod_arith(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a basic modular arithmetic question."""
        quotient, m, b = random.randint(30, 40), random.randint(10, 20), random.randint(200, 350)
        ans = random.randint(0, 9)  # max remainder is 9, since the minimum modulus is 10
        a = quotient * m + ans - b

        question = q_format.format(a, b, m)
        answer = a_format.format(ans)

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def ngonal_prism(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a question regarding vertices on n-gonal prisms."""
        n = random.randint(0, len(cls.N_PREFIXES) - 1)

        question = q_format.format(cls.N_PREFIXES[n])
        answer = a_format.format((n + cls.N_PREFIX_STARTS_AT) * 2)

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def imag_sqrt(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a negative square root question."""
        ans_coeff = random.randint(3, 10)

        question = q_format.format(ans_coeff ** 2)
        answer = a_format.format(ans_coeff)

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def binary_calc(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a binary calculation question."""
        a = random.randint(15, 20)
        b = random.randint(10, a)
        oper = random.choice(
            (
                ("+", operator.add),
                ("-", operator.sub),
                ("*", operator.mul),
            )
        )

        # if the operator is multiplication, lower the values of the two operands to make it easier
        if oper[0] == "*":
            a -= 5
            b -= 5

        question = q_format.format(a, oper[0], b)
        answer = a_format.format(oper[1](a, b))

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def solar_system(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a question on the planets of the Solar System."""
        planet = random.choice(cls.PLANETS)

        question = q_format.format(planet[0])
        answer = a_format.format(planet[1])

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def taxonomic_rank(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a question on taxonomic classification."""
        level = random.randint(0, len(cls.TAXONOMIC_HIERARCHY) - 2)

        question = q_format.format(cls.TAXONOMIC_HIERARCHY[level])
        answer = a_format.format(cls.TAXONOMIC_HIERARCHY[level + 1])

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def base_units_convert(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a SI base units conversion question."""
        unit = random.choice(list(cls.UNITS_TO_BASE_UNITS))

        question = q_format.format(
            unit + " " + cls.UNITS_TO_BASE_UNITS[unit][0]
        )
        answer = a_format.format(
            cls.UNITS_TO_BASE_UNITS[unit][1]
        )

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)


DYNAMIC_QUESTIONS_FORMAT_FUNCS = {
    201: DynamicQuestionGen.linear_system,
    202: DynamicQuestionGen.mod_arith,
    203: DynamicQuestionGen.ngonal_prism,
    204: DynamicQuestionGen.imag_sqrt,
    205: DynamicQuestionGen.binary_calc,
    301: DynamicQuestionGen.solar_system,
    302: DynamicQuestionGen.taxonomic_rank,
    303: DynamicQuestionGen.base_units_convert,
}


class Colours:
    blue = 0x0279FD
    bright_green = 0x01D277
    dark_green = 0x1F8B4C
    orange = 0xE67E22
    pink = 0xCF84E0
    purple = 0xB734EB
    soft_green = 0x68C290
    soft_orange = 0xF9CB54
    soft_red = 0xCD6D6D
    yellow = 0xF9F586
    python_blue = 0x4B8BBE
    python_yellow = 0xFFD43B
    grass_green = 0x66FF00
    gold = 0xE6C200

    easter_like_colours = [
        (255, 247, 0),
        (255, 255, 224),
        (0, 255, 127),
        (189, 252, 201),
        (255, 192, 203),
        (255, 160, 122),
        (181, 115, 220),
        (221, 160, 221),
        (200, 162, 200),
        (238, 130, 238),
        (135, 206, 235),
        (0, 204, 204),
        (64, 224, 208),
    ]

def replace_many(
    sentence: str, replacements: dict, *, ignore_case: bool = False, match_case: bool = False
) -> str:

    if ignore_case:
        replacements = dict(
            (word.lower(), replacement) for word, replacement in replacements.items()
        )

    words_to_replace = sorted(replacements, key=lambda s: (-len(s), s))

    # Join and compile words to replace into a regex
    pattern = "|".join(re.escape(word) for word in words_to_replace)
    regex = re.compile(pattern, re.I if ignore_case else 0)

    def _repl(match: re.Match) -> str:
        """Returns replacement depending on `ignore_case` and `match_case`."""
        word = match.group(0)
        replacement = replacements[word.lower() if ignore_case else word]

        if not match_case:
            return replacement

        # Clean punctuation from word so string methods work
        cleaned_word = word.translate(str.maketrans("", "", string.punctuation))
        if cleaned_word.isupper():
            return replacement.upper()
        elif cleaned_word[0].isupper():
            return replacement.capitalize()
        else:
            return replacement.lower()

    return regex.sub(_repl, sentence)


class Fun(Cog, command_attrs={'cooldown': commands.CooldownMapping.from_cooldown(1, 5.0, commands.BucketType.member)}):
    """Parrot gives you huge amount of fun commands, so that you won't get bored"""

    def __init__(self, bot: Parrot):
        self.bot = bot

        self.game_status = {}  # A variable to store the game status: either running or not running.
        self.game_owners = {}  # A variable to store the person's ID who started the quiz game in a channel.

        self.questions = self.load_questions()
        self.question_limit = 0
        self.games: dict[int, AnagramGame] = {}
        
        self.player_scores = defaultdict(int)  # A variable to store all player's scores for a bot session.
        self.game_player_scores = {}  # A variable to store temporary game player's scores.

        self.categories = {
            "general": "Test your general knowledge.",
            "retro": "Questions related to retro gaming.",
            "math": "General questions about mathematics ranging from grade 8 to grade 12.",
            "science": "Put your understanding of science to the test!",
            "cs": "A large variety of computer science questions.",
            "python": "Trivia on our amazing language, Python!",
            "wikipedia": "Guess the title of random wikipedia passages.",
        }

        self.get_wiki_questions.start()

    def cog_unload(self) -> None:
        """Cancel `get_wiki_questions` task when Cog will unload."""
        self.get_wiki_questions.cancel()
    
    @staticmethod
    def create_embed(tries: int, user_guess: str) -> Embed:
        """
        Helper method that creates the embed where the game information is shown.
        This includes how many letters the user has guessed so far, and the hangman photo itself.
        """
        hangman_embed = Embed(
            title="Hangman",
            color=Colours.python_blue,
        )
        hangman_embed.set_image(url=IMAGES[tries])
        hangman_embed.add_field(
            name=f"You've guessed `{user_guess}` so far.",
            value="Guess the word by sending a message with a letter!"
        )
        hangman_embed.set_footer(text=f"Tries remaining: {tries} | You have 60s to guess.")
        return hangman_embed

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='fun', id=892432619374014544)

    async def _get_discord_message(self, ctx: Context, text: str) -> Union[discord.Message, str]:
        """
        Attempts to convert a given `text` to a discord Message object and return it.
        Conversion will succeed if given a discord Message ID or link.
        Returns `text` if the conversion fails.
        """
        try:
            text = await commands.MessageConverter().convert(ctx, text)
        except commands.BadArgument:
            return
        return text

    async def _get_text_and_embed(self, ctx: Context, text: str) -> tuple[str, Optional[Embed]]:
        embed = None

        msg = await self._get_discord_message(ctx, text)
        # Ensure the user has read permissions for the channel the message is in
        if isinstance(msg, discord.Message):
            permissions = msg.channel.permissions_for(ctx.author)
            if permissions.read_messages:
                text = msg.clean_content
                # Take first embed because we can't send multiple embeds
                if msg.embeds:
                    embed = msg.embeds[0]

        return (text, embed)
    
    def _convert_embed(self, func: Callable[[str, ], str], embed: Embed) -> Embed:
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

        return Embed.from_dict(embed_dict)
    
    @tasks.loop(hours=24.0)
    async def get_wiki_questions(self) -> None:
        """Get yesterday's most read articles from wikipedia and format them like trivia questions."""
        error_fetches = 0
        wiki_questions = []
        # trivia_quiz.json follows a pattern, every new category starts with the next century.
        start_id = 501
        yesterday = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(1), '%Y/%m/%d')

        while error_fetches < MAX_ERROR_FETCH_TRIES:
            async with self.bot.http_session.get(url=WIKI_FEED_API_URL.format(date=yesterday)) as r:
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
                            rf'\b{word.strip(string.punctuation)}\b', word, title, flags=re.IGNORECASE
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
                        question = re.sub(rf'\b{word}\b', f"**{secret_word}**", question, flags=re.IGNORECASE)

                    formatted_article_question = {
                        "id": start_id,
                        "question": f"Guess the title of the Wikipedia article.\n\n{question}",
                        "answer": cleaned_title,
                        "info": article["extract"]
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
    
    @commands.command(name="anagram", aliases=("anag", "gram", "ag"))
    @commands.guild_only()
    async def anagram_command(self, ctx: commands.Context) -> None:
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
        await asyncio.sleep(TIME_LIMIT)

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

        game = self.games.get(message.channel.id)
        if not game:
            return

        await game.message_creation(message)

    @commands.group(name="quiz", aliases=("trivia", "triviaquiz"), invoke_without_command=True)
    async def quiz_game(self, ctx: Context, category: Optional[str], questions: Optional[int]) -> None:
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
            await ctx.send(
                "Game is already running... "
                f"do `{ctx.prefix}quiz stop`"
            )
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

            elif questions < 1:
                await ctx.send(
                    embed=self.make_error_embed(
                        "You must choose to complete at least one question. "
                        f"(or enter nothing for the default value of {DEFAULT_QUESTION_LIMIT} questions)"
                    )
                )
                return

            else:
                self.question_limit = questions

        # Start game if not running.
        if not self.game_status[ctx.channel.id]:
            self.game_owners[ctx.channel.id] = ctx.author
            self.game_status[ctx.channel.id] = True
            start_embed = self.make_start_embed(category)

            await ctx.send(embed=start_embed)  # send an embed with the rules
            await asyncio.sleep(5)

        done_questions = []
        hint_no = 0
        quiz_entry = None

        while self.game_status[ctx.channel.id]:
            # Exit quiz if number of questions for a round are already sent.
            if len(done_questions) == self.question_limit and hint_no == 0:
                await ctx.send("The round has ended.")
                await self.declare_winner(ctx.channel, self.game_player_scores[ctx.channel.id])

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

                if "dynamic_id" not in question_dict:
                    quiz_entry = QuizEntry(
                        question_dict["question"],
                        quiz_answers if isinstance(quiz_answers := question_dict["answer"], list) else [quiz_answers],
                        STANDARD_VARIATION_TOLERANCE
                    )
                else:
                    format_func = DYNAMIC_QUESTIONS_FORMAT_FUNCS[question_dict["dynamic_id"]]
                    quiz_entry = format_func(
                        question_dict["question"],
                        question_dict["answer"],
                    )

                embed = discord.Embed(
                    colour=Colours.gold,
                    title=f"Question #{len(done_questions)}",
                    description=quiz_entry.question,
                )

                if img_url := question_dict.get("img_url"):
                    embed.set_image(url=img_url)

                await ctx.send(embed=embed)

            # def check_func(variation_tolerance: int) -> Callable[[discord.Message], bool]:
            #     def contains_correct_answer(m: discord.Message) -> bool:
            #         return (m.channel == ctx.channel) and any(
            #             fuzz.ratio(answer.lower(), m.content.lower()) > variation_tolerance
            #             for answer in quiz_entry.answers
            #         )

            #     return contains_correct_answer
            
            def check(m: discord.Message) -> bool:
                return (m.channel.id == ctx.channel.id) and any(
                    fuzz.ratio(answer.lower(), m.content.lower()) > quiz_entry.var_tol for answer in quiz_entry.answers)
            
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=10)
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
                    await asyncio.sleep(1)

                    hint_no = 0  # Reset the hint counter so that on the next round, it's in the initial state

                    await self.send_score(ctx.channel, self.game_player_scores[ctx.channel.id])
                    await asyncio.sleep(2)
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

                await ctx.send(f"{msg.author.mention} got the correct answer :tada: {points} points!")

                await self.send_answer(
                    ctx.channel,
                    quiz_entry.answers,
                    True,
                    question_dict,
                    self.question_limit - len(done_questions),
                )
                await self.send_score(ctx.channel, self.game_player_scores[ctx.channel.id])

                await asyncio.sleep(2)

    def make_start_embed(self, category: str) -> discord.Embed:
        """Generate a starting/introduction embed for the quiz."""
        rules = "\n".join([f"{index}: {rule}" for index, rule in enumerate(RULES, start=1)])

        start_embed = discord.Embed(
            title="Quiz game Starting!!",
            description=(
                f"Each game consists of {self.question_limit} questions.\n"
                f"**Rules :**\n{rules}"
                f"\n **Category** : {category}"
            ),
            colour=Colours.blue
        )
        start_embed.set_thumbnail(url=TRIVIA_QUIZ_ICON)

        return start_embed

    @staticmethod
    def make_error_embed(desc: str) -> discord.Embed:
        """Generate an error embed with the given description."""
        error_embed = discord.Embed(
            colour=Colours.soft_red,
            title=random.choice(NEGATIVE_REPLIES),
            description=desc,
        )

        return error_embed

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def hangman(
            self,
            ctx: commands.Context,
            min_length: int = 0,
            max_length: int = 25,
            min_unique_letters: int = 0,
            max_unique_letters: int = 25,
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
            word for word in ALL_WORDS
            if min_length < len(word) < max_length
            and min_unique_letters < len(set(word)) < max_unique_letters
        ]

        if not filtered_words:
            filter_not_found_embed = Embed(
                title=choice(NEGATIVE_REPLIES),
                description="No words could be found that fit all filters specified.",
                color=Colours.soft_red,
            )
            await ctx.send(content=f"{ctx.author.mention}", embed=filter_not_found_embed)
            return

        word = choice(filtered_words)
        # `pretty_word` is used for comparing the indices where the guess of the user is similar to the word
        # The `user_guess` variable is prettified by adding spaces between every dash, and so is the `pretty_word`
        pretty_word = ''.join([f"{letter} " for letter in word])[:-1]
        user_guess = ("_ " * len(word))[:-1]
        tries = 6
        guessed_letters = set()

        def check(msg: discord.Message) -> bool:
            return msg.author == ctx.author and msg.channel == ctx.channel

        original_message = await ctx.send(
            content=f"{ctx.author.mention}",
            embed=Embed(
            title="Hangman",
            description="Loading game...",
            color=Colours.soft_green
        ))

        # Game loop
        while user_guess.replace(' ', '') != word:
            # Edit the message to the current state of the game
            await original_message.edit(content=f"{ctx.author.mention}", embed=self.create_embed(tries, user_guess))

            try:
                message = await self.bot.wait_for(
                    event="message",
                    timeout=60.0,
                    check=check
                )
            except Exception:
                timeout_embed = Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="Looks like the bot timed out! You must send a letter within 60 seconds.",
                    color=Colours.soft_red,
                )
                await original_message.edit(content=f"{ctx.author.mention}", embed=timeout_embed)
                return

            # If the user enters a capital letter as their guess, it is automatically converted to a lowercase letter
            normalized_content = message.content.lower()
            # The user should only guess one letter per message
            if len(normalized_content) > 1:
                letter_embed = Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="You can only send one letter at a time, try again!",
                    color=Colours.dark_green,
                )
                await ctx.send(content=f"{ctx.author.mention}", embed=letter_embed, delete_after=4)
                continue

            # Checks for repeated guesses
            elif normalized_content in guessed_letters:
                already_guessed_embed = Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description=f"You have already guessed `{normalized_content}`, try again!",
                    color=Colours.dark_green,
                )
                await ctx.send(content=f"{ctx.author.mention}", embed=already_guessed_embed, delete_after=4)
                continue

            # Checks for correct guesses from the user
            elif normalized_content in word:
                positions = {idx for idx, letter in enumerate(pretty_word) if letter == normalized_content}
                user_guess = "".join(
                    [normalized_content if index in positions else dash for index, dash in enumerate(user_guess)]
                )

            else:
                tries -= 1

                if tries <= 0:
                    losing_embed = Embed(
                        title="You lost.",
                        description=f"The word was `{word}`.",
                        color=Colours.soft_red,
                    )
                    await original_message.edit(
                        content=f"{ctx.author.mention}",
                        embed=self.create_embed(tries, user_guess))
                    await ctx.send(content=f"{ctx.author.mention}", embed=losing_embed)
                    return

            guessed_letters.add(normalized_content)

        # The loop exited meaning that the user has guessed the word
        await original_message.edit(content=f"{ctx.author.mention}", embed=self.create_embed(tries, user_guess))
        win_embed = Embed(
            title="You won!",
            description=f"The word was `{word}`.",
            color=Colours.grass_green
        )
        return await ctx.send(content=f"{ctx.author.mention}", embed=win_embed)

    @quiz_game.command(name="stop")
    async def stop_quiz(self, ctx: commands.Context) -> None:
        """
        Stop a quiz game if its running in the channel.
        Note: Only mods or the owner of the quiz can stop it.
        """
        try:
            if self.game_status[ctx.channel.id]:
                # Check if the author is the game starter or a moderator.
                if ctx.author == self.game_owners[ctx.channel.id]:
                    self.game_status[ctx.channel.id] = False
                    del self.game_owners[ctx.channel.id]
                    self.game_player_scores[ctx.channel.id] = {}

                    await ctx.send("Quiz stopped.")
                    await self.declare_winner(ctx.channel, self.game_player_scores[ctx.channel.id])

                else:
                    await ctx.send(f"{ctx.author.mention}, you are not authorised to stop this game :ghost:!")
            else:
                await ctx.send("No quiz running.")
        except KeyError:
            await ctx.send("No quiz running.")

    @quiz_game.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context) -> None:
        """View everyone's score for this bot session."""
        await self.send_score(ctx.channel, self.player_scores)

    @staticmethod
    async def send_score(channel: discord.TextChannel, player_data: dict) -> None:
        """Send the current scores of players in the game channel."""
        if len(player_data) == 0:
            await channel.send("No one has made it onto the leaderboard yet.")
            return

        embed = discord.Embed(
            colour=Colours.blue,
            title="Score Board",
            description="",
        )
        embed.set_thumbnail(url=TRIVIA_QUIZ_ICON)

        sorted_dict = sorted(player_data.items(), key=operator.itemgetter(1), reverse=True)
        for item in sorted_dict:
            embed.description += f"{item[0]}: {item[1]}\n"

        await channel.send(embed=embed)

    @staticmethod
    async def declare_winner(channel: discord.TextChannel, player_data: dict) -> None:
        """Announce the winner of the quiz in the game channel."""
        if player_data:
            highest_points = max(list(player_data.values()))
            no_of_winners = list(player_data.values()).count(highest_points)

            # Check if more than 1 player has highest points.
            if no_of_winners > 1:
                winners = []
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

        embed.set_footer(text="If a category is not chosen, a random one will be selected.")

        for cat, description in self.categories.items():
            embed.description += (
                f"**- {cat.capitalize()}**\n"
                f"{description.capitalize()}\n"
            )

        return embed

    @staticmethod
    async def send_answer(
        channel: discord.TextChannel,
        answers: list[str],
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
            ("Let's move to the next question." if q_left > 0 else "")
            + f"\nRemaining questions: {q_left}"
        )
        await channel.send(embed=embed)

    @command(name='8ball')
    @Context.with_type
    async def _8ball(self, ctx: Context, *, question:commands.clean_content):
        """
        8ball Magic, nothing to say much
        """
        await ctx.reply(f'Question: **{question}**\nAnswer: **{random.choice(response)}**')

    @commands.command()
    @Context.with_type
    async def choose(self, ctx: Context, *, options:commands.clean_content):
        """
        Confuse something with your decision? Let Parrot choose from your choice.
        NOTE: The `Options` should be seperated by commas `,`.
        """
        options = options.split(',')
        await ctx.reply(f'{ctx.author.mention} I choose {choice(options)}')
  

    @commands.command(aliases=['colours', 'colour'])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def color(self, ctx: Context, colour):
        """
        To get colour information using the hexadecimal codes.
        """
        
        link = f"https://www.thecolorapi.com/id?format=json&hex={colour}"
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                if response.status == 200:
                    res = await response.json()
                else:
                    return

        green = round(res['rgb']['fraction']['g'], 2)
        red = round(res['rgb']['fraction']['r'], 2)
        blue = round(res['rgb']['fraction']['b'], 2)
        _green = res['rgb']['g']
        _red = res['rgb']['r']
        _blue = res['rgb']['b']
        
        #HSL VALUE
        hue = round(res['hsl']['fraction']['h'], 2)
        saturation = round(res['hsl']['fraction']['s'], 2)
        lightness = round(res['hsl']['fraction']['l'], 2)
        _hue = res['hsl']['h']
        _saturation = res['hsl']['s']
        _lightness = res['hsl']['l']
        
        #HSV VALUE
        hue_ = round(res['hsv']['fraction']['h'], 2)
        saturation_ = round(res['hsv']['fraction']['s'], 2)
        value_ = round(res['hsv']['fraction']['v'], 2)
        _hue_ = res['hsv']['h']
        _saturation_ = res['hsv']['s']
        _value_ = res['hsv']['v']
        
        #GENERAL
        name = res['name']['value']
        close_name_hex = res['name']['closest_named_hex']
        exact_name = res['name']['exact_match_name']
        distance = res['name']['distance']

        embed = discord.Embed(title="Parrot colour prompt", timestamp=datetime.datetime.utcnow(), colour = discord.Color.from_rgb(_red, _green, _blue), description=f"Colour name: `{name}` | Close Hex code: `{close_name_hex}` | Having exact name? `{exact_name}` | Distance: `{distance}`")
        embed.set_thumbnail(url=f"https://some-random-api.ml/canvas/colorviewer?hex={colour}")
        embed.set_footer(text=f"{ctx.author.name}")
        fields = [
            ("RGB value (fraction)", f"Red: `{_red}` (`{red}`)\nGreen: `{_green}` (`{green}`)\nBlue: `{_blue}` (`{blue}`)", True),
            ("HSL value (fraction)", f"Hue: `{_hue}` (`{hue}`)\nSaturation: `{_saturation}` (`{saturation}`)\nLightness: `{_lightness}` (`{lightness}`)", True),
            ("HSV value (fraction)", f"Hue: `{_hue_}` (`{hue_}`)\nSaturation: `{_saturation_}` (`{saturation_}`)\nValue: `{_value_}` (`{value_}`)", True)		
          ]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        await ctx.reply(embed=embed)
      
  
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def decode(self, ctx: Context, *, string:str):
        """
        Decode the code to text from Base64 encryption
        """
        base64_string = string
        base64_bytes = base64_string.encode("ascii") 
        
        sample_string_bytes = base64.b64decode(base64_bytes) 
        sample_string = sample_string_bytes.decode("ascii") 
        
        embed = discord.Embed(title="Decoding...", colour=discord.Colour.red(), timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Encoded text:", value=f'```\n{base64_string}\n```', inline=False)
        embed.add_field(name="Decoded text:", value=f'```\n{sample_string}\n```', inline=False)
        embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/4/45/Parrot_Logo.png')
        embed.set_footer(text=f"{ctx.author.name}", icon_url=f'{ctx.author.display_avatar.url}')
        await ctx.reply(embed=embed)



    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def encode(self, ctx: Context, *, string:str):
        """
        Encode the text to Base64 Encryption and in Binary
        """
        sample_string = string
        sample_string_bytes = sample_string.encode("ascii") 
        res = ''.join(format(ord(i), 'b') for i in string)
        base64_bytes = base64.b64encode(sample_string_bytes) 
        base64_string = base64_bytes.decode("ascii") 
        
        embed = discord.Embed(title="Encoding...", colour=discord.Colour.red(), timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Normal [string] text:", value=f'```\n{sample_string}\n```', inline=False)
        embed.add_field(name="Encoded [base64]:", value=f'```\n{base64_string}\n```', inline=False)
        embed.add_field(name="Encoded [binary]:", value=f'```\n{str(res)}\n```', inline=False)
        embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/4/45/Parrot_Logo.png')
        embed.set_footer(text=f"{ctx.author.name}", icon_url=f'{ctx.author.display_avatar.url}')
        await ctx.reply(embed=embed)

  
      
    @commands.command(name="fact")
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def animal_fact(self, ctx: Context, *, animal: str):
        """
        Return a random Fact. It's useless command, I know

        NOTE: Available animals - Dog, Cat, Panda, Fox, Bird, Koala
        """
        if (animal := animal.lower()) in ("dog", "cat", "panda", "fox", "bird", "koala"):
            fact_url = f"https://some-random-api.ml/facts/{animal}"
            image_url = f"https://some-random-api.ml/img/{'birb' if animal == 'bird' else animal}"

            async with request("GET", image_url, headers={}) as response:
                if response.status == 200:
                    data = await response.json()
                    image_link = data["link"]

                else:
                    image_link = None

            async with request("GET", fact_url, headers={}) as response:
                if response.status == 200:
                    data = await response.json()

                    embed = Embed(title=f"{animal.title()} fact", description=data["fact"], colour=ctx.author.colour)
                    if image_link is not None:
                        embed.set_image(url=image_link)
                        return await ctx.reply(embed=embed)

                    else:
                        return await ctx.reply(f"{ctx.author.mention} API returned a {response.status} status.")

                else:
                    return await ctx.reply(f"{ctx.author.mention} no facts are available for that animal. Available animals: `dog`, `cat`, `panda`, `fox`, `bird`, `koala`")


    @commands.command()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def gay(self, ctx: Context, *, member:discord.Member=None):
        """
        Image Generator. Gay Pride.
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get('https://some-random-api.ml/canvas/gay?avatar={}'.format(member.display_avatar.url)) as wastedImage: 
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'gay.png')) # replying the file


    @commands.command()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def glass(self, ctx: Context, *, member:discord.Member=None):
        """
        Provide a glass filter on your profile picture, try it!
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/glass?avatar={member.display_avatar.url}') as wastedImage: # get users avatar as png with 1024 size
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'glass.png')) # replying the file


    @commands.command()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def horny(self, ctx: Context, *, member:discord.Member=None):
        """
        Image generator, Horny card generator.
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/horny?avatar={member.display_avatar.url}.') as wastedImage: 
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'horny.png')) # replying the file


    @commands.command(aliases=['insult'])
    @Context.with_type
    async def roast(self, ctx: Context, *, member: discord.Member = None):
        """
        Insult your enemy, Ugh!
        """
        if member == None: member = ctx.author
        async with aiohttp.ClientSession() as session:
            async with session.get("https://insult.mattbas.org/api/insult") as response:
                insult = await response.text()
                await ctx.reply(f"**{member.name}** {insult}")



    @commands.command(aliases=['its-so-stupid'])
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def itssostupid(self, ctx, *, comment:str):
      """
      :\ I don't know what is this, I think a meme generator.
      """
      member = ctx.author
      if len(comment) > 20: comment = comment[:19:]
      async with aiohttp.ClientSession() as wastedSession:
          async with wastedSession.get(f'https://some-random-api.ml/canvas/its-so-stupid?avatar={member.display_avatar.url}&dog={comment}') as wastedImage: # get users avatar as png with 1024 size
              imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
              
              await wastedSession.close() # closing the session and;
              
              await ctx.reply(file=discord.File(imageData, 'itssostupid.png')) # replying the file

      

    @commands.command()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def jail(self, ctx: Context, *, member:discord.Member=None):
        """
        Image generator. Makes you behind the bars. Haha
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/jail?avatar={member.display_avatar.url}') as wastedImage: # get users avatar as png with 1024 size
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'jail.png')) # replying the file
  

    @commands.command()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def lolice(self, ctx: Context, *, member:discord.Member=None):
        """
        This command is not made by me. :\
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/lolice?avatar={member.display_avatar.url}') as wastedImage: # get users avatar as png with 1024 size
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'lolice.png')) # replying the file
  

    @commands.command(name='meme')
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def meme(self, ctx: Context):
        """
        Random meme generator.
        """
        link = "https://memes.blademaker.tv/api?lang=en"
        async with aiohttp.ClientSession() as session:
          async with session.get(link) as response:
              if response.status == 200:
                  res = await response.json()
              else:
                  return
        title = res['title']
        ups = res["ups"]
        downs = res["downs"]
        sub = res["subreddit"]

        embed = discord.Embed(title=f'{title}', description=f"{sub}", timestamp=datetime.datetime.utcnow())
        embed.set_image(url = res["image"])
        embed.set_footer(text=f"UP(s): {ups} | DOWN(s): {downs}") 

        await ctx.reply(embed=embed)
      

    @commands.command(aliases=['fakeprofile'])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def fakepeople(self, ctx: Context):
        """
        Fake Identity generator.
        """
        link = "https://randomuser.me/api/"
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                if response.status == 200:
                    res = await response.json()
                else:
                    return
        res = res['results'][0]
        name = f"{res['name']['title']} {res['name']['first']} {res['name']['last']}"
        address = f"{res['location']['street']['number']}, {res['location']['street']['name']}, {res['location']['city']}, {res['location']['state']}, {res['location']['country']}, {res['location']['postcode']}"
        cords = f"{res['location']['coordinates']['latitude']}, {res['location']['coordinates']['longitude']}"
        tz = f"{res['location']['timezone']['offset']}, {res['location']['timezone']['description']}"
        email = res['email']
        usrname = res['login']['username']
        pswd = res['login']['password']
        age = res['dob']['age']
        phone = f"{res['phone']}, {res['cell']}"
        pic = res['picture']['large']

        em = discord.Embed(title=f"{name}", description=f"```\n{address} {cords}```", timestamp=datetime.datetime.utcnow())
        em.add_field(name="Timezone", value=f"{tz}", inline=False)
        em.add_field(name="Email & Password", value=f"**Username:** {usrname}\n**Email:** {email}\n**Password:** {pswd}", inline=False)
        em.add_field(name="Age", value=f"{age}", inline=False)
        em.set_thumbnail(url=pic)
        em.add_field(name="Phone", value=f"{phone}", inline=False)
        em.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=em)


    @commands.command()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def simpcard(self, ctx: Context, *, member:discord.Member=None):
        """
        Good for those, who are hell simp! LOL
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/simpcard?avatar={member.display_avatar.url}') as wastedImage: # get users avatar as png with 1024 size
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'simpcard.png')) # replying the file

    @commands.command(aliases=['trans'])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def translate(self, ctx: Context, to: str, *, message: commands.clean_content=None):
        """
        Translates a message to English (default) using Google translate
        """
        if message is None:
            ref = ctx.message.reference
            if ref and isinstance(ref.resolved, discord.Message):
                message = ref.resolved.content
            else:
                return await ctx.reply(f"{ctx.author.mention} you must provide the message reference or message for translation")
        
        link = "https://translate-api.ml/translate?text={}&lang={}".format(message.lower(), to.lower() if to else 'en')

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                if response.status == 200:
                    data = await response.json()
                else:
                    return await ctx.reply(f"{ctx.author.mention} Something not right!")
                
        success = data['status']
        if success == 200:
            text = data['given']['text']
            lang = data['given']['lang']
            translated_text = data['translated']['text']
            translated_lang = data['translated']['lang']
            translated_pronunciation = data['translated']['pronunciation']
        else: 
            return await ctx.reply(f"{ctx.author.mention} Can not translate **{message[1000::]}** to **{to}**")
        
        if ctx.author.id == 741614468546560092: # its kinda spammy for me. lol
            return await ctx.send(f"{translated_text}")

        embed = discord.Embed(
            title="Translated", 
            description=f"```\n{translated_text}\n```",
            color=ctx.author.color, 
            timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"{ctx.author.name}")
        embed.add_field(name="Info", value=f"Tranlated from **{lg[lang]['name']}** to **{lg[translated_lang]['name']}**", inline=False)
        # embed.add_field(name="Pronunciation", value=f"```\n{translated_pronunciation}\n```", inline=False)
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/1/14/Google_Translate_logo_%28old%29.png")
        await ctx.reply(embed=embed)

    @commands.command(aliases=['triggered'])
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def trigger(self, ctx: Context, *, member:discord.Member=None):
        """
        User Triggered!
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/triggered?avatar={member.display_avatar.url}') as wastedImage: # get users avatar as png with 1024 size
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'triggered.gif')) # replying the file

    @commands.command(aliases=['def', 'urban'])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def urbandictionary(self, ctx: Context, *, text: commands.clean_content):
      """
      LOL. This command is insane.
      """
      t = text
      text = urllib.parse.quote(text)
      link = 'http://api.urbandictionary.com/v0/define?term=' + text 

      async with aiohttp.ClientSession() as session:
          async with session.get(link) as response:
              if response.status == 200:
                  res = await response.json()
              else:
                  return
      if not res['list']: return await ctx.reply(f"{ctx.author.mention} :\ **{t}** means nothings. Try something else")
      em_list = []
      for i in range(0, len(res['list'])):
          _def = res['list'][i]['definition']
          _link = res['list'][i]['permalink']
          thumbs_up = res['list'][i]['thumbs_up']
          thumbs_down = res['list'][i]['thumbs_down']
          author = res['list'][i]['author']
          example = res['list'][i]['example']
          word = res['list'][i]['word'].capitalize()	
          embed = discord.Embed(title=f"{word}", description=f"{_def}", url=f"{_link}", timestamp=datetime.datetime.utcnow())
          embed.add_field(name="Example", value=f"{example}")
          embed.set_author(name=f"Author: {author}")
          embed.set_footer(text=f"👍 {thumbs_up} • 👎 {thumbs_down}")
          em_list.append(embed)

      # paginator = Paginator(pages=em_list, timeout=60.0)
      # await paginator.start(ctx)
      await PaginationView(em_list).start(ctx=ctx)


    @commands.command()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def wasted(self, ctx: Context, *, member:discord.Member=None):
        """
        Overlay 'WASTED' on your profile picture, just like GTA:SA
        """
        if member is None: member = ctx.author
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/wasted?avatar={member.display_avatar.url}') as wastedImage: # get users avatar as png with 1024 size
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'wasted.png')) # replying the file
  

    @commands.command(aliases=['youtube-comment', 'youtube_comment'])
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    @Context.with_type
    async def ytcomment(self, ctx: Context, *, comment:str):
        """
        Makes a comment in YT. Best ways to fool your fool friends. :')
        """
        member = ctx.author
        if len(comment) > 1000: comment = comment[:999:]
        if len(member.name) > 20: name = member.name[:20:]
        else: name = member.name
        async with aiohttp.ClientSession() as wastedSession:
            async with wastedSession.get(f'https://some-random-api.ml/canvas/youtube-comment?avatar={member.display_avatar.url}&username={name}&comment={comment}') as wastedImage: # get users avatar as png with 1024 size
                imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
                
                await wastedSession.close() # closing the session and;
                
                await ctx.reply(file=discord.File(imageData, 'ytcomment.png')) # replying the file
  
  
    @commands.command() 
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def dare(self, ctx: Context, *, member:discord.Member=None):
        """
        I dared you to use this command.
        """
        dare = _dare.split("\n")
        if member is None:
            em = discord.Embed(title="Dare", description=f"{random.choice(dare)}", timestamp=datetime.datetime.utcnow())
        else:
            em = discord.Embed(title=f"{member.name} Dared", description=f"{random.choice(dare)}", timestamp=datetime.datetime.utcnow())
        
        em.set_footer(text=f'{ctx.author.name}')
        await ctx.reply(embed=em)


    @commands.command() 
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def truth(self, ctx: Context, *, member:discord.Member=None):
        """
        Truth: Who is your crush?
        """
        t = _truth.split("\n")
        if member is None:
            em = discord.Embed(title="Truth", description=f"{random.choice(t)}", timestamp=datetime.datetime.utcnow())
            em.set_footer(text=f'{ctx.author.name}')
        else:
            em = discord.Embed(title=f"{member.name} reply!", description=f"{random.choice(t)}", timestamp=datetime.datetime.utcnow())
            em.set_footer(text=f'{ctx.author.name}')
        await ctx.reply(embed=em)

    @commands.group(aliases=['https'], invoke_without_command=True) 
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def http(self, ctx: Context, *, status_code: int):
        """To understand HTTP Errors, try: `http 404`"""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                embed=discord.Embed(
                    timestamp=datetime.datetime.utcnow(), 
                    color=ctx.author.color
                ).set_image(
                    url=f"https://http.cat/{status_code}"
                ).set_footer(text=f"{ctx.author}")
            )

    @http.command(name='dog')
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def http_dog(self, ctx: Context, *, status_code: int):
        """To understand HTTP Errors, in dog format"""
        await ctx.reply(
            embed=discord.Embed(
                timestamp=datetime.datetime.utcnow(), 
                color=ctx.author.color
            ).set_image(
                url=f"https://httpstatusdogs.com/img/{status_code}.jpg"
            ).set_footer(text=f"{ctx.author}")
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def patpat(self, ctx: Context, *, member: discord.Member=None):
        """Pat pat image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def burn(self, ctx: Context, *, member: discord.Member=None):
        """Burn image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def glitch(self, ctx: Context, *, member: discord.Member=None):
        """Glitch image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def bomb(self, ctx: Context, *, member: discord.Member=None):
        """Bomb image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def explicit(self, ctx: Context, *, member: discord.Member=None):
        """Explicit image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def lamp(self, ctx: Context, *, member: discord.Member=None):
        """Lamp image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def rain(self, ctx: Context, *, member: discord.Member=None):
        """Rain image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def layers(self, ctx: Context, *, member: discord.Member=None):
        """Layers image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def radiate(self, ctx: Context, *, member: discord.Member=None):
        """Radiate image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def shoot(self, ctx: Context, *, member: discord.Member=None):
        """Shoot image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def tv(self, ctx: Context, *, member: discord.Member=None):
        """TV image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def gallery(self, ctx: Context, *, member: discord.Member=None):
        """Gallery image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def balls(self, ctx: Context, *, member: discord.Member=None):
        """Balls image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def equations(self, ctx: Context, *, member: discord.Member=None):
        """Equation image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command(aliases=['halfinvert'])
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def half_invert(self, ctx: Context, *, member: discord.Member=None):
        """Half Invert image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def roll(self, ctx: Context, *, member: discord.Member=None):
        """Roll image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def optics(self, ctx: Context, *, member: discord.Member=None):
        """Optics image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def scrapbook(self, ctx: Context, *, text: commands.clean_content):
        """ScrapBook Text image generation"""
        params = {'text': text[:20:]}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command(aliases=['earthquack'])
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def earth_quack(self, ctx: Context, *,  member: discord.Member=None):
        """Earth Quack image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def bonks(self, ctx: Context, *,  member: discord.Member=None):
        """Bonks image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def infinity(self, ctx: Context, *,  member: discord.Member=None):
        """Infinity image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')

    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @Context.with_type
    async def sob(self, ctx: Context, *,  member: discord.Member=None):
        """Sob sob sob sob image generation"""
        member = member or ctx.author
        params = {'image_url': member.display_avatar.url}
        r = await self.bot.session.get(f'https://api.jeyy.xyz/image/{ctx.command.name}', params=params)
        file_obj = discord.File(io.BytesIO(await r.read()), f'{ctx.command.qualified_name}.gif')
        await ctx.reply(file=file_obj)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
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