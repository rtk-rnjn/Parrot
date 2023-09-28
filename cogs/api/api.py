from __future__ import annotations

import asyncio
import base64
import binascii
import os
import re
from contextlib import suppress

import yarl

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

TOKEN_REGEX = re.compile(r"[a-zA-Z0-9_-]{23,28}\.[a-zA-Z0-9_-]{6,7}\.[a-zA-Z0-9_-]{27,}")
DISCORD_PY_ID = 336642139381301249


class GistContent:
    def __init__(self, argument: str) -> None:
        try:
            block, code = argument.split("\n", 1)
        except ValueError:
            self.source = argument
            self.language = None
        else:
            if not block.startswith("```") and not code.endswith("```"):
                self.source = argument
                self.language = None
            else:
                self.language = block[3:]
                self.source = code.rstrip("`").replace("```", "")


def validate_token(token: str) -> bool:
    try:
        # Just check if the first part validates as a user ID
        (user_id, _, _) = token.split(".")
        user_id = int(base64.b64decode(f"{user_id}==", validate=True))
    except (ValueError, binascii.Error):
        return False
    else:
        return True


class Gist(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._req_lock = asyncio.Lock()
        self.token = os.environ["GITHUB_TOKEN"]

        self.__internal_token_caching = set()

    @property
    def internal_token_cache(self) -> set[str]:
        return self.__internal_token_caching

    async def github_request(self, method, url, *, params=None, data=None, headers=None, repo=None):
        hdrs = {
            "Accept": "application/vnd.github.inertia-preview+json",
            "User-Agent": f"DiscordBot {self.bot.user} {self.bot.github}",
            "Authorization": f"token {self.token}",
        }

        if not repo:
            req_url = yarl.URL("https://api.github.com") / url
        else:
            req_url = yarl.URL("https://api.github.com") / "repos" / repo / url

        if headers is not None and isinstance(headers, dict):
            hdrs = {**hdrs, **headers}

        await self._req_lock.acquire()
        try:
            async with self.bot.http_session.request(method, req_url, params=params, json=data, headers=hdrs) as r:
                remaining = r.headers.get("X-Ratelimit-Remaining")
                js = await r.json()
                if r.status == 429 or remaining == "0":
                    # wait before we release the lock
                    delta = discord.utils._parse_ratelimit_header(r)
                    await asyncio.sleep(delta)
                    self._req_lock.release()
                    return await self.github_request(method, url, params=params, data=data, headers=headers)
                if 300 > r.status >= 200:
                    return js
                raise commands.CommandError(js["message"])
        finally:
            if self._req_lock.locked():
                self._req_lock.release()

    async def create_gist(self, content, *, description=None, filename=None, public=True):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        filename = filename or "output.txt"
        data = {"public": public, "files": {filename: {"content": content}}}

        if description:
            data["description"] = description

        js = await self.github_request("POST", "gists", data=data, headers=headers)
        return js["html_url"]

    async def create_issue(self, title, body):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        data = {"title": title, "body": body}

        js = await self.github_request("POST", "issues", data=data, headers=headers, repo="rtk-rnjn/Parrot")
        return js["html_url"]

    def get_tokens(self, argument: str) -> list[str]:
        return [token for token in TOKEN_REGEX.findall(argument) if validate_token(token)]

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if not message.guild or message.guild.id == DISCORD_PY_ID:
            return

        tokens = self.get_tokens(message.content)
        if not tokens:
            return

        if all(token in self.__internal_token_caching for token in tokens):
            return

        _qs = ", ".join(["?" for _ in range(len(tokens))])
        result = await self.bot.sql.execute(
            f"""SELECT token FROM discord_tokens WHERE token IN ({_qs})""",
            (*tokens,),
        )
        if await result.fetchall():
            return

        if tokens and message.author.id != self.bot.user.id:
            url = await self.create_gist("\n".join(tokens), description="Discord tokens detected")
            msg = f"{message.author.mention}, found tokens and sent them to <{url}> to be invalidated for you."
            self.__internal_token_caching.update(set(tokens))

            with suppress(discord.HTTPException):
                await message.channel.send(msg)
        await asyncio.gather(self.add_to_caching_db(tokens))

    async def add_to_caching_db(self, tokens: list[str]):
        asqlite = self.bot.sql
        query = """INSERT INTO discord_tokens (token) VALUES (?) ON CONFLICT DO NOTHING"""
        await asqlite.executemany(query, [tuple(tokens)])
        await asqlite.commit()

    @commands.group(name="gist")
    @commands.is_owner()
    async def gist(self, ctx: Context):
        """Gist related commands."""

    @gist.command(name="create", aliases=["make", "mk", "new"])
    @commands.is_owner()
    async def gist_create(self, ctx: Context, *, content: str):
        """Create a gist from the given content."""
        content = GistContent(content)  # type: ignore
        url = await self.create_gist(
            content.source,  # type: ignore
        )
        await ctx.send(f"Created gist at <{url}>")

    @gist.command(name="delete", aliases=["remove", "del", "rm"])
    @commands.is_owner()
    async def gist_delete(self, ctx: Context, gist_id: str):
        """Delete a gist."""
        if gist_id.startswith("<") and gist_id.endswith(">"):
            gist_id = gist_id[1:-1]

        if not gist_id.startswith("https://gist.github.com/"):
            await ctx.send("Invalid gist ID")
            return

        gist_id = gist_id.split("/")[-1]
        await self.github_request("DELETE", f"gists/{gist_id}")
        await ctx.send(f"Deleted gist <{gist_id}>")
