from __future__ import annotations

from core import Parrot, Cog

from discord.ext import commands

import aiohttp
import asyncio
import discord
import io
import json
from discord import Webhook
import textwrap
import re
from aiohttp import ClientResponseError
from urllib.parse import quote_plus

import typing as tp

from utilities.database import parrot_db, msg_increment
from utilities.regex import LINKS_NO_PROTOCOLS, INVITE_RE
from utilities.buttons import Delete

from time import time

collection = parrot_db["global_chat"]

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


class OnMsg(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.channel
        )
        self.collection = None
        self.log_collection = parrot_db["logging"]
        self.pattern_handlers = [
            (GITHUB_RE, self._fetch_github_snippet),
            (GITHUB_GIST_RE, self._fetch_github_gist_snippet),
            (GITLAB_RE, self._fetch_gitlab_snippet),
            (BITBUCKET_RE, self._fetch_bitbucket_snippet),
        ]

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
        res = await self.bot.session.get(link)
        data = json.loads(await res.text())
        if data.get("Abstract"):
            return data.get("Abstract")
        if data["RelatedTopics"]:
            return data["RelatedTopics"][0]["Text"]

    async def quick_answer(self, message: discord.Message):
        """This is good."""
        if message.content.lower().startswith(TRIGGER):
            if message.content.lower().startswith("ok"):
                query = message.content.lower()[10:]
                res = await self.query_ddg(query)
                if not res:
                    return
                try:
                    return await message.channel.send(res)
                except discord.Forbidden:
                    pass
            if message.content.lower().startswith("hey"):
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

    async def is_banned(self, user) -> bool:
        if self.collection is None:
            db = await self.bot.db("parrot_db")
            self.collection = db["banned_users"]
        if data := await self.collection.find_one({"_id": user.id}):
            if data["chat"] or data["global"]:
                return True
        else:
            return False

    async def on_invite(self, message: discord.Message, invite_link: list):
        if data := await self.log_collection.find_one(
            {"_id": message.guild.id, "on_invite_post": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_invite_post"], session=self.bot.session
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
                    fp = io.BytesIO("NOTHING HERE".ecnode())
                await webhook.send(
                    content=content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )

    @Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.guild.me.id == message.author.id:
            return
        message_to_send = await self._parse_snippets(message.content)

        if 0 < len(message_to_send) <= 2000:
            await message.channel.send(message_to_send, view=Delete(message.author))
            try:
                await message.edit(suppress=True)
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass

        if message.author.bot:
            return
        await msg_increment(message.guild.id, message.author.id)  # for gw only
        await self.quick_answer(message)
        channel = await collection.find_one(
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

            guild = await collection.find_one({"_id": message.guild.id})
            # data = await collection.find({})

            role = message.guild.get_role(guild["ignore-role"])
            if role:
                if role in message.author.roles:
                    return

            if message.content.startswith(
                ("$", "!", "%", "^", "&", "*", "-", ">", "/", "\\")
            ):  # bot commands or mention in starting
                return

            urls = LINKS_NO_PROTOCOLS.search(message.content)
            if urls:
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | URLs aren't allowed.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | URLs aren't allowed.",
                        delete_after=5,
                    )

            if "discord.gg" in message.content.lower():
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )
            if len(message.content.split("\n")) > 4:
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Do not send message in 4-5 lines or above.",
                        delete_after=5,
                    )

            if "discord.com" in message.content.lower():
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Advertisements aren't allowed.",
                        delete_after=5,
                    )

            to_send = self.refrain_message(message.content.lower())
            if to_send:
                pass
            elif not to_send:
                try:
                    await message.delete()
                    return await message.channel.send(
                        f"{message.author.mention} | Sending Bad Word not allowed",
                        delete_after=5,
                    )
                except Exception:
                    return await message.channel.send(
                        f"{message.author.mention} | Sending Bad Word not allowed",
                        delete_after=5,
                    )
            is_user_banned = await self.is_banned(message.author)
            if is_user_banned:
                return
            try:
                await asyncio.sleep(0.1)
                await message.delete()
            except Exception:
                return await message.channel.send(
                    "Bot requires **Manage Messages** permission(s) to function properly."
                )

            async for webhook in collection.find({}):
                hook = webhook["webhook"]
                if hook:
                    try:
                        async with aiohttp.ClientSession() as session:
                            webhook = Webhook.from_url(f"{hook}", session=session)
                            await webhook.send(
                                content=message.content,
                                username=f"{message.author}",
                                avatar_url=message.author.display_avatar.url,
                                allowed_mentions=discord.AllowedMentions.none(),
                            )
                    except Exception:
                        continue

    @Cog.listener()
    async def on_message_delete(self, message):
        pass

    @Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass

    @Cog.listener()
    async def on_raw_message_delete(self, payload):
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_message_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_message_delete"], session=self.bot.session
            )
            if webhook:
                if payload.cached_message:
                    msg = payload.cached_message
                    message_author = msg.author
                    if (message_author.id == self.bot.user.id) or message_author.bot:
                        return
                    content = msg.content
                else:
                    guild = self.bot.get_guild(payload.guild_id)
                    message_author = None
                    content = None

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
                    fp = io.BytesIO("NOTHING HERE".ecnode())
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_bulk_message_delete": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_bulk_message_delete"], session=self.bot.session
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
                    fp = io.BytesIO("NOTHING HERE", filename="content.txt")
                main_content = f"""**Bulk Message Delete**

`Total Messages:` **{len(msgs)}**
`Channel       :` **<#{payload.channel_id}>**
"""
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )

    @Cog.listener()
    async def on_message_edit(self, before, after):
        pass

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        if data := await self.log_collection.find_one(
            {"_id": payload.guild_id, "on_message_edit": {"$exists": True}}
        ):
            webhook = discord.Webhook.from_url(
                data["on_message_edit"], session=self.bot.session
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
                    fp = io.BytesIO("NOTHING HERE".ecnode())
                await webhook.send(
                    content=main_content,
                    avatar_url=self.bot.user.avatar.url,
                    username=self.bot.user.name,
                    file=discord.File(fp, filename="content.txt"),
                )


def setup(bot):
    bot.add_cog(OnMsg(bot))
