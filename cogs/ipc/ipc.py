from __future__ import annotations

import os
from typing import Any
import async_timeout

import wavelink
from wavelink.ext import spotify

import discord
from api import cricket_api
from core import Cog, Parrot
from discord.ext.ipc.server import Server
from discord.ext.ipc.objects import ClientPayload


class IPCRoutes(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ON_TESTING = False

    def _overwrite_to_json(
        self,
        overwrites: dict[discord.User | discord.Role, discord.PermissionOverwrite],
    ) -> dict[str, str | bool | None]:
        try:
            return {str(target.id): overwrite._values for target, overwrite in overwrites.items()}  # type: ignore
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
    async def commands(self, data: ClientPayload) -> list[dict[str, Any]]:
        if name := getattr(data, "name", None):
            cmds = [self.bot.get_command(name)]
        else:
            cmds = list(self.bot.commands)

        return [
            {
                "name": command.qualified_name,
                "aliases": command.aliases,
                "description": command.description,
                "usage": command.signature,
                "enabled": command.enabled,
                "hidden": command.hidden,
                "cog": command.cog_name,
            }
            for command in cmds if command is not None
        ]

    @Server.route()
    async def guilds(self, data: ClientPayload) -> list[dict[str, Any]]:
        if _id := getattr(data, "id", None):
            guilds = [self.bot.get_guild(_id)]
        elif name := getattr(data, "name", None):
            guilds = [discord.utils.get(self.bot.guilds, name=name)]
        else:
            guilds = self.bot.guilds

        return [
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
                "icon_url": guild.icon.url if guild.icon is not None else None,
                "member_count": guild.member_count,
                "channels": [
                    {
                        "id": channel.id,
                        "name": channel.name,
                        "type": str(channel.type),
                        "position": channel.position,
                        "overwrites": self._overwrite_to_json(channel.overwrites),
                    }
                    for channel in guild.channels
                ],
                "roles": [
                    {
                        "id": role.id,
                        "name": role.name,
                        "color": role.color.value,
                        "position": role.position,
                        "permissions": role.permissions.value,
                        "managed": role.managed,
                        "hoist": role.hoist,
                        "mentionable": role.mentionable,
                    }
                    for role in guild.roles
                ],
                "members": [
                    {
                        "id": member.id,
                        "name": member.name,
                        "avatar_url": member.display_avatar.url,
                        "bot": member.bot,
                        "roles": [role.id for role in member.roles],
                        "joined_at": member.joined_at.isoformat(),
                        "display_name": member.display_name,
                        "nick": member.nick,
                        "color": member.color.value,
                    }
                    for member in guild.members
                ],
                "emojis": [
                    {
                        "id": emoji.id,
                        "name": emoji.name,
                        "url": emoji.url,
                        "roles": [role.id for role in emoji.roles],
                        "require_colons": emoji.require_colons,
                        "managed": emoji.managed,
                        "animated": emoji.animated,
                        "available": emoji.available,
                    }
                    for emoji in guild.emojis
                ],
                "threads": [
                    {
                        "id": thread.id,
                        "name": thread.name,
                        "created_at": thread.created_at.isoformat(),
                        "owner_id": thread.owner_id,
                        "parent_id": thread.parent_id,
                        "slowmod_delay": thread.slowmode_delay,
                        "archived": thread.archived,
                        "locked": thread.locked,
                    }
                    for thread in guild.threads
                ],
            }
            for guild in guilds if guild is not None
        ]

    @Server.route()
    async def users(self, data: ClientPayload) -> list[dict[str, Any]]:
        if _id := getattr(data, "id", None):
            users = [self.bot.get_user(_id)]
        elif name := getattr(data, "name", None):
            users = [discord.utils.get(self.bot.users, name=name)]
        else:
            users = self.bot.users

        return [
            {
                "id": user.id,
                "name": user.name,
                "avatar_url": user.display_avatar.url,
                "bot": user.bot,
                "created_at": user.created_at.isoformat(),
                "system": user.system,
            }
            for user in users if user is not None
        ]

    @Server.route()
    async def get_message(self, data: ClientPayload) -> dict[str, Any]:
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
                    "system": message.author.system,
                },
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
    async def start_wavelink_nodes(self, data: ClientPayload) -> dict[str, str]:
        if self.bot.ON_HEROKU:
            return {"status": "error: cannot start wavelink on heroku"}
        host = data.host
        port = data.port
        password = data.password
        try:
            async with async_timeout.timeout(5):
                if hasattr(self.bot, "wavelink"):
                    node: wavelink.Node = wavelink.Node(uri=f"{host}:{port}", password=password, id="MAIN")
                    await self.bot.wavelink.connect(
                        client=self.bot,
                        nodes=[node],
                        spotify=spotify.SpotifyClient(
                            client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
                            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
                        ),
                    )
            self.bot.WAVELINK_NODE_READY = True
        except Exception as e:
            return {"status": f"error: {e}"}

        return {"status": "ok"}

    @Server.route()
    async def start_cricket_api(self, data: ClientPayload) -> dict[str, Any] | None:
        url = data.url
        return await cricket_api(url) if url else None

    @Server.route()
    async def start_dbl_server(self, data: ClientPayload) -> dict[str, str]:
        if self.bot.HAS_TOP_GG:
            port = data.port or 1019
            end_point = data.end_point or "/dblwebhook"

            authentication = os.environ["TOPGG_AUTH"]
            try:
                self.bot.topgg_webhook.dbl_webhook(end_point, authentication)
                self.bot.topgg_webhook.run(port)

                self.bot.DBL_SERVER_RUNNING = True
                return {"status": "ok"}
            except Exception as e:
                return {"status": f"error: {e}"}

        return {"status": "error: top.gg not installed"}

    @Server.route()
    async def stop_dbl_server(self, data: ClientPayload) -> dict[str, str]:
        if self.bot.HAS_TOP_GG:
            self.bot.topgg_webhook.close()
            self.bot.DBL_SERVER_RUNNING = False
            return {"status": "ok"}
        return {"status": "error: no top.gg webhook"}
