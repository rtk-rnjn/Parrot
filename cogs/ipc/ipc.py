from __future__ import annotations

import os
import time
from random import choice
from typing import Any

from discord.ext.ipc.objects import ClientPayload
from discord.ext.ipc.server import Server

import discord
from api import cricket_api
from core import Cog, Parrot
from discord.ext import commands

from .methods import channel_to_json, emoji_to_json, member_to_json, role_to_json, thread_to_json, user_to_json


class IPCRoutes(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ON_TESTING = False

    def _overwrite_to_json(
        self,
        overwrites: dict[discord.Member | discord.Role | discord.Object, discord.PermissionOverwrite],
    ) -> dict[str, dict[str, bool | None]]:
        try:
            return {str(target.id): overwrite._values for target, overwrite in overwrites.items()}
        except Exception:
            return {}

    @Server.route()
    async def echo(self, data: ClientPayload) -> dict[str, Any]:
        return data.raw

    @Server.route()
    async def db_exec_find_one(self, data: ClientPayload) -> dict[str, Any]:
        db = data.db
        collection = data.collection

        query = getattr(data, "query", {})
        projection = getattr(data, "projection", {})

        return await self.bot.mongo[db][collection].find_one(query, projection)

    @Server.route()
    async def db_exec_update_one(self, data: ClientPayload) -> Any:
        db: str = data.db
        collection: str = data.collection

        query: dict[str, Any] = getattr(data, "query", {})
        update: dict[str, Any] = getattr(data, "update", {})
        upsert: bool = getattr(data, "upsert", False)

        return await self.bot.mongo[db][collection].update_one(query, update, upsert=upsert)

    @Server.route()
    async def sql_execute(self, data: ClientPayload) -> Any:
        args = [data.query]
        if values := getattr(data, "values", None):
            args.append(values)

        ini = time.perf_counter()
        cursor = await self.bot.sql.execute(*args)
        fin = time.perf_counter() - ini

        rows = [i[0] for i in cursor.description]
        affected = cursor.rowcount
        return {"result": await cursor.fetchall(), "affected": affected, "rows": rows, "timetaken": fin}

    def _get_all_commands(self, cog_group: Cog | commands.Group | None = None):
        # recusively get all commands
        if cog_group is None:
            for cmd in self.bot.commands:
                yield cmd
                if isinstance(cmd, commands.Group):
                    yield from cmd.commands
        else:
            for cmd in cog_group.walk_commands():
                yield cmd
                if isinstance(cmd, commands.Group):
                    yield from cmd.commands

    @Server.route(name="commands")
    async def _commands(self, data: ClientPayload) -> dict[str, Any]:
        if name := getattr(data, "name", None):
            cmds = [self.bot.get_command(name)]
        elif cog := getattr(data, "cog", None):
            cmds = list(self._get_all_commands(self.bot.get_cog(cog)))
        else:
            cmds = list(self._get_all_commands())

        return {
            "commands": [
                {
                    "name": command.qualified_name,
                    "aliases": command.aliases,
                    "description": command.description,
                    "usage": command.signature,
                    "enabled": command.enabled,
                    "hidden": command.hidden,
                    "cog": command.cog_name,
                    "help": command.help,
                    "brief": command.brief,
                }
                for command in cmds
                if command is not None
            ],
        }

    def __guild_channel(self, guild: discord.Guild, *, channels: bool, channel_id: int):
        if not channels:
            return []

        if not channel_id:
            return [channel_to_json(self, channel) for channel in guild.channels]

        for channel in guild.channels:
            if channel_id == channel.id:
                return [channel_to_json(self, channel)]
        return []

    def __guild_role(self, guild: discord.Guild, *, roles: bool, role_id: int):
        if not roles:
            return []

        if not role_id:
            return [role_to_json(role) for role in guild.roles]

        for role in guild.roles:
            if role_id == role.id:
                return [role_to_json(role)]
        return []

    def __guild_emoji(self, guild: discord.Guild, *, emojis: bool, emoji_id: int):
        if not emojis:
            return []

        if not emoji_id:
            return [emoji_to_json(emoji) for emoji in guild.emojis]

        for emoji in guild.emojis:
            if emoji_id == emoji.id:
                return [emoji_to_json(emoji)]
        return []

    def __guild_thread(self, guild: discord.Guild, *, threads: bool, thread_id: int):
        if not threads:
            return []

        if not thread_id:
            return [thread_to_json(channel) for channel in guild.threads]

        for channel in guild.threads:
            if thread_id == channel.id:
                return [thread_to_json(channel)]
        return []

    def __guild_member(self, guild: discord.Guild, *, members: bool, member_id: int):
        if not members:
            return []

        if not member_id:
            return [member_to_json(member) for member in guild.members]

        for member in guild.members:
            if member_id == member.id:
                return [member_to_json(member)]
        return []

    @Server.route()
    async def guilds(self, data: ClientPayload) -> dict[str, Any]:
        if _id := getattr(data, "id", None):
            guilds = [self.bot.get_guild(_id)]
        elif name := getattr(data, "name", None):
            guilds = [discord.utils.get(self.bot.guilds, name=name)]
        else:
            guilds = self.bot.guilds

        roles = getattr(data, "roles", False)
        role_id = getattr(data, "role_id", 0)

        members = getattr(data, "members", False)
        member_id = getattr(data, "member_id", 0)

        channels = getattr(data, "channels", False)
        channel_id = getattr(data, "channel_id", 0)

        emojis = getattr(data, "emojis", False)
        emoji_id = getattr(data, "emoji_id", 0)

        threads = getattr(data, "threads", False)
        thread_id = getattr(data, "thread_id", 0)

        return {
            "guilds": [
                {
                    "id": guild.id,
                    "name": guild.name,
                    "owner": {
                        "id": guild.owner.id,
                        "name": guild.owner.name,
                        "avatar_url": guild.owner.display_avatar.url,
                    }
                    if guild.owner is not None
                    else {},
                    "member_count": guild.member_count,
                    "icon_url": guild.icon.url if guild.icon is not None else None,
                    "channels": self.__guild_channel(guild, channels=channels, channel_id=channel_id),
                    "members": self.__guild_member(guild, members=members, member_id=member_id),
                    "threads": self.__guild_thread(guild, threads=threads, thread_id=thread_id),
                    "emojis": self.__guild_emoji(guild, emojis=emojis, emoji_id=emoji_id),
                    "roles": self.__guild_role(guild, roles=roles, role_id=role_id),
                }
                for guild in guilds
                if guild is not None
            ],
        }

    @Server.route()
    async def users(self, data: ClientPayload) -> dict[str, Any]:
        if _id := getattr(data, "id", None):
            users = [self.bot.get_user(_id)]
        elif name := getattr(data, "name", None):
            users = [discord.utils.get(self.bot.users, name=name)]
        else:
            users = self.bot.users

        return {
            "users": [user_to_json(user) for user in users if user],
        }

    @Server.route()
    async def messages(self, data: ClientPayload) -> dict[str, Any]:
        channel = self.bot.get_channel(data.channel_id)
        message = await self.bot.get_or_fetch_message(
            channel,
            data.message_id,
            partial=False,
        )
        return (
            {
                "id": message.id,
                "author": {
                    "id": message.author.id,
                    "name": message.author.name,
                    "avatar_url": message.author.display_avatar.url,
                    "bot": message.author.bot,
                },
                "system": message.author.system,
                "content": message.content,
                "embeds": [embed.to_dict() for embed in message.embeds],
            }
            if isinstance(message, discord.Message)
            else {}
        )

    @Server.route()
    async def announce_global(self, data: ClientPayload) -> list[dict[str, str]]:
        MESSAGES = []
        async for data in self.bot.guild_configurations.find({}):
            webhook = data["global_chat"]
            if (hook := webhook["webhook"]) and webhook["enable"]:
                try:
                    webhook = discord.Webhook.from_url(f"{hook}", session=self.bot.http_session)
                    msg = await webhook.send(
                        content=data.content[:1990],
                        username=f"{data.author_name}",
                        avatar_url=data.avatar_url,
                        allowed_mentions=discord.AllowedMentions.none(),
                        wait=True,
                    )
                except (discord.NotFound, discord.HTTPException):
                    pass
                else:
                    MESSAGES.append(
                        {
                            "jump_url": msg.jump_url,
                            "clean_content": msg.clean_content,
                            "created_at": msg.created_at.isoformat(),
                        },
                    )
        return MESSAGES

    @Server.route()
    async def start_cricket_api(self, data: ClientPayload) -> dict[str, Any] | None:
        url = data.url
        return await cricket_api(url) if url else None

    @Server.route()
    async def start_dbl_server(self, data: ClientPayload) -> dict[str, str]:
        if not self.bot.HAS_TOP_GG:
            return {"status": "error: top.gg not installed"}
        port = data.port or 1019
        end_point = data.end_point or "/dblwebhook"

        authentication = os.environ["TOPGG_AUTH"]
        try:
            self.bot.topgg_webhook.dbl_webhook(end_point, authentication)
            await self.bot.topgg_webhook.run(port)

            self.bot.DBL_SERVER_RUNNING = True
            return {"status": "ok"}
        except Exception as e:
            return {"status": f"error: {e}"}

    @Server.route()
    async def stop_dbl_server(self, data: ClientPayload) -> dict[str, str]:
        if self.bot.HAS_TOP_GG:
            await self.bot.topgg_webhook.close()
            self.bot.DBL_SERVER_RUNNING = False
            return {"status": "ok"}
        return {"status": "error: no top.gg webhook"}

    @Server.route()
    async def bot_dispatch(self, data: ClientPayload) -> dict[str, str]:
        raw = data.raw
        if not raw:
            return {"status": "error"}

        if event := raw.pop("event", None):
            self.bot.dispatch(event, raw)
            return {"status": "ok"}
        return {"status": "error"}

    @Server.route()
    async def guild_exists(self, data: ClientPayload) -> dict[str, bool]:
        if _id := getattr(data, "id", None):
            guild = self.bot.get_guild(int(_id))
        elif name := getattr(data, "name", None):
            guild = discord.utils.get(self.bot.guilds, name=name)
        else:
            return {"exists": False}

        return {"exists": guild is not None}

    @Server.route()
    async def guild_config(self, data: ClientPayload) -> dict[str, dict]:
        if _id := getattr(data, "id", None):
            guild = self.bot.get_guild(int(_id))
        elif name := getattr(data, "name", None):
            guild = discord.utils.get(self.bot.guilds, name=name)
        else:
            return {}

        if not guild:
            return {}

        d = await self.bot.guild_configurations.find_one({"_id": guild.id})
        return dict(d) if d else {}

    @Server.route()
    async def nsfw_links(self, data: ClientPayload) -> dict[str, list[str]]:
        limit: int | None = getattr(data, "limit", None)
        count: int | None = getattr(data, "count", None)

        tp: str | None = getattr(data, "type", None)
        gif: bool = getattr(data, "gif", True)
        if limit is None and count is None:
            return {"links": []}

        limit = max(1, min(100, limit or count))  # type: ignore
        return await self.get_nsfw_links(limit, tp, gif=gif)

    async def get_nsfw_links(self, limit: int, tp: str | None = None, *, gif: bool = True) -> dict[str, list[str]]:
        conditions = []
        if tp:
            table_name = "nsfw_links_grouped"
            porn_type = tp.lower()
            if porn_type not in self.bot.NSFW._sexdotcomgif._tags:  # SQL injection protection?
                porn_type = choice(self.bot.NSFW._sexdotcomgif._tags)
            conditions.append(f"type = '{porn_type}'")
        else:
            table_name = "nsfw_links"

        if gif:
            conditions.append("link LIKE '%gif%'")
        else:
            conditions.append("link NOT LIKE '%gif%'")

        where = " AND ".join(conditions)
        query = f"""
            SELECT link
            FROM   {table_name}
            WHERE  {where}
            ORDER BY RANDOM()
            LIMIT  {limit}
        """

        cur = await self.bot.sql.execute(query)
        rows = await cur.fetchall()
        return {"links": [row[0] for row in rows]}
