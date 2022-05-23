from __future__ import annotations
import asyncio
import base64
import binascii
import os
import yarl

import discord
from discord.ext import commands
import re

from core import Parrot, Cog, Context


TOKEN_REGEX = re.compile(r"[a-zA-Z0-9_-]{23,28}\.[a-zA-Z0-9_-]{6,7}\.[a-zA-Z0-9_-]{27}")
DISCORD_PY_ID = 336642139381301249


class GistContent:
    def __init__(self, argument: str):
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
        int(base64.b64decode(user_id, validate=True))
    except (ValueError, binascii.Error):
        return False
    else:
        return True


class Gist(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._req_lock = asyncio.Lock(loop=self.bot.loop)
        self.token = os.environ["GITHUB_TOKEN"]

    async def github_request(
        self, method, url, *, params=None, data=None, headers=None
    ):
        hdrs = {
            "Accept": "application/vnd.github.inertia-preview+json",
            "User-Agent": f"Discord Bot: {self.bot.user} {self.bot.github}",
            "Authorization": f"token {self.token}",
        }

        req_url = yarl.URL("https://api.github.com") / url

        if headers is not None and isinstance(headers, dict):
            hdrs.update(headers)

        await self._req_lock.acquire()
        try:
            async with self.bot.http_session.request(
                method, req_url, params=params, json=data, headers=hdrs
            ) as r:
                remaining = r.headers.get("X-Ratelimit-Remaining")
                js = await r.json()
                if r.status == 429 or remaining == "0":
                    # wait before we release the lock
                    delta = discord.utils._parse_ratelimit_header(r)
                    await asyncio.sleep(delta)
                    self._req_lock.release()
                    return await self.github_request(
                        method, url, params=params, data=data, headers=headers
                    )
                if 300 > r.status >= 200:
                    return js
                raise commands.CommandError(js["message"])
        finally:
            if self._req_lock.locked():
                self._req_lock.release()

    async def create_gist(
        self, content, *, description=None, filename=None, public=True
    ):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        filename = filename or "output.txt"
        data = {"public": public, "files": {filename: {"content": content}}}

        if description:
            data["description"] = description

        js = await self.github_request("POST", "gists", data=data, headers=headers)
        return js["html_url"]

    @Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.guild.id == DISCORD_PY_ID:
            return

        tokens = [
            token
            for token in TOKEN_REGEX.findall(message.content)
            if validate_token(token)
        ]
        if tokens and message.author.id != self.bot.user.id:
            url = await self.create_gist(
                "\n".join(tokens), description="Discord tokens detected"
            )
            msg = f"{message.author.mention}, I have found tokens and sent them to <{url}> to be invalidated for you."
            return await message.channel.send(msg)

    @commands.group(name="gist")
    @commands.is_owner()
    async def gist(self, ctx: Context):
        """Gist related commands"""

    @gist.command(name="create")
    @commands.is_owner()
    async def gist_create(self, ctx: Context, *, content: str):
        """Create a gist from the given content"""
        content = GistContent(content)
        url = await self.create_gist(
            content.source,
        )
        await ctx.send(f"Created gist at <{url}>")

    @gist.command(name="delete")
    @commands.is_owner()
    async def gist_delete(self, ctx: Context, gist_id: str):
        """Delete a gist"""
        if gist_id.startswith("<") and gist_id.endswith(">"):
            gist_id = gist_id[1:-1]

        if not gist_id.startswith("https://gist.github.com/"):
            await ctx.send("Invalid gist ID")
            return

        gist_id = gist_id.split("/")[-1]
        await self.github_request("DELETE", f"gists/{gist_id}")
        await ctx.send(f"Deleted gist <{gist_id}>")
