from __future__ import annotations

import bisect
import calendar
import collections
import hashlib
import json
import logging
import random
from datetime import datetime
from random import choice
from typing import TYPE_CHECKING, TypedDict

import arrow
import discord
from discord import Member
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.love")


class LoveMatch(TypedDict):
    titles: list[str]
    text: str


class ZodicCompatibility(TypedDict):
    Zodiac: str
    description: str
    compatibility_score: str


class ValentineDateIdea(TypedDict):
    name: str
    description: str


class ValentineDateIdeas(TypedDict):
    ideas: list[ValentineDateIdea]


class PickupLine(TypedDict):
    line: str
    image: str


class PickupLines(TypedDict):
    placeholder: str
    lines: list[PickupLine]


class Valenstate(TypedDict):
    text: str
    flag: str


class ValentineFacts(TypedDict):
    whois: str
    titles: list[str]
    text: list[str]


class ZodiacExplanation(TypedDict):
    start_at: str
    end_at: str
    About: str
    Motto: str
    Strengths: str
    Weaknesses: str
    full_form: str
    url: str


LETTER_EMOJI = "\N{LOVE LETTER}"
HEART_EMOJIS = [
    "\N{HEAVY BLACK HEART}",
    "\N{HEART WITH RIBBON}",
    "\N{REVOLVING HEARTS}",
    "\N{SPARKLING HEART}",
    "\N{TWO HEARTS}",
]


