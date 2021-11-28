from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db

import discord, time, io, json

log = parrot_db['logging']
server_config = parrot_db['server_config']


class GuildChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = log

    def _overwrite_to_json(self, overwrites):
        try:
            over = {
                f"{str(target.name)} ({'Role' if type(target) is discord.Role else 'Member'})": overwrite._values for target, overwrite in overwrites.items()
            }
            return json.dumps(over, indent=4)
        except Exception:
            return "{}"
    
    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if data := await self.collection.find_one({'_id': channel.guild.id, 'on_channel_delete': {'$exists': True}}):
            webhook = discord.Webhook.from_url(data['on_channel_delete'], session=self.bot.session)
            if webhook:
                channel_type = str(channel.type)
                TYPE = channel_type.replace('_', ' ').title() + " Channel"
                async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=5):
                    if entry.target.id == channel.id:
                        
                        reason = entry.reason or None       # Fact is this thing has to be implemented
                        user = entry.user or "UNKNOWN#0000" # If the action is too old
                        deleted_at = entry.created_at       # The logs can't be proceeded. I dont know why
                        content = f"""**Channel Delete Event**
                
`Name (ID) :` **{channel.name} [`{TYPE}`] ({channel.id})**
`Created at:` **<t:{int(channel.created_at.timestamp())}>**
`Position  :` **{channel.position}**
`Category  :` **{channel.category.mention if channel.category else None}**
`Caterogy Synced?:` **{channel.permissions_synced}**
`Reason    :` **{reason if reason else 'No reason provided'}**
`Deleted at:` **{discord.utils.format_dt(deleted_at) if deleted_at else 'Not available'}**
`Deleted by:` **{user}**
"""                     
                        break
                fp = io.BytesIO(self._overwrite_to_json(channel.overwrites).encode())
                await webhook.send(
                    content=content, 
                    avatar_url=self.bot.user.avatar.url, 
                    username=self.bot.user.name,
                    file=discord.File(fp, filename='overwrites.json')
                )

    @Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if data := await self.collection.find_one({'_id': channel.guild.id, 'on_channel_create': {'$exists': True}}):
            webhook = discord.Webhook.from_url(data['on_channel_create'], session=self.bot.session)
            if webhook:
                embed = discord.Embed(title='Channel Create Event', color=self.bot.color)
                channel_type = str(channel.type)
                TYPE = channel_type.replace('_', ' ').title() + " Channel"
                async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=5):
                    if entry.target.id == channel.id:
                        reason = entry.reason or None
                        user = entry.user or "UNKNOWN#0000"
                        entryID = entry.id
                        content = f"""**Channel Create Event**
                
`Name (ID) :` **{channel.name} [`{TYPE}`] ({channel.id})**
`Created at:` **<t:{int(channel.created_at.timestamp())}>**
`Position  :` **{channel.position}**
`Category  :` **{channel.category.mention if channel.category else None}**
`Caterogy Synced?:` **{channel.permissions_synced}**
`Reason    :` **{reason if reason else 'No reason provided'}**
`Entry ID  :` **{entryID if entryID else None}**
`Deleted by:` **{user}**
"""
                fp = io.BytesIO(self._overwrite_to_json(channel.overwrites).encode())
                await webhook.send(
                    content=content, 
                    avatar_url=self.bot.user.avatar.url, 
                    username=self.bot.user.name,
                    file=discord.File(fp, filename='overwrites.json')
                )
            if channel.permissions_for(channel.guild.me).manage_channels and channel.permissions_for(channel.guild.default_role).send_messages and channel.permissions_for(channel.guild.me).manage_roles:
                if data := await server_config.find_one({'_id': channel.guild.id}):
                    if data['muted_role']:
                        if role := channel.guild.get_role(data['muted_role']):
                            await channel.edit(role, send_messages=False, add_reactions=False)
                    else:
                        if role := discord.utils.get(channel.guild.roles, name="Muted"):
                            await channel.edit(role, send_messages=False, add_reactions=False)

    @Cog.listener()
    async def on_guild_channel_update(self, before, after):
        pass

    @Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        pass

    @Cog.listener()
    async def on_guild_integrations_update(self, guild):
        pass

    @Cog.listener()
    async def on_webhooks_update(self, channel):
        pass

    @Cog.listener()
    async def on_reaction_clear_emoji(self, reaction):
        pass

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload):
        pass


def setup(bot):
    bot.add_cog(GuildChannel(bot))
