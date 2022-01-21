from __future__ import annotations

from core import Parrot, Cog, Context

import json
import random
import calendar
import collections
import bisect
import hashlib

from pathlib import Path
from random import choice
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import clean_content
from discord import Member

from typing import Union, Coroutine, Optional, Callable

FACTS = json.loads(Path(r"extra/valentines/valentine_facts.json").read_text("utf8"))

LETTER_EMOJI = ":love_letter:"
HEART_EMOJIS = [
    ":heart:",
    ":gift_heart:",
    ":revolving_hearts:",
    ":sparkling_heart:",
    ":two_hearts:",
]
VALENTINES_DATES = json.loads(
    Path("extra/valentines/date_ideas.json").read_text("utf8")
)
PICKUP_LINES = json.loads(Path("extra/valentines/pickup_lines.json").read_text("utf8"))
STATES = json.loads(Path("extra/valentines/valenstates.json").read_text("utf8"))
LOVE_DATA = json.loads(Path("extra/valentines/love_matches.json").read_text("utf8"))
LOVE_DATA = sorted((int(key), value) for key, value in LOVE_DATA.items())


class Love(Cog):
    """Love, Love, Love, what is Love? I love you?"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.zodiacs, self.zodiac_fact = self.load_comp_json()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{HEAVY BLACK HEART}")

    def levenshtein(self, source: str, goal: str) -> int:
        """Calculates the Levenshtein Distance between source and goal."""
        if len(source) < len(goal):
            return self.levenshtein(goal, source)
        if len(source) == 0:
            return len(goal)
        if len(goal) == 0:
            return len(source)

        pre_row = list(range(0, len(source) + 1))
        for i, source_c in enumerate(source):
            cur_row = [i + 1]
            for j, goal_c in enumerate(goal):
                if source_c != goal_c:
                    cur_row.append(min(pre_row[j], pre_row[j + 1], cur_row[j]) + 1)
                else:
                    cur_row.append(min(pre_row[j], pre_row[j + 1], cur_row[j]))
            pre_row = cur_row
        return pre_row[-1]

    @staticmethod
    def load_comp_json() -> tuple[dict, dict]:
        """Load zodiac compatibility from static JSON resource."""
        explanation_file = Path("extra/valentines/zodiac_explanation.json")
        compatibility_file = Path("extra/valentines/zodiac_compatibility.json")

        zodiac_fact = json.loads(explanation_file.read_text("utf8"))

        for zodiac_data in zodiac_fact.values():
            zodiac_data["start_at"] = datetime.fromisoformat(zodiac_data["start_at"])
            zodiac_data["end_at"] = datetime.fromisoformat(zodiac_data["end_at"])

        zodiacs = json.loads(compatibility_file.read_text("utf8"))

        return zodiacs, zodiac_fact

    def generate_invalidname_embed(self, zodiac: str) -> discord.Embed:
        """Returns error embed."""
        embed = discord.Embed()
        error_msg = f"**{zodiac}** is not a valid zodiac sign, here is the list of valid zodiac signs.\n"
        names = list(self.zodiac_fact)
        middle_index = len(names) // 2
        first_half_names = ", ".join(names[:middle_index])
        second_half_names = ", ".join(names[middle_index:])
        embed.description = error_msg + first_half_names + ",\n" + second_half_names
        return embed

    def zodiac_build_embed(self, zodiac: str) -> discord.Embed:
        """Gives informative zodiac embed."""
        zodiac = zodiac.capitalize()
        embed = discord.Embed()
        embed.color = discord.Color.dark_purple()
        if zodiac in self.zodiac_fact:
            embed.title = f"__{zodiac}__"
            embed.description = self.zodiac_fact[zodiac]["About"]
            embed.add_field(
                name="__Motto__", value=self.zodiac_fact[zodiac]["Motto"], inline=False
            )
            embed.add_field(
                name="__Strengths__",
                value=self.zodiac_fact[zodiac]["Strengths"],
                inline=False,
            )
            embed.add_field(
                name="__Weaknesses__",
                value=self.zodiac_fact[zodiac]["Weaknesses"],
                inline=False,
            )
            embed.add_field(
                name="__Full form__",
                value=self.zodiac_fact[zodiac]["full_form"],
                inline=False,
            )
            embed.set_thumbnail(url=self.zodiac_fact[zodiac]["url"])
        else:
            embed = self.generate_invalidname_embed(zodiac)
        return embed

    def zodiac_date_verifier(self, query_date: datetime) -> str:
        """Returns zodiac sign by checking date."""
        for zodiac_name, zodiac_data in self.zodiac_fact.items():
            if (
                zodiac_data["start_at"].date()
                <= query_date.date()
                <= zodiac_data["end_at"].date()
            ):
                return zodiac_name

    @commands.command(aliases=["saintvalentine"])
    async def whoisvalentine(
        self,
        ctx: Context,
    ):
        """Displays info about Saint Valentine."""
        embed = discord.Embed(
            title="Who is Saint Valentine?",
            description=FACTS["whois"],
            color=ctx.author.color,
        )
        embed.set_thumbnail(
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Saint_Valentine_-_facial_reconstruction.jpg/1024px-Saint_Valentine_-_facial_reconstruction.jpg"
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["valentine-fact"])
    async def valentinefact(self, ctx: Context) -> None:
        """Shows a random fact about Valentine's Day."""
        embed = discord.Embed(
            title=choice(FACTS["titles"]),
            description=choice(FACTS["text"]),
            color=ctx.author.color,
        )

        await ctx.send(embed=embed)

    @commands.group(name="zodiac", invoke_without_command=True)
    async def zodiac(self, ctx: Context, zodiac_sign: str) -> None:
        """Provides information about zodiac sign by taking zodiac sign name as input."""
        final_embed = self.zodiac_build_embed(zodiac_sign)
        await ctx.send(embed=final_embed)

    @zodiac.command(name="date")
    async def date_and_month(
        self, ctx: Context, date: int, month: Union[int, str]
    ) -> None:
        """Provides information about zodiac sign by taking month and date as input."""
        if isinstance(month, str):
            month = month.capitalize()
            try:
                month = list(calendar.month_abbr).index(month[:3])
            except ValueError:
                await ctx.send(f"Sorry, but `{month}` is not a valid month name.")
                return
        if (month == 1 and 1 <= date <= 19) or (month == 12 and 22 <= date <= 31):
            zodiac = "capricorn"
            final_embed = self.zodiac_build_embed(zodiac)
        else:
            try:
                zodiac_sign_based_on_date = self.zodiac_date_verifier(
                    datetime(2020, month, date)
                )

            except ValueError as e:
                final_embed = discord.Embed()
                final_embed.color = discord.Color.dark_purple()
                final_embed.description = (
                    f"Zodiac sign could not be found because.\n```\n{e}\n```"
                )

            else:
                final_embed = self.zodiac_build_embed(zodiac_sign_based_on_date)

        await ctx.send(embed=final_embed)

    @zodiac.command(name="partnerzodiac", aliases=("partner",))
    async def partner_zodiac(self, ctx: Context, zodiac_sign: str) -> None:
        """Provides a random counter compatible zodiac sign to the given user's zodiac sign."""
        embed = discord.Embed()
        embed.color = discord.Color.dark_purple()
        zodiac_check = self.zodiacs.get(zodiac_sign.capitalize())
        if zodiac_check:
            compatible_zodiac = random.choice(self.zodiacs[zodiac_sign.capitalize()])
            emoji1 = random.choice(HEART_EMOJIS)
            emoji2 = random.choice(HEART_EMOJIS)
            embed.title = "Zodiac Compatibility"
            embed.description = (
                f"{zodiac_sign.capitalize()}{emoji1}{compatible_zodiac['Zodiac']}\n"
                f"{emoji2}Compatibility meter : {compatible_zodiac['compatibility_score']}{emoji2}"
            )
            embed.add_field(
                name=f"A letter from Dr.Zodiac {LETTER_EMOJI}",
                value=compatible_zodiac["description"],
            )
        else:
            embed = self.generate_invalidname_embed(zodiac_sign)
        await ctx.send(embed=embed)

    @commands.command()
    async def savethedate(self, ctx: Context) -> None:
        """Gives you ideas for what to do on a date with your valentine."""
        random_date = random.choice(VALENTINES_DATES["ideas"])
        emoji_1 = random.choice(HEART_EMOJIS)
        emoji_2 = random.choice(HEART_EMOJIS)
        embed = discord.Embed(
            title=f"{emoji_1}{random_date['name']}{emoji_2}",
            description=f"{random_date['description']}",
            colour=discord.Color.dark_purple(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def pickupline(self, ctx: Context) -> None:
        """
        Gives you a random pickup line.
        Note that most of them are very cheesy.
        """
        random_line = random.choice(PICKUP_LINES["lines"])
        embed = discord.Embed(
            title=":cheese: Your pickup line :cheese:",
            description=random_line["line"],
            color=ctx.author.color,
        )
        embed.set_thumbnail(url=random_line.get("image", PICKUP_LINES["placeholder"]))
        await ctx.send(embed=embed)

    @commands.command()
    async def myvalenstate(self, ctx: Context, *, name: str = None) -> None:
        """Find the vacation spot(s) with the most matching characters to the invoking user."""
        eq_chars = collections.defaultdict(int)
        if name is None:
            author = ctx.author.name.lower().replace(" ", "")
        else:
            author = name.lower().replace(" ", "")

        for state in STATES.keys():
            lower_state = state.lower().replace(" ", "")
            eq_chars[state] = self.levenshtein(author, lower_state)

        matches = [x for x, y in eq_chars.items() if y == min(eq_chars.values())]
        valenstate = choice(matches)
        matches.remove(valenstate)

        embed_title = "But there are more!"
        if len(matches) > 1:
            leftovers = f"{', '.join(matches[:-2])}, and {matches[-1]}"
            embed_text = (
                f"You have {len(matches)} more matches, these being {leftovers}."
            )
        elif len(matches) == 1:
            embed_title = "But there's another one!"
            embed_text = f"You have another match, this being {matches[0]}."
        else:
            embed_title = "You have a true match!"
            embed_text = (
                "This state is your true Valenstate! There are no states that would suit"
                " you better"
            )

        embed = discord.Embed(
            title=f"Your Valenstate is {valenstate} \u2764",
            description=STATES[valenstate]["text"],
            colour=ctx.author.color,
        )
        embed.add_field(name=embed_title, value=embed_text)
        embed.set_image(url=STATES[valenstate]["flag"])
        await ctx.send(embed=embed)

    """A cog for calculating the love between two people."""

    # @in_month(Month.FEBRUARY)
    @commands.command(aliases=("love_calculator", "love_calc"))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def love(
        self, ctx: Context, who: Member, whom: Optional[Member] = None
    ) -> None:
        """
        Tells you how much the two love each other.
        This command requires at least one member as input, if two are given love will be calculated between
        those two users, if only one is given, the second member is asusmed to be the invoker.
        Members are converted from:
          - User ID
          - Mention
          - name#discrim
          - name
          - nickname
        Any two arguments will always yield the same result, regardless of the order of arguments:
          Running $love @joe#6000 @chrisjl#2655 will always yield the same result.
          Running $love @chrisjl#2655 @joe#6000 will yield the same result as before.
        """
        if whom is None:
            whom = ctx.author

        def normalize(arg: Member) -> Coroutine:
            # This has to be done manually to be applied to usernames
            return clean_content(escape_markdown=True).convert(ctx, str(arg))

        # Sort to ensure same result for same input, regardless of order
        who, whom = sorted([await normalize(arg) for arg in (who, whom)])

        # Hash inputs to guarantee consistent results (hashing algorithm choice arbitrary)
        #
        # hashlib is used over the builtin hash() to guarantee same result over multiple runtimes
        m = hashlib.sha256(who.encode() + whom.encode())
        # Mod 101 for [0, 100]
        love_percent = sum(m.digest()) % 101

        # We need the -1 due to how bisect returns the point
        # see the documentation for further detail
        # https://docs.python.org/3/library/bisect.html#bisect.bisect
        love_threshold = [threshold for threshold, _ in LOVE_DATA]
        index = bisect.bisect(love_threshold, love_percent) - 1
        # We already have the nearest "fit" love level
        # We only need the dict, so we can ditch the first element
        _, data = LOVE_DATA[index]

        status = random.choice(data["titles"])
        embed = discord.Embed(
            title=status,
            description=f"{who} \N{HEAVY BLACK HEART} {whom} scored {love_percent}%!\n\u200b",
            color=discord.Color.dark_magenta(),
        )
        embed.add_field(name="A letter from Dr. Love:", value=data["text"])

        await ctx.send(embed=embed)
