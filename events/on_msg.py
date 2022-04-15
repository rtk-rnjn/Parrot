# -*- coding: utf-8 -*-

from __future__ import annotations

import typing as tp

import aiohttp
import discord
import random
import io
import json
from discord import Webhook
from discord.ext import commands
import textwrap
import re
from aiohttp import ClientResponseError

from time import time
from urllib.parse import quote_plus
from pymongo import ReturnDocument

from utilities.regex import LINKS_NO_PROTOCOLS, INVITE_RE
from utilities.rankcard import rank_card

from core import Parrot, Cog

with open("extra/profanity.json") as f:
    bad_dict = json.load(f)

TRIGGER = (
    "ok google,",
    "ok google ",
    "hey google,",
    "hey google ",
)
GITHUB_RE = re.compile(
    r"https://github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/blob/"
    r"(?P<path>[^#>]+)(\?[^#>]+)?(#L(?P<start_line>\d+)(([-~:]|(\.\.))L(?P<end_line>\d+))?)"
)

GITHUB_GIST_RE = re.compile(
    r"https://gist\.github\.com/([a-zA-Z0-9-]+)/(?P<gist_id>[a-zA-Z0-9]+)/*"
    r"(?P<revision>[a-zA-Z0-9]*)/*#file-(?P<file_path>[^#>]+?)(\?[^#>]+)?"
    r"(-L(?P<start_line>\d+)([-~:]L(?P<end_line>\d+))?)"
)

GITHUB_HEADERS = {"Accept": "application/vnd.github.v3.raw"}

GITLAB_RE = re.compile(
    r"https://gitlab\.com/(?P<repo>[\w.-]+/[\w.-]+)/\-/blob/(?P<path>[^#>]+)"
    r"(\?[^#>]+)?(#L(?P<start_line>\d+)(-(?P<end_line>\d+))?)"
)

BITBUCKET_RE = re.compile(
    r"https://bitbucket\.org/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/src/(?P<ref>[0-9a-zA-Z]+)"
    r"/(?P<file_path>[^#>]+)(\?[^#>]+)?(#lines-(?P<start_line>\d+)(:(?P<end_line>\d+))?)"
)

whitelist = [
    615785223296253953,  # `Tari#2755`
    741614468546560092,  # `!! Ritik Ranjan [*.*]#9230`
    523452718413643788,  # `Hay#6433`
    699839134709317642,  # `proguy914629.bot#5419`
    531179463673774080,  # `ROLEX#6596`
    857103603130302514,  # `Var_Monke#1354`
    770646750804312105,  # `Nιgнт Fυяу ♪🤍#4371`
]


class Delete(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=30.0)
        self.user = user
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user.bot:
            return True
        if self.user.id != interaction.user.id:
            return False
        return True

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.message.delete()
        self.stop()