class Love(commands.Cog):
    """Love, Love, Love, what is Love? I love you?."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self._valentines_date_ideas: list[ValentineDateIdea] = []
        self._love_matches: dict[str, LoveMatch] = {}
        self._pickup_lines: PickupLines | None = None
        self._valenstates: dict[str, Valenstate] = {}
        self._valentine_facts: ValentineFacts | None = None
        self._zodiac_compatibility: dict[str, list[ZodicCompatibility]] = {}
        self._zodiac_explanation: dict[str, ZodiacExplanation] = {}

        self.love_data = sorted((int(key), value) for key, value in self.love_matches.items())
        self.zodiacs, self.zodiac_fact = self.load_comp_json()

        _log.info("Cog loaded: %s", self.__class__.__name__)

    @property
    def pickup_lines(self) -> PickupLines:
        if self._pickup_lines:
            return self._pickup_lines

        with open("assets/valentine/pickup_lines.json", encoding="utf-8") as file:
            pickup_lines = json.load(file)
            self._pickup_lines = pickup_lines
            return pickup_lines

    @property
    def valenstates(self) -> dict[str, Valenstate]:
        if self._valenstates:
            return self._valenstates

        with open("assets/valentine/valenstates", encoding="utf-8") as file:
            self._valenstates = json.load(file)
            return self._valenstates

    @property
    def valentine_facts(self) -> ValentineFacts:
        if self._valentine_facts:
            return self._valentine_facts

        with open("assets/valentine/valentine_facts", encoding="utf-8") as file:
            valentine_facts = json.load(file)
            self._valentine_facts = valentine_facts
            return valentine_facts

    @property
    def valentines_date_ideas(self) -> list[ValentineDateIdea]:
        if self._valentines_date_ideas:
            return self._valentines_date_ideas

        with open("assets/valentine/date_ideas", encoding="utf-8") as file:
            data: ValentineDateIdeas = json.load(file)
            self._valentines_date_ideas = data["ideas"]
            return self._valentines_date_ideas

    @property
    def love_matches(self) -> dict[str, LoveMatch]:
        if self._love_matches:
            return self._love_matches

        with open("assets/valentine/love_matches.json", encoding="utf-8") as file:
            self._love_matches = json.load(file)
            return self._love_matches

    @property
    def zodiac_compatibility(self) -> dict[str, list[ZodicCompatibility]]:
        if self._zodiac_compatibility:
            return self._zodiac_compatibility

        with open("assets/valentine/zodiac_compatibility.json", encoding="utf-8") as file:
            self._zodiac_compatibility = json.load(file)
            return self._zodiac_compatibility

    @property
    def zodiac_explanation(self) -> dict[str, ZodiacExplanation]:
        if self._zodiac_explanation:
            return self._zodiac_explanation

        with open("assets/valentine/zodiac_explanation.json", encoding="utf-8") as file:
            self._zodiac_explanation = json.load(file)
            return self._zodiac_explanation

    def levenshtein(self, source: str, goal: str) -> int:
        """Calculates the Levenshtein Distance between source and goal."""
        if len(source) < len(goal):
            return self.levenshtein(goal, source)
        if not source:
            return len(goal)
        if not goal:
            return len(source)

        pre_row = list(range(len(source) + 1))
        for i, source_c in enumerate(source):
            cur_row = [i + 1]
            for j, goal_c in enumerate(goal):
                if source_c != goal_c:
                    cur_row.append(min(pre_row[j], pre_row[j + 1], cur_row[j]) + 1)
                else:
                    cur_row.append(min(pre_row[j], pre_row[j + 1], cur_row[j]))
            pre_row = cur_row
        return pre_row[-1]

    def load_comp_json(self):
        """Load zodiac compatibility from static JSON resource."""
        return self.zodiac_compatibility, self.zodiac_explanation

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
        embed = discord.Embed(color=discord.Color.dark_magenta())
        if zodiac in self.zodiac_fact:
            self._extracted_from_zodiac_build_embed_6(zodiac, embed)
        else:
            embed = self.generate_invalidname_embed(zodiac)
        return embed

    # TODO Rename this here and in `zodiac_build_embed`
    def _extracted_from_zodiac_build_embed_6(self, zodiac: str, embed: discord.Embed):
        embed.title = f"__{zodiac}__"
        embed.description = self.zodiac_fact[zodiac]["About"]
        embed.add_field(name="__Motto__", value=self.zodiac_fact[zodiac]["Motto"], inline=False).add_field(
            name="__Strengths__",
            value=self.zodiac_fact[zodiac]["Strengths"],
            inline=False,
        ).add_field(name="__Weaknesses__", value=self.zodiac_fact[zodiac]["Weaknesses"], inline=False).add_field(
            name="__Full form__",
            value=self.zodiac_fact[zodiac]["full_form"],
            inline=False,
        ).set_thumbnail(url=self.zodiac_fact[zodiac]["url"])

    def zodiac_date_verifier(self, query_date: datetime) -> str:
        """Returns zodiac sign by checking date."""
        for zodiac_name, zodiac_data in self.zodiac_fact.items():
            start_at = arrow.get(zodiac_data["start_at"])
            end_at = arrow.get(zodiac_data["end_at"])

            if start_at <= arrow.get(query_date) <= end_at:
                return zodiac_name

        return ""

    @commands.command(aliases=["saintvalentine"])
    async def whoisvalentine(self, ctx: commands.Context[Parrot]):
        """Displays info about Saint Valentine."""
        embed = discord.Embed(title="Who is Saint Valentine?", description=self.valentine_facts["whois"], color=ctx.author.color)
        embed.set_thumbnail(
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Saint_Valentine_-_facial_reconstruction.jpg/1024px-Saint_Valentine_-_facial_reconstruction.jpg",
        )

        await ctx.reply(embed=embed)

    @commands.command(aliases=["valentine-fact"])
    async def valentinefact(self, ctx: commands.Context[Parrot]) -> None:
        """Shows a random fact about Valentine's Day."""
        embed = discord.Embed(
            title=choice(self.valentine_facts["titles"]),
            description=choice(self.valentine_facts["text"]),
            color=ctx.author.color,
        )

        await ctx.reply(embed=embed)

    @commands.group(name="zodiac", invoke_without_command=True)
    async def zodiac(self, ctx: commands.Context[Parrot], zodiac_sign: str) -> None:
        """Provides information about zodiac sign by taking zodiac sign name as input."""
        final_embed = self.zodiac_build_embed(zodiac_sign)
        await ctx.reply(embed=final_embed)

    @zodiac.command(name="date")
    async def date_and_month(self, ctx: commands.Context[Parrot], date: int, month: int | str) -> None:
        """Provides information about zodiac sign by taking month and date as input."""
        if isinstance(month, str):
            month = month.capitalize()
            try:
                month = list(calendar.month_abbr).index(month[:3])
            except ValueError:
                await ctx.reply(f"Sorry, but `{month}` is not a valid month name.")
                return
        if (month == 1 and 1 <= date <= 19) or (month == 12 and 22 <= date <= 31):
            zodiac = "capricorn"
            final_embed = self.zodiac_build_embed(zodiac)
        else:
            try:
                zodiac_sign_based_on_date = self.zodiac_date_verifier(datetime(2020, month, date))

            except ValueError as e:
                final_embed = discord.Embed(color=discord.Color.dark_magenta())
                final_embed.description = f"Zodiac sign could not be found because.\n```\n{e}\n```"

            else:
                final_embed = self.zodiac_build_embed(zodiac_sign_based_on_date)

        await ctx.reply(embed=final_embed)

    @zodiac.command(name="partnerzodiac", aliases=("partner",))
    async def partner_zodiac(self, ctx: commands.Context[Parrot], zodiac_sign: str) -> None:
        """Provides a random counter compatible zodiac sign to the given user's zodiac sign."""
        embed = discord.Embed(color=discord.Color.dark_magenta())
        if _ := self.zodiacs.get(zodiac_sign.capitalize()):
            compatible_zodiac = random.choice(self.zodiacs[zodiac_sign.capitalize()])
            emoji1 = random.choice(HEART_EMOJIS)
            emoji2 = random.choice(HEART_EMOJIS)
            embed.title = "Zodiac Compatibility"
            embed.description = f"{zodiac_sign.capitalize()}{emoji1}{compatible_zodiac['Zodiac']}\n{emoji2}Compatibility meter : {compatible_zodiac['compatibility_score']}{emoji2}"
            embed.add_field(name=f"A letter from Dr.Zodiac {LETTER_EMOJI}", value=compatible_zodiac["description"])
        else:
            embed = self.generate_invalidname_embed(zodiac_sign)
        await ctx.reply(embed=embed)

    @commands.command()
    async def savethedate(self, ctx: commands.Context[Parrot]) -> None:
        """Gives you ideas for what to do on a date with your valentine."""
        random_date = random.choice(self.valentines_date_ideas)
        emoji_1 = random.choice(HEART_EMOJIS)
        emoji_2 = random.choice(HEART_EMOJIS)
        embed = discord.Embed(
            title=f"{emoji_1}{random_date['name']}{emoji_2}",
            description=f"{random_date['description']}",
            colour=discord.Color.dark_purple(),
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def pickupline(self, ctx: commands.Context[Parrot]) -> None:
        """Gives you a random pickup line.
        Note that most of them are very cheesy.
        """
        random_line = random.choice(self.pickup_lines["lines"])
        embed = discord.Embed(title=":cheese: Your pickup line :cheese:", description=random_line["line"], color=ctx.author.color)
        embed.set_thumbnail(url=random_line.get("image", self.pickup_lines["placeholder"]))
        await ctx.reply(embed=embed)

    @commands.command()
    async def myvalenstate(self, ctx: commands.Context[Parrot], *, name: str | None = None) -> None:
        """Find the vacation spot(s) with the most matching characters to the invoking user."""
        eq_chars = collections.defaultdict(int)
        if name is None:
            author = ctx.author.name.lower().replace(" ", "")
        else:
            author = name.lower().replace(" ", "")

        for state in self.valenstates.keys():
            lower_state = state.lower().replace(" ", "")
            eq_chars[state] = self.levenshtein(author, lower_state)

        matches = [x for x, y in eq_chars.items() if y == min(eq_chars.values())]
        valenstate = choice(matches)
        matches.remove(valenstate)

        embed_title = "But there are more!"
        if len(matches) > 1:
            leftovers = f"{', '.join(matches[:-2])}, and {matches[-1]}"
            embed_text = f"You have {len(matches)} more matches, these being {leftovers}."
        elif len(matches) == 1:
            embed_title = "But there's another one!"
            embed_text = f"You have another match, this being {matches[0]}."
        else:
            embed_title = "You have a true match!"
            embed_text = "This state is your true Valenstate! There are no states that would suit you better"

        embed = discord.Embed(
            title=f"Your Valenstate is {valenstate} \N{HEAVY BLACK HEART}",
            description=self.valenstates[valenstate]["text"],
            colour=ctx.author.color,
        )
        embed.add_field(name=embed_title, value=embed_text)
        embed.set_image(url=self.valenstates[valenstate]["flag"])
        await ctx.reply(embed=embed)

    @commands.command(aliases=("love_calculator", "love_calc"))
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def love(self, ctx: commands.Context[Parrot], who: Member, whom: Member) -> None:
        """Tells you how much the two love each other.
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

        who_user = discord.utils.escape_markdown(who.display_name)
        whom_user = discord.utils.escape_markdown(whom.display_name)

        who_user, whom_user = sorted([who_user, whom_user])

        # Hash inputs to guarantee consistent results (hashing algorithm choice arbitrary)
        #
        # hashlib is used over the builtin hash() to guarantee same result over multiple runtimes
        m = hashlib.sha256(who_user.encode() + whom_user.encode())
        # Mod 101 for [0, 100]
        love_percent = sum(m.digest()) % 101

        # We need the -1 due to how bisect returns the point
        # see the documentation for further detail
        # https://docs.python.org/3/library/bisect.html#bisect.bisect
        love_threshold = [threshold for threshold, _ in self.love_data]
        index = bisect.bisect(love_threshold, love_percent) - 1
        # We already have the nearest "fit" love level
        # We only need the dict, so we can ditch the first element
        _, data = self.love_data[index]

        status = random.choice(data["titles"])
        embed = discord.Embed(
            title=status,
            description=f"{who} \N{HEAVY BLACK HEART} {whom} scored {love_percent}%!\n\N{ZERO WIDTH SPACE}",
            color=discord.Color.dark_magenta(),
        )
        embed.add_field(name="A letter from Dr. Love:", value=data["text"])

        await ctx.reply(embed=embed)


async def setup(bot: Parrot) -> None:
    """Loads the Love cog."""
    await bot.add_cog(Love(bot))
