from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db
import discord, json, io


class GuildRoleEmoji(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['logging']

    def permissions_to_json(self, permissions) -> str:
        return json.dumps(dict(permissions), indent=4) if permissions else "{}"

    @Cog.listener()
    async def on_guild_role_create(self, role):
        if data := await self.collection.find_one({'_id': role.guild.id, 'on_role_create': {'$exists': True}}):
            webhook = discord.Webhook.from_url(data['on_role_create'], session=self.bot.session)
            if webhook:
                async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=5):
                    if entry.target.id == role.id:
                        content = f"""**Role Create**

`Name (ID)  :` **{role.name} [`{role.id}`]**
`Created At :` **{discord.utils.format_dt(role.created_at)}**
`Position   :` **{role.position}**
`Colour     :` **{role.color.to_rgb()} (RGB)**
`Mentionable:` **{role.mentionable}**
`Hoisted    :` **{role.hoist}**
`Bot Managed:` **{role.is_bot_managed()}**
`Integrated :` **{role.is_integration()}**
"""
                        fp = io.ByteIO(self.permissions_to_json(role.permissions).encode())
                        await webhook.send(
                            content=content, 
                            avatar_url=self.bot.user.avatar.url, 
                            username=self.bot.user.name,
                            file=discord.File(fp, filename='permissions.json')
                        )
                        break

    @Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if data := await self.collection.find_one({'_id': role.guild.id, 'on_role_delete': {'$exists': True}}):
            webhook = discord.Webhook.from_url(data['on_role_delete'], session=self.bot.session)
            if webhook:
                async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=5):
                    if entry.target.id == role.id:
                        content = f"""**Role Create**

`Name (ID)  :` **{role.name} [`{role.id}`]**
`Created At :` **{discord.utils.format_dt(role.created_at)}**
`Position   :` **{role.position}**
`Colour     :` **{role.color.to_rgb()} (RGB)**
`Mentionable:` **{role.mentionable}**
`Hoisted    :` **{role.hoist}**
`Bot Managed:` **{role.is_bot_managed()}**
`Integrated :` **{role.is_integration()}**
"""
                        fp = io.ByteIO(self.permissions_to_json(role.permissions).encode())
                        await webhook.send(
                            content=content, 
                            avatar_url=self.bot.user.avatar.url, 
                            username=self.bot.user.name,
                            file=discord.File(fp, filename='permissions.json')
                        )
                        break

        parrot_db = await self.bot.db('parrot_db')

        if data := await parrot_db['server_config'].find_one({'_id': role.guild.id}):
            if data['mod_role'] == role.id:
                await parrot_db['server_config'].update_one({'_id': role.guild.id}, {'$set': {'mod_role': None}})
            if data['mute_role'] == role.id:
                await parrot_db['server_config'].update_one({'_id': role.guild.id}, {'$set': {'mute_role': None}})

        if data := await parrot_db['global_chat'].find_one({'_id': role.guild.id}):
            if data['ignore-role'] == role.id:
                await parrot_db['global_chat'].update_one({'_id': role.guild.id}, {'$set': {'ignore_role': None}})

        if data := await parrot_db['telephone'].find_one({'_id': role.guild.id}):
            if data['pingrole'] == role.id:
                await parrot_db['telephone'].update_one({'_id': role.guild.id}, {'$set': {'pingrole': None}})

        if data := await parrot_db['ticket'].find_one({'_id': role.guild.id}):
            await parrot_db['ticket'].update_one({'_id': role.guild.id}, {'$pull': {'valid_roles': role.id, 'pinged_roles': role.id, 'verified_roles': role.id}})

    @Cog.listener()
    async def on_guild_role_update(self, before, after):
        pass

    @Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        pass


def setup(bot):
    bot.add_cog(GuildRoleEmoji(bot))