class OnMsg(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.channel
        )
        self.collection = None
        self.log_collection = bot.mongo.parrot_db["logging"]
        self.pattern_handlers = [
            (GITHUB_RE, self._fetch_github_snippet),
            (GITHUB_GIST_RE, self._fetch_github_gist_snippet),
            (GITLAB_RE, self._fetch_gitlab_snippet),
            (BITBUCKET_RE, self._fetch_bitbucket_snippet),
        ]
        self.message_append = []
        self.message_cooldown = commands.CooldownMapping.from_cooldown(
            1,
            60,
            commands.BucketType.member,
        )

    async def _fetch_response(self, url: str, response_format: str, **kwargs) -> tp.Any:
        """Makes http requests using aiohttp."""
        async with self.bot.http_session.get(
            url, raise_for_status=True, **kwargs
        ) as response:
            if response_format == "text":
                return await response.text()
            if response_format == "json":
                return await response.json()

    def _find_ref(self, path: str, refs: tuple) -> tuple:
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
        self, repo: str, path: str, start_line: str, end_line: str
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
        start_line: str,
        end_line: str,
    ) -> str:
        """Fetches a snippet from a GitHub gist."""
        gist_json = await self._fetch_response(
            f'https://api.github.com/gists/{gist_id}{f"/{revision}" if len(revision) > 0 else ""}',
            "json",
            headers=GITHUB_HEADERS,
        )

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
        self, repo: str, path: str, start_line: str, end_line: str
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
        self, file_contents: str, file_path: str, start_line: str, end_line: str
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

        split_file_contents = file_contents.splitlines()

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

    async def query_ddg(self, query: str) -> tp.Optional[str]:
        link = "https://api.duckduckgo.com/?q={}&format=json&pretty=1".format(query)
        # saying `ok google`, and querying from ddg LOL.
        res = await self.bot.http_session.get(link)
        data = json.loads(await res.text())
        if data.get("Abstract"):
            return data.get("Abstract")
        if data["RelatedTopics"]:
            return data["RelatedTopics"][0]["Text"]

    async def quick_answer(self, message: discord.Message):
        """This is good."""
        if message.content.lower().startswith(TRIGGER):
            if message.content.lower().startswith("ok google"):
                query = message.content.lower()[10:]
                res = await self.query_ddg(query)
                if not res:
                    return
                try:
                    return await message.channel.send(res)
                except discord.Forbidden:
                    pass
            if message.content.lower().startswith("hey google"):
                query = message.content.lower()[11:]
                res = await self.query_ddg(query)
                if not res:
                    return
                try:
                    return await message.channel.send(res)
                except discord.Forbidden:
                    pass

    def refrain_message(self, msg: str):
        if "chod" in msg.replace(",", "").split(" "):
            return False
        for bad_word in bad_dict:
            if bad_word.lower() in msg.replace(",", "").split(" "):
                return False
        return True

    def is_banned(self, user) -> bool:
        # return True if member is banned else False
        try:
            user = self.bot.banned_users[user.id]
        except KeyError:
            return False
        else:
            return bool(self.bot.banned_users[user.id].get("global"))

    async def on_invite(self, message: discord.Message, invite_link: list):
        if data := await self.log_collection.find_one(
            {"_id": message.guild.id, "on_invite_post": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_invite_post"], session=self.bot.http_session
            )
            if webhook:
                content = f"""**Invite Link Posted**

`Author (ID):` **{message.author} [`{message.author.id}`]**
`Message ID :` **{message.id}**
`Jump URL   :` **{message.jump_url}**
`Invite Link:` **<{invite_link[0]}>**

`Content    :` **{message.content[:250:]}**
"""
                msg = message
                if content:
                    fp = io.BytesIO(
                        f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n".encode()
                    )
                else:
                    fp = io.BytesIO("NOTHING HERE".encode())
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )

    @Cog.listener()
    async def on_message(self, message):
        await self.bot.wait_until_ready()
        await self._on_message_leveling(message)
        await self._scam_detection(message)
        if not message.guild:
            return
        if message.guild.me.id == message.author.id:
            return
        message_to_send = await self._parse_snippets(message.content)

        if 0 < len(message_to_send) <= 2000 and (
            message.guild.id != 336642139381301249 or message.author.id in whitelist
        ):
            await message.channel.send(message_to_send, view=Delete(message.author))
            try:
                await message.edit(suppress=True)
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass

        if message.author.bot:
            return

        await self.quick_answer(message)
        await self._on_message_passive(message)
        channel = await self.bot.mongo.parrot_db.global_chat.find_one(
            {"_id": message.guild.id, "channel_id": message.channel.id}
        )
        if links := INVITE_RE.findall(message.content):
            await self.on_invite(message, links)

        if channel:
            bucket = self.cd_mapping.get_bucket(message)
            retry_after = bucket.update_rate_limit()

            if retry_after:
                return await message.channel.send(
                    f"{message.author.mention} Chill out | You reached the limit | Continous spam may leads to ban from global-chat | **Send message after {round(retry_after, 3)}s**",
                    delete_after=10,
                )

            guild = channel
            role_id = guild.get("ignore_role") or guild.get("ignore-role") or 0
            if message.author._roles.has(role_id):
                return

            if message.content.startswith(
                ("$", "!", "%", "^", "&", "*", "-", ">", "/", "\\")
            ):  # bot commands or mention in starting
                return

            urls = LINKS_NO_PROTOCOLS.search(message.content)
            if urls:
                try:
                    await message.delete(delay=0)
                    return await message.channel.send(
                        f"{message.author.mention} | URLs aren't allowed.",
                        delete_after=5,
                    )
                except discord.Forbidden:
                    return await message.channel.send(
                        f"{message.author.mention} | URLs aren't allowed.",
                        delete_after=5,
                    )

            if len(message.content.split("\n")) > 4:
                try:
                    await message.delete(delay=0)
                    return await message.channel.send(
                        f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                        delete_after=5,
                    )
                except discord.Forbidden:
                    return await message.channel.send(
                        f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                        delete_after=5,
                    )

            to_send = self.refrain_message(message.content.lower())
            if not to_send:
                try:
                    await message.delete(delay=0)
                    return await message.channel.send(
                        f"{message.author.mention} | Sending Bad Word not allowed",
                        delete_after=5,
                    )
                except discord.Forbidden:
                    return await message.channel.send(
                        f"{message.author.mention} | Sending Bad Word not allowed",
                        delete_after=5,
                    )
            if self.is_banned(message.author):
                return
            try:
                await message.delete()
            except discord.Forbidden:
                return await message.channel.send(
                    "Bot requires **Manage Messages** permission(s) to function properly."
                )

            async for webhook in self.bot.mongo.parrot_db.global_chat.find(
                {"webhook": {"$exists": True}}, {"webhook": 1}
            ):
                hook = webhook["webhook"]
                if hook:
                    try:
                        async with aiohttp.ClientSession() as session:
                            webhook = Webhook.from_url(f"{hook}", session=session)
                            if webhook:
                                await webhook.send(
                                    content=message.content[:1990],
                                    username=f"{message.author}",
                                    avatar_url=message.author.display_avatar.url,
                                    allowed_mentions=discord.AllowedMentions.none(),
                                )
                    except discord.NotFound:
                        await self.bot.mongo.parrot_db.global_chat.delete_one(
                            {"webhook": hook}
                        )  # all hooks are unique
                    except discord.HTTPException as e:
                        pass

    @Cog.listener()
    async def on_message_delete(self, message):
        pass

    @Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        await self.bot.wait_until_ready()
        await self.bot.mongo.parrot_db.starboard.delete_one(
            {
                "$or": [
                    {"message_id.bot": payload.message_id},
                    {"message_id.author": payload.message_id},
                ]
            }
        )
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_message_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_message_delete"], session=self.bot.http_session
            )
            if webhook:
                if payload.cached_message:
                    msg = payload.cached_message
                    message_author = msg.author
                    if (message_author.id == self.bot.user.id) or message_author.bot:
                        return
                    content = msg.content
                else:
                    return

                main_content = f"""**Message Delete Event**

`ID      :` **{payload.message_id}**
`Channel :` **<#{payload.channel_id}>**
`Author  :` **{message_author}**
`Deleted at:` **<t:{int(time())}>**
"""
                if content:
                    fp = io.BytesIO(
                        f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n".encode()
                    )
                else:
                    fp = None
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt")
                    if fp is not None
                    else None,
                )

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        await self.bot.wait_until_ready()
        msg_ids = list(payload.message_ids)
        await self.bot.mongo.parrot_db.starboard.delete_one(
            {
                "$or": [
                    {"message_id.bot": {"$in": msg_ids}},
                    {"message_id.author": {"$in": msg_ids}},
                ]
            }
        )
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_bulk_message_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_bulk_message_delete"], session=self.bot.http_session
            )
            main = ""
            if webhook:
                if payload.cached_messages:
                    msgs = payload.cached_messages
                else:
                    msgs = []
                for msg in msgs:
                    if not msg.bot:
                        main += f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n"
                if msgs:
                    fp = io.BytesIO(main.encode())
                else:
                    fp = None
                main_content = f"""**Bulk Message Delete**

`Total Messages:` **{len(msgs)}**
`Channel       :` **<#{payload.channel_id}>**
"""
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt")
                    if fp is not None
                    else None,
                )

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.bot.wait_until_ready()
        if before.content != after.content:
            await self._on_message_passive(after)
            await self._scam_detection(after)

    async def _on_message_leveling(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return

        # self.message_append.append(UpdateOne({"_id": message.author.id}, {"$inc": {"count": 1}}, upsert=True))
        await self.bot.mongo.msg_db.counter.update_one(
            {"_id": message.author.id}, {"$inc": {"count": 1}}, upsert=True
        )

        bucket = self.message_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            return

        try:
            enable = self.bot.server_config[message.guild.id]["leveling"]["enable"]
        except KeyError:
            return

        if not enable:
            return

        try:
            role = (
                self.bot.server_config[message.guild.id]["leveling"]["ignore_role"]
                or []
            )
        except KeyError:
            role = []

        if any(message.author._roles.has(r) for r in role):
            return

        try:
            ignore_channel = (
                self.bot.server_config[message.guild.id]["leveling"]["ignore_channel"]
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
            announce_channel = (
                self.bot.server_config[message.guild.id]["leveling"]["channel"] or 0
            )
        except KeyError:
            return
        else:
            collection = self.bot.mongo.leveling[f"{message.guild.id}"]
            ch = await self.bot.getch(
                self.bot.get_channel,
                self.bot.fetch_channel,
                announce_channel,
                force_fetch=False,
            )
            if ch:
                if data := await collection.find_one_and_update(
                    {"_id": message.author.id},
                    {"$inc": {"xp": 0}},
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                ):
                    cog = self.bot.get_cog("Utils")
                    level = int((data["xp"] // 42) ** 0.55)
                    xp = cog._Utils__get_required_xp(level + 1)
                    rank = await cog._Utils__get_rank(
                        collection=collection, member=message.author
                    )
                    file = await rank_card(
                        level,
                        rank,
                        message.author,
                        current_xp=data["xp"],
                        custom_background="#000000",
                        xp_color="#FFFFFF",
                        next_level_xp=xp,
                    )
                    await message.reply("GG! Level up!", file=file)

    async def _scam_detection(self, message: discord.Message):
        API = "https://anti-fish.bitflow.dev/check"

        match_list = re.findall(
            r"(?:[A-z0-9](?:[A-z0-9-]{0,61}[A-z0-9])?\.)+[A-z0-9][A-z0-9-]{0,61}[A-z0-9]",
            message.content,
        )

        if not match_list:
            return

        response = await self.bot.http_session.post(
            API,
            json={"message": message.content},
            headers={"User-Agent": f"{self.bot.user.name} ({self.bot.github})"},
        )

        if response.status != 200:
            return

        data = await response.json()

        if data["match"]:
            await message.channel.send(
                f"\N{WARNING SIGN} potential scam detected in {message.author}'s message. Match: `{'`, `'.join(match_list)}`",
            )

    async def __add_xp(self, *, member: discord.Member, xp: int, msg: discord.Message):
        collection = self.bot.mongo.leveling[f"{member.guild.id}"]
        data = await collection.find_one_and_update(
            {"_id": member.id},
            {"$inc": {"xp": xp}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        level = int((data["xp"] // 42) ** 0.55)
        await self.__add_role__xp(msg.guild.id, level, msg)

    async def __add_role__xp(self, guild_id: int, level: int, msg: discord.Message):
        try:
            ls = self.bot.server_config[guild_id]["leveling"]["reward"]
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
        member,
        role: tp.Union[discord.Roles, discord.Object],
        reason: tp.Optional[str] = None,
    ):
        try:
            await member.add_roles(role, reason=reason)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _on_message_passive(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return

        # code: when the AFK user messages
        if message.author.id in self.bot.afk:
            if data := await self.bot.mongo.parrot_db.afk.find_one(
                {
                    "$or": [
                        {"messageAuthor": message.author.id, "guild": message.guild.id},
                        {"messageAuthor": message.author.id, "global": True},
                    ]
                }
            ):
                if message.channel.id in data["ignoredChannel"]:
                    return  # There exists `$nin` operator in MongoDB
                await message.channel.send(
                    f"{message.author.mention} welcome back! You were AFK <t:{int(data['at'])}:R>\n"
                    f"> You were mentioned **{len(data['pings'])}** times"
                )
                try:
                    if str(message.author.display_name).startswith(("[AFK]", "[AFK] ")):
                        name = message.author.display_name[5:]
                        if len(name) != 0 or name not in (" ", ""):
                            await message.author.edit(
                                nick=name, reason=f"{message.author} came after AFK"
                            )
                except discord.Forbidden:
                    pass
                await self.bot.mongo.parrot_db.afk.delete_one({"_id": data["_id"]})
                await self.bot.mongo.parrot_db.timers.delete_one({"_id": data["_id"]})
                self.bot.afk = set(
                    await self.bot.mongo.parrot_db.afk.distinct("messageAuthor")
                )

        # code from someone mentions the AFK user
        if message.mentions:
            for user in message.mentions:
                if data := await self.bot.mongo.parrot_db.afk.find_one(
                    {
                        "$or": [
                            {"messageAuthor": user.id, "guild": user.guild.id},
                            {"messageAuthor": user.id, "global": True},
                        ]
                    }
                ):
                    if message.channel.id in data["ignoredChannel"]:
                        return
                    post = {
                        "messageAuthor": message.author.id,
                        "channel": message.channel.id,
                        "messageURL": message.jump_url,
                    }
                    await self.bot.mongo.parrot_db.afk.update_one(
                        {"_id": data["_id"]}, {"$addToSet": {"pings": post}}
                    )
                    await message.channel.send(
                        f"{message.author.mention} {self.bot.get_user(data['messageAuthor'])} is AFK: {data['text']}"
                    )

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        await self.bot.wait_until_ready()
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_message_edit": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_message_edit"], session=self.bot.http_session
            )
            if webhook:
                if payload.cached_message:
                    msg = payload.cached_message
                    message_author = msg.author
                    if message_author.bot:
                        return
                    content = msg.content
                else:
                    # guild = self.bot.get_guild(payload.guild_id)
                    message_author = None
                    content = None

                main_content = f"""**Message Edit Event**

`ID       :` **{payload.message_id}**
`Channel  :` **<#{payload.channel_id}>**
`Author   :` **{message_author}**
`Edited at:` **<t:{int(time())}>**
`Jump URL :` **<https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}>**
"""
                if content:
                    fp = io.BytesIO(
                        f"[{msg.created_at}] {msg.author.name}#{msg.author.discriminator} | {msg.content if msg.content else ''} {', '.join([i.url for i in msg.attachments]) if msg.attachments else ''} {', '.join([str(i.to_dict()) for i in msg.embeds]) if msg.embeds else ''}\n".encode()
                    )
                else:
                    fp = None
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt")
                    if fp is not None
                    else None,
                )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(OnMsg(bot))
