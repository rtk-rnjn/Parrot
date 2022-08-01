from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

import discord
from api import cricket_api
from core import Cog, Parrot
from discord.ext.ipc import server
from wavelink.ext import spotify


class IPCRoutes(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    def _overwrite_to_json(
        self,
        overwrites: Dict[Union[discord.User, discord.Role], discord.PermissionOverwrite],
    ) -> Dict[str, Union[str, Optional[bool]]]:
        try:
            return {
                str(target.id): overwrite._values  # type: ignore
                for target, overwrite in overwrites.items()
            }
        except Exception:
            return {}

    @server.route()
    async def echo(self, data: server.IpcServerResponse) -> Dict[str, Any]:
        return data.to_json()

    @server.route()
    async def db_exec_find_one(self, data: server.IpcServerResponse) -> Dict[str, Any]:
        db = data.db
        collection = data.collection

        query = getattr(data, "query", {})
        projection = getattr(data, "projection", {})

        return await self.bot.mongo[db][collection].find_one(query, projection)

    @server.route()
    async def db_exec_update_one(self, data: server.IpcServerResponse) -> Any:
        db: str = data.db
        collection: str = data.collection

        query: Dict[str, Any] = getattr(data, "query", {})
        update: Dict[str, Any] = getattr(data, "update", {})
        upsert: bool = getattr(data, "upsert", False)

        return await self.bot.mongo[db][collection].update_one(query, update, upsert=upsert)

    @server.route()
    async def commands(self, data: server.IpcServerResponse) -> List[Dict[str, str]]:
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
            for command in cmds
        ]

    @server.route()
    async def guilds(self, data: server.IpcServerResponse) -> List[Dict[str, Any]]:
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
                    "discriminator": guild.owner.discriminator,
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
                        "discriminator": member.discriminator,
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
                        "slowmod_delay": thread.slowmod_delay,
                        "archived": thread.archived,
                        "locked": thread.locked,
                    }
                    for thread in guild.threads
                ],
            }
            for guild in guilds
        ]

    @server.route()
    async def users(self, data: server.IpcServerResponse) -> List[Dict[str, Any]]:
        if _id := getattr(data, "id", None):
            users = [self.bot.get_user(_id)]
        elif (name := getattr(data, "name", None)) and (
            discriminator := getattr(data, "discriminator", None)
        ):
            users = [discord.utils.get(self.bot.users, name=name, discriminator=discriminator)]
        else:
            users = self.bot.users

        return [
            {
                "id": user.id,
                "name": user.name,
                "discriminator": user.discriminator,
                "avatar_url": user.display_avatar.url,
                "bot": user.bot,
                "created_at": user.created_at.isoformat(),
                "system": user.system,
            }
            for user in users
        ]

    @server.route()
    async def get_message(self, data: server.IpcServerResponse) -> Dict[str, Any]:
        channel = self.bot.get_channel(data.channel_id)
        message = await self.bot.get_or_fetch_message(
            channel,
            data.message_id,
            partial=False,
        )
        if not isinstance(message, discord.Message):
            return {}

        return {
            "id": message.id,
            "author": {
                "id": message.author.id,
                "name": message.author.name,
                "discriminator": message.author.discriminator,
                "avatar_url": message.author.display_avatar.url,
                "bot": message.author.bot,
                "system": message.author.system,
            },
            "content": message.content,
            "embeds": [embed.to_dict() for embed in message.embeds],
        }

    @server.route()
    async def announce_global(self, data: server.IpcServerResponse) -> List[Dict[str, str]]:
        MESSAGES = []
        async for webhook in self.bot.mongo.parrot_db.global_chat.find(
            {"webhook": {"$exists": True}}, {"webhook": 1, "_id": 0}
        ):
            hook = webhook["webhook"]
            if hook:
                try:
                    webhook = discord.Webhook.from_url(f"{hook}", session=self.bot.http_session)
                    msg = await webhook.send(
                        content=data.content[:1990],
                        username=f"{data.author_name}#{data.discriminator}",
                        avatar_url=data.avatar_url,
                        allowed_mentions=discord.AllowedMentions.none(),
                        wait=True,
                    )
                except discord.NotFound:
                    await self.bot.mongo.parrot_db.global_chat.delete_one(
                        {"webhook": hook}
                    )  # all hooks are unique
                except discord.HTTPException:
                    pass
                else:
                    MESSAGES.append(
                        {
                            "jump_url": msg.jump_url,
                            "clean_content": msg.clean_content,
                            "created_at": msg.created_at.isoformat(),
                        }
                    )
        return MESSAGES

    @server.route()
    async def start_wavelink_nodes(self, data: server.IpcServerResponse) -> Dict[str, str]:
        host = data.host
        port = data.port
        password = data.password
        try:
            if hasattr(self.bot, "wavelink"):
                await self.bot.wavelink.create_node(
                    bot=self.bot,
                    host=host,
                    port=port,
                    password=password,
                    identifier="MAIN",
                    spotify_client=spotify.SpotifyClient(
                        client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
                        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
                    ),
                )
        except Exception as e:
            return {"status": f"error: {e}"}
        else:
            return {"status": "ok"}

    @server.route()
    async def start_cricket_api(self, data: server.IpcServerResponse) -> Optional[Dict[str, Any]]:
        url = data.url
        if not url:
            return None

        return cricket_api(url)

    @server.route()
    async def start_dbl_server(self, data: server.IpcServerResponse) -> Dict[str, str]:
        port = data.port or 1019
        end_point = data.end_point or "/dblwebhook"

        authentication = os.environ["TOPGG_AUTH"]
        try:
            self.bot.topgg_webhook.dbl_webhook(end_point, authentication)
            self.bot.topgg_webhook.run(port)
        except Exception as e:
            return {"status": f"error: {e}"}
        else:
            return {"status": "ok"}
    
    @server.route()
    async def stop_dbl_server(self, data: server.IpcServerResponse) -> Dict[str, str]:
        self.bot.topgg_webhook.close()
        return {"status": "ok"}