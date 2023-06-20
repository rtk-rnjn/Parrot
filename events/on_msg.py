# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
import random
import re
import textwrap
import urllib.parse
from contextlib import suppress
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Pattern,
    Tuple,
    Union,
)
from urllib.parse import quote_plus

import aiohttp  # type: ignore
from aiohttp import ClientResponseError  # type: ignore
from pymongo import ReturnDocument, UpdateOne

import discord
import emojis
from cogs.fun.fun import replace_many
from discord.ext import commands
from utilities.rankcard import rank_card
from utilities.regex import EQUATION_REGEX, LINKS_NO_PROTOCOLS

if TYPE_CHECKING:
    from discord.ext.commands.cooldowns import CooldownMapping
    from pymongo.collection import Collection
    from pymongo.typings import _DocumentType
    from typing_extensions import TypeAlias

    from core import Parrot

    DocumentType: TypeAlias = _DocumentType

    from cogs.utils import Utils

from core import Cog

with open("extra/profanity.json", encoding="utf-8", errors="ignore") as f:
    bad_dict: Dict[str, bool] = json.load(f)

TRIGGER: Tuple = (
    "ok google,",
    "ok google ",
    "hey google,",
    "hey google ",
)

GITHUB_RE = re.compile(
    r"https://github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/blob/"
    r"(?P<path>[^#>]+)(\?[^#>]+)?(#L(?P<start_line>\d+)(([-~:]|(\.\.))L(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

GITHUB_GIST_RE = re.compile(
    r"https://gist\.github\.com/([a-zA-Z0-9-]+)/(?P<gist_id>[a-zA-Z0-9]+)/*"
    r"(?P<revision>[a-zA-Z0-9]*)/*#file-(?P<file_path>[^#>]+?)(\?[^#>]+)?"
    r"(-L(?P<start_line>\d+)([-~:]L(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

GITLAB_RE = re.compile(
    r"https://gitlab\.com/(?P<repo>[\w.-]+/[\w.-]+)/\-/blob/(?P<path>[^#>]+)"
    r"(\?[^#>]+)?(#L(?P<start_line>\d+)(-(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

BITBUCKET_RE = re.compile(
    r"https://bitbucket\.org/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/src/(?P<ref>[0-9a-zA-Z]+)"
    r"/(?P<file_path>[^#>]+)(\?[^#>]+)?(#lines-(?P<start_line>\d+)(:(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

QUESTION_REGEX = re.compile(
    r"(((what)\s(is)\s)(\w+)[\?|\.|\/|\,]?)|(((\w+)\s(means))[\?|\.|\/|\,]?)|(((what)\s(\w+)(is|means))[\?|\.|\/|\,]?)",
    re.IGNORECASE,
)

GITHUB_HEADERS = {"Accept": "application/vnd.github.v3.raw"}

DISCORD_PY_ID = 336642139381301249


class Delete(discord.ui.View):
    message: Optional[discord.Message]

    def __init__(self, user: Union[discord.Member, discord.User]):
        super().__init__(timeout=30.0)
        self.user = user
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True if self.user.bot else self.user.id == interaction.user.id

    @discord.ui.button(
        label="Delete", style=discord.ButtonStyle.red, emoji="\N{WASTEBASKET}"
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.message is not None

        await interaction.message.delete()
        self.stop()

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                child.style = discord.ButtonStyle.grey
        if self.message:
            await self.message.edit(view=self)
        self.stop()


class OnMsg(Cog, command_attrs=dict(hidden=True)):  # type: ignore
    def __init__(self, bot: Parrot):
        self.bot: Parrot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.channel
        )
        self.pattern_handlers: List[Tuple[Pattern[str], Callable]] = [
            (GITHUB_RE, self._fetch_github_snippet),
            (GITHUB_GIST_RE, self._fetch_github_gist_snippet),
            (GITLAB_RE, self._fetch_gitlab_snippet),
            (BITBUCKET_RE, self._fetch_bitbucket_snippet),
        ]
        self.message_append: List[discord.Message] = []
        self.message_cooldown: CooldownMapping = commands.CooldownMapping.from_cooldown(
            1,
            60,
            commands.BucketType.member,
        )

        self.write_data: List[UpdateOne] = []

        self.lock = asyncio.Lock()

        self.__scam_link_cache: Dict[str, bool] = {}

    async def _fetch_response(
        self, url: str, response_format: str, **kwargs: Any
    ) -> Union[str, Dict[str, Any], None]:
        """Makes http requests using aiohttp."""
        async with self.bot.http_session.get(
            url, raise_for_status=True, **kwargs
        ) as response:
            if response_format == "text":
                return await response.text()
            if response_format == "json":
                return await response.json()
        return None

    def _find_ref(self, path: str, refs: Tuple) -> Tuple:
        """Loops through all branches and tags to find the required ref."""
        # Base case: there is no slash in the branch name
        ref, file_path = path.split("/", 1)
        # In case there are slashes in the branch name, we loop through all branches and tags
        for possible_ref in refs:
            if path.startswith(possible_ref["name"] + "/"):
                ref = possible_ref["name"]
                file_path = path[len(ref) + 1 :]
                break
        return ref, file_path

    async def _fetch_github_snippet(
        self, repo: str, path: str, start_line: Optional[Union[str, int]], end_line: Optional[Union[str, int]]
    ) -> str:
        """Fetches a snippet from a GitHub repo."""
        # Search the GitHub API for the specified branch
        branches = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/branches",
            "json",
            headers=GITHUB_HEADERS,
        )
        tags = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/tags", "json", headers=GITHUB_HEADERS
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)

        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}",
            "text",
            headers=GITHUB_HEADERS,
        )
        return self._snippet_to_codeblock(
            file_contents, file_path, start_line, end_line
        )

    async def _fetch_github_gist_snippet(
        self,
        gist_id: str,
        revision: str,
        file_path: str,
        start_line: Optional[Union[str, int]],
        end_line: Optional[Union[str, int]],
    ) -> str:
        """Fetches a snippet from a GitHub gist."""
        gist_json = await self._fetch_response(
            f'https://api.github.com/gists/{gist_id}{f"/{revision}" if revision != "" else ""}',
            "json",
            headers=GITHUB_HEADERS,
        )

        if gist_json is None:
            return ""

        # Check each file in the gist for the specified file
        for gist_file in gist_json["files"]:
            if file_path == gist_file.lower().replace(".", "-"):
                file_contents = await self._fetch_response(
                    gist_json["files"][gist_file]["raw_url"],
                    "text",
                )
                return self._snippet_to_codeblock(
                    file_contents, gist_file, start_line, end_line
                )
        return ""

    async def _fetch_gitlab_snippet(
        self, repo: str, path: str, start_line: Optional[Union[str, int]], end_line: Optional[Union[str, int]]
    ) -> str:
        """Fetches a snippet from a GitLab repo."""
        enc_repo = quote_plus(repo)

        # Searches the GitLab API for the specified branch
        branches = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/branches", "json"
        )
        tags = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/tags", "json"
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)
        enc_ref = quote_plus(ref)
        enc_file_path = quote_plus(file_path)

        file_contents = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/files/{enc_file_path}/raw?ref={enc_ref}",
            "text",
        )
        return self._snippet_to_codeblock(
            file_contents, file_path, start_line, end_line
        )

    async def _fetch_bitbucket_snippet(
        self, repo: str, ref: str, file_path: str, start_line: str, end_line: str
    ) -> str:
        """Fetches a snippet from a BitBucket repo."""
        file_contents = await self._fetch_response(
            f"https://bitbucket.org/{quote_plus(repo)}/raw/{quote_plus(ref)}/{quote_plus(file_path)}",
            "text",
        )
        return self._snippet_to_codeblock(
            file_contents, file_path, start_line, end_line
        )

    def _snippet_to_codeblock(
        self, file_contents: Optional[Any], file_path: str, start_line: Optional[Union[str, int]], end_line: Optional[Union[str, int]]
    ) -> str:
        """
        Given the entire file contents and target lines, creates a code block.
        First, we split the file contents into a list of lines and then keep and join only the required
        ones together.
        We then dedent the lines to look nice, and replace all ` characters with `\u200b to prevent
        markdown injection.
        Finally, we surround the code with ``` characters.
        """
        # Parse start_line and end_line into integers
        if end_line is None:
            start_line = end_line = int(start_line)
        else:
            start_line = int(start_line)
            end_line = int(end_line)

        split_file_contents = file_contents.splitlines() if file_contents else []

        # Make sure that the specified lines are in range
        if start_line > end_line:
            start_line, end_line = end_line, start_line
        if start_line > len(split_file_contents) or end_line < 1:
            return ""
        start_line = max(1, start_line)
        end_line = min(len(split_file_contents), end_line)

        # Gets the code lines, dedents them, and inserts zero-width spaces to prevent Markdown injection
        required = "\n".join(split_file_contents[start_line - 1 : end_line])
        required = textwrap.dedent(required).rstrip().replace("`", "`\u200b")

        # Extracts the code language and checks whether it's a "valid" language
        language = file_path.split("/")[-1].split(".")[-1]
        trimmed_language = language.replace("-", "").replace("+", "").replace("_", "")
        is_valid_language = trimmed_language.isalnum()
        if not is_valid_language:
            language = ""

        # Adds a label showing the file path to the snippet
        if start_line == end_line:
            ret = f"`{file_path}` line {start_line}\n"
        else:
            ret = f"`{file_path}` lines {start_line} to {end_line}\n"

        if len(required) != 0:
            return f"{ret}```{language}\n{required}```"
        # Returns an empty codeblock if the snippet is empty
        return f"{ret}``` ```"

    async def _parse_snippets(self, content: str) -> str:
        """Parse message content and return a string with a code block for each URL found."""
        all_snippets = []

        for pattern, handler in self.pattern_handlers:
            for match in pattern.finditer(content):
                try:
                    snippet = await handler(**match.groupdict())
                    all_snippets.append((match.start(), snippet))
                except ClientResponseError as error:
                    error_message = error.message
                    print(error_message)

        # Sorts the list of snippets by their match index and joins them into a single message
        return "\n".join(map(lambda x: x[1], sorted(all_snippets)))

    def _check_gitlink_req(self, message: discord.Message):
        assert message.guild is not None

        return self.bot.guild_configurations_cache[message.guild.id]["opts"][
            "gitlink_enabled"
        ]

    def _check_equation_req(self, message: discord.Message):
        assert message.guild is not None

        return self.bot.guild_configurations_cache[message.guild.id]["opts"][
            "equation_enabled"
        ]

    async def query_ddg(self, query: str) -> Optional[str]:
        link = f"https://api.duckduckgo.com/?q={query}&format=json&pretty=1"
        # saying `ok google`, and querying from ddg LOL.
        res = await self.bot.http_session.get(link)
        data: Dict = json.loads(await res.text())
        if data.get("Abstract"):
            return data.get("Abstract")
        return data["RelatedTopics"][0]["Text"] if data["RelatedTopics"] else None

    async def quick_answer(self, message: discord.Message):
        """This is good."""
        if not message.content.lower().startswith(TRIGGER):
            return
        if message.content.lower().startswith("ok google"):
            query = message.content.lower()[10:]
            res = await self.query_ddg(query)
            if not res:
                return
            with suppress(discord.Forbidden):
                return await message.channel.send(res)
        if message.content.lower().startswith("hey google"):
            query = message.content.lower()[11:]
            res = await self.query_ddg(query)
            if not res:
                return
            with suppress(discord.Forbidden):
                return await message.channel.send(res)

    def refrain_message(self, msg: str):
        if "chod" in msg.replace(",", "").split(" "):
            return False
        return all(
            bad_word.lower() not in msg.replace(",", "").split(" ")
            for bad_word in bad_dict
        )

    def is_banned(self, member: Union[discord.User, discord.Member]) -> bool:
        # return True if member is banned else False
        if not hasattr(member, "guild"):
            return

        try:
            return self.bot.banned_users[member.id].get("global", False)  # type: ignore
        except (AttributeError, KeyError):
            pass

        return False

    def get_emoji_count(self, message_content: str) -> int:
        str_count = emojis.count(message_content)
        dis_count = len(
            re.findall(
                r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>",
                message_content,
            )
        )
        return int(str_count + dis_count)

    async def equation_solver(self, message: discord.Message):
        OP = [
            "+",
            "-",
            "*",
            "/",
            "sin",
            "cos",
            "tan",
            "cot",
            "sec",
            "csc",
            "log",
            "ln",
            "sqrt",
            "^",
        ]
        message.content = message.content.replace(
            "\N{MULTIPLICATION SIGN}", "*"
        ).replace("\N{DIVISION SIGN}", "/")

        if message.author.bot:
            return
        if len(message.content) < 3:
            return

        if all(i not in message.content for i in OP):
            return

        if not self._check_equation_req(message):
            return

        def check(r: discord.Reaction, u: discord.User) -> bool:
            return r.message.id == message.id and u.id == message.author.id

        if re.fullmatch(EQUATION_REGEX, message.content):
            with suppress(discord.Forbidden, discord.NotFound):
                await message.add_reaction("\N{SPIRAL NOTE PAD}")
                try:
                    r, _ = await self.bot.wait_for(
                        "reaction_add", check=check, timeout=30
                    )
                except asyncio.TimeoutError:
                    return
                if r.emoji == "\N{SPIRAL NOTE PAD}":
                    url = f"http://twitch.center/customapi/math?expr={urllib.parse.quote(message.content)}"
                    try:
                        res = await self.bot.http_session.get(url)
                    except aiohttp.ClientOSError:
                        await asyncio.sleep(60)
                        return

                    if res.status == 200:
                        text = await res.text()
                    else:
                        return
                    if text != "???":
                        return await message.reply(text)

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()

        if message.guild is None:
            return

        if message.guild.me.id == message.author.id:
            return

        async def __internal_snippets_parser():
            message_to_send = await self._parse_snippets(message.content)
            if 0 < len(message_to_send) <= 2000 and self._check_gitlink_req(message):
                view = Delete(message.author)
                view.message = await message.channel.send(message_to_send, view=view)
                try:
                    await message.edit(suppress=True)
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
            if message.author.bot:
                return

        AWAITABLES: List[Coroutine] = [
            __internal_snippets_parser(),
            self._scam_detection(message),
            self._on_message_leveling(message),
            self.equation_solver(message),
            self.quick_answer(message),
            self._on_message_passive(message),
            self._global_chat_handler(message),
        ]
        await asyncio.gather(*AWAITABLES, return_exceptions=False)

    async def _global_chat_handler(self, message: discord.Message) -> None:
        # sourcery skip: low-code-quality

        if not message.content:
            return

        if not hasattr(message.author, "guild"):
            return
        # this is equivalent to `if not message.guild: ...`
        # for some reason, message.author.guild is None from that check

        if self.is_banned(message.author):
            return

        data: Optional[DocumentType] = await self.bot.guild_configurations.find_one(
            {
                "_id": message.guild.id,
                "global_chat.channel_id": message.channel.id,
                "global_chat.enable": True,
            }
        )
        if data is None:
            return

        data = data["global_chat"]

        bucket = self.cd_mapping.get_bucket(message)
        if retry_after := bucket.update_rate_limit():
            await message.channel.send(
                (
                    f"{message.author.mention} Chill out | You reached the limit | \n"
                    f"Continous spam may leads to ban from global-chat | **Send message after {round(retry_after, 3)}s**"
                ),
                delete_after=10,
            )
            return

        guild = data
        role_id = guild.get("ignore_role") or 0

        if message.author._roles.has(role_id):
            return

        if message.content.startswith(
            ("$", "!", "%", "^", "&", "*", "-", ">", "/", "\\")
        ):
            return

        if LINKS_NO_PROTOCOLS.search(message.content):
            await message.delete(delay=0)
            await message.channel.send(
                f"{message.author.mention} | URLs aren't allowed.", delete_after=5
            )
            return

        if len(message.content.split("\n")) > 4:
            await message.delete(delay=0)
            await message.channel.send(
                f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                delete_after=5,
            )
            return

        to_send: bool = self.refrain_message(message.content.lower())
        if not to_send:
            await message.delete(delay=0)
            await message.channel.send(
                f"{message.author.mention} | Sending Bad Word not allowed",
                delete_after=5,
            )
            return

        if self.get_emoji_count(message.content) > 10:
            await message.delete(delay=0)
            await message.channel.send(
                f"{message.author.mention} | Do not send message with more than 10 emoji.",
                delete_after=5,
            )
            return

        async def __internal_funtion(*, hook: str, message: discord.Message):
            try:
                await self.bot._execute_webhook(
                    hook,
                    username=f"{message.author}",
                    avatar_url=message.author.display_avatar.url,
                    content=message.content[:1990],
                    allowed_mentions=discord.AllowedMentions.none(),
                    suppressor=(ValueError, discord.HTTPException),
                )
            except discord.NotFound:
                pass

        await message.delete(delay=2)
        __functions: list = []
        async for webhook in self.bot.guild_configurations.find(
            {"global_chat.enable": True}
        ):
            if hook := webhook["global_chat"]["webhook"]:
                __functions.append(__internal_funtion(hook=hook, message=message))

        if __functions:
            await asyncio.gather(*__functions, return_exceptions=False)

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.bot.wait_until_ready()
        if (
            before.content != after.content
            and after.guild is not None
            and after.author.id == self.bot.user.id
        ):
            AWAITABLES: List[Coroutine] = [
                self._on_message_passive(after),
                self._scam_detection(after),
                self.equation_solver(after),
            ]
            await asyncio.gather(*AWAITABLES, return_exceptions=False)

    async def _on_message_leveling(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        bucket: Optional[commands.Cooldown] = self.message_cooldown.get_bucket(message)
        if bucket is None:
            return

        if bucket.update_rate_limit():
            return

        try:
            enable: bool = self.bot.guild_configurations_cache[message.guild.id][
                "leveling"
            ]["enable"]
        except KeyError:
            return

        if not enable:
            return

        try:
            role: List[int] = (
                self.bot.guild_configurations_cache[message.guild.id]["leveling"][
                    "ignore_role"
                ]
                or []
            )
        except KeyError:
            role = []

        if any(message.author._roles.has(r) for r in role):
            return

        try:
            ignore_channel: List = (
                self.bot.guild_configurations_cache[message.guild.id]["leveling"][
                    "ignore_channel"
                ]
                or []
            )
        except KeyError:
            ignore_channel = []

        if message.channel.id in ignore_channel:
            return

        await self.__add_xp(
            member=message.author, xp=random.randint(10, 15), msg=message
        )

        try:
            announce_channel: int = (
                self.bot.guild_configurations_cache[message.guild.id]["leveling"][
                    "channel"
                ]
                or 0
            )
        except KeyError:
            return
        else:
            collection: Collection = self.bot.guild_level_db[f"{message.guild.id}"]
            ch: discord.TextChannel = await self.bot.getch(
                self.bot.get_channel,
                self.bot.fetch_channel,
                announce_channel,
                force_fetch=True,
            )
            if ch and (
                data := await collection.find_one_and_update(
                    {"_id": message.author.id},
                    {"$inc": {"xp": 0}},
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                )
            ):
                cog: Utils = self.bot.get_cog("Utils")  # type: ignore
                level = int((data["xp"] // 42) ** 0.55)
                xp = cog._Utils__get_required_xp(level + 1)  # type: ignore
                rank = await cog._Utils__get_rank(collection=collection, member=message.author)  # type: ignore
                file: discord.File = await rank_card(
                    level,
                    rank,
                    message.author,
                    current_xp=data["xp"],
                    custom_background="#000000",
                    xp_color="#FFFFFF",
                    next_level_xp=xp,
                )
                await message.reply("GG! Level up!", file=file)

    async def _scam_detection(self, message: discord.Message) -> Optional[bool]:
        if message.guild is None:
            return False

        if message.author.id == self.bot.user.id:
            return False

        if not message.channel.permissions_for(message.guild.me).send_messages:  # type: ignore
            return

        API = "https://anti-fish.bitflow.dev/check"

        match_list = re.findall(
            r"(?:[A-z0-9](?:[A-z0-9-]{0,61}[A-z0-9])?\.)+[A-z0-9][A-z0-9-]{0,61}[A-z0-9]",
            message.content,
        )

        if any(self.__scam_link_cache.get(i, False) for i in set(match_list)):
            with suppress(discord.Forbidden):
                await message.channel.send(
                    f"\N{WARNING SIGN} potential scam detected in {message.author}'s message. "
                    f"Match: `{'`, `'.join(k for k, v in self.__scam_link_cache.items() if v and k in match_list)}`",
                )
            return True

        if match_list and all(
            not self.__scam_link_cache.get(i, True) for i in set(match_list)
        ):
            return False

        with suppress(aiohttp.ClientOSError):
            response = await self.bot.http_session.post(
                API,
                json={"message": message.content},
                headers={"User-Agent": f"{self.bot.user.name} ({self.bot.github})"},
            )

            if response.status != 200:
                for i in match_list:
                    self.__scam_link_cache[i] = False
                return

            data = await response.json()

            if data["match"]:
                await message.channel.send(
                    f"\N{WARNING SIGN} potential scam detected in {message.author}'s message. Match: "
                    + (
                        f"`{'`, `'.join(i['domain'] for i in data['matches'])}`"
                        if len(data["matches"]) < 10
                        else str(len(data["matches"]))
                    )
                )
                for match in data["matches"]:
                    self.__scam_link_cache[match["domain"]] = True
                    await asyncio.sleep(0)
                return True

    async def __add_xp(self, *, member: Union[discord.Member, discord.User], xp: int, msg: discord.Message):
        assert isinstance(msg.author, discord.Member) and msg.guild is not None

        collection: Collection = self.bot.guild_level_db[f"{member.guild.id}"]
        data = await collection.find_one_and_update(
            {"_id": member.id},
            {"$inc": {"xp": xp}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        level = int((data["xp"] // 42) ** 0.55)
        await self.__add_role__xp(msg.guild.id, level, msg)

    async def __add_role__xp(self, guild_id: int, level: int, msg: discord.Message):
        assert isinstance(msg.author, discord.Member)
        try:
            ls = self.bot.guild_configurations_cache[guild_id]["leveling"]["reward"]
        except KeyError:
            return

        for reward in ls:
            if reward["lvl"] <= level:
                await self.__add_roles(
                    msg.author,
                    discord.Object(id=reward["role"]),
                    reason=f"Level Up role! On reaching: {level}",
                )

    async def __add_roles(
        self,
        member: discord.Member,
        role: discord.abc.Snowflake,
        reason: Optional[str] = None,
    ):
        with suppress(discord.Forbidden, discord.HTTPException):
            await member.add_roles(role, reason=reason)

    async def _on_message_passive(self, message: discord.Message):
        # sourcery skip: low-code-quality
        if message.guild is None or message.author.bot:
            return

        await asyncio.gather(
            self._on_message_passive_afk_user_message(message),
            self._on_message_passive_afk_user_mention(message),
        )

    async def _on_message_passive_afk_user_message(self, message: discord.Message):
        # code - when the AFK user messages
        data = await self.bot.extra_collections.find_one_and_update(
            {
                "$and": [
                    {
                        "$or": [
                            {
                                "afk.messageAuthor": message.author.id,
                                "afk.guild": message.guild.id,
                            },
                            {
                                "afk.messageAuthor": message.author.id,
                                "afk.global": True,
                            },
                        ]
                    },
                    {"afk.ignoreChannel": {"$nin": [message.channel.id]}},
                ]
            },
            {"$pull": {"afk": {"messageAuthor": message.author.id}}},
            {"afk": {"$elemMatch": {"messageAuthor": message.author.id}}},
            return_document=ReturnDocument.BEFORE,
        )
        if message.author.id not in self.bot.afk or not data or "afk" not in data:
            self.bot.afk = set(
                await self.bot.extra_collections.distinct("afk.messageAuthor")
            )
            return
        data = data["afk"][0]
        await message.channel.send(f"{message.author.mention} welcome back!")
        try:
            if str(message.author.display_name).startswith(("[AFK]", "[AFK] ")) and (
                isinstance(message.author, discord.Member)
            ):
                name = message.author.display_name[5:]
                if len(name) != 0 or name not in (" ", ""):
                    await message.author.edit(
                        nick=name, reason=f"{message.author} came after AFK"
                    )
        except discord.Forbidden:
            pass

        await self.bot.delete_timer(**{"_id": data["_id"]})
        self.bot.afk = set(
            await self.bot.extra_collections.distinct("afk.messageAuthor")
        )

    async def _on_message_passive_afk_user_mention(self, message: discord.Message):
        if message.guild is None:
            return
        for user in message.mentions:
            if (user.id in self.bot.afk) and (
                data := await self.bot.extra_collections.find_one(
                    {
                        "$and": [
                            {
                                "$or": [
                                    {
                                        "afk.messageAuthor": user.id,
                                        "afk.guild": message.guild.id,
                                    },
                                    {
                                        "afk.messageAuthor": user.id,
                                        "afk.global": True,
                                    },
                                ]
                            },
                            {"afk.ignoreChannel": {"$nin": [message.channel.id]}},
                        ]
                    },
                    {"afk": {"$elemMatch": {"messageAuthor": user.id}}},
                )
            ):
                if "afk" not in data:
                    return
                data = data["afk"][0]
                await message.channel.send(
                    f"{message.author.mention} {self.bot.get_user(data['messageAuthor'])} is AFK: {data['text']}"
                )
        self.bot.afk = set(
            await self.bot.extra_collections.distinct("afk.messageAuthor")
        )

    async def _what_is_this(
        self, message: Union[discord.Message, str], *, channel: discord.TextChannel
    ) -> None:
        if match := QUESTION_REGEX.fullmatch(
            message.content if isinstance(message, discord.Message) else message
        ):
            word = replace_many(
                match.string,
                {"means": "", "what is": "", " ": "", "?": "", ".": ""},
                ignore_case=True,
            )
            if data := await self.bot.dictionary.find_one({"word": word}):
                await channel.send(
                    f"**{data['word'].title()}**: {data['meaning'].split('.')[0]}"
                )
            return

    # Internal Message Cache Updater Events
    # caching variable `Parrot.message_cache`

    @Cog.listener("on_message")
    async def on_message_updater(self, message: discord.Message) -> None:
        if message.author.id in self.bot.message_cache:
            self.bot.message_cache[message.author.id] = message

    @Cog.listener("on_message_delete")
    async def on_message_delete_updater(self, message: discord.Message) -> None:
        if message.author.id in self.bot.message_cache:
            del self.bot.message_cache[message.author.id]

    @Cog.listener("on_message_edit")
    async def on_message_edit_updater(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        if before.author.id in self.bot.message_cache:
            self.bot.message_cache[before.author.id] = after

    @Cog.listener("on_reaction_add")
    async def on_reaction_add_updater(
        self, reaction: discord.Reaction, _: discord.User
    ) -> None:
        if reaction.message.id in self.bot.message_cache:
            self.bot.message_cache[reaction.message.id] = reaction.message

    @Cog.listener("on_reaction_remove")
    async def on_reaction_remove_updater(
        self, reaction: discord.Reaction, _: discord.User
    ) -> None:
        if reaction.message.id in self.bot.message_cache:
            self.bot.message_cache[reaction.message.id] = reaction.message

    @Cog.listener("on_reaction_clear")
    async def on_reaction_clear_updater(
        self, message: discord.Message, _: List[discord.Reaction]
    ) -> None:
        if message.id in self.bot.message_cache:
            self.bot.message_cache[message.id] = message

    @Cog.listener("on_reaction_clear_emoji")
    async def on_reaction_clear_emoji_updater(self, reaction: discord.Reaction) -> None:
        if reaction.message.id in self.bot.message_cache:
            self.bot.message_cache[reaction.message.id] = reaction.message


async def setup(bot: Parrot) -> None:
    await bot.add_cog(OnMsg(bot))
