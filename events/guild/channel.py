from __future__ import annotations

from core import Cog, Parrot
from utilities.database import parrot_db

import discord, time, io, json

log = parrot_db['logging']


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
            if not webhook: return # webhook deleted
            embed = discord.Embed(title='Channel Delete Event', color=self.bot.color)
            channel_type = str(channel.type)
            TYPE = channel_type.replace('_', ' ').title() + " Channel"

            data = [
                ("Name", f"{channel.name} ({TYPE})"),
                ("Created at", f"<t:{int(channel.created_at.timestamp())}>"),
                ("Position", f"{channel.position}"),
                ("Category", f"{channel.category.mention if channel.category else None}"),
                ("Synced with Category?", f"{channel.permissions_synced}")
            ]
            
            for name, value in data: embed.add_field(name=name, value=value, inline=True)
            async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
                reason = entry.reason or None       # Fact is this thing has to be implemented
                user = entry.user or "UNKNOWN#0000" # If the action is too old
                deleted_at = entry.created_at       # The logs can't be proceeded. I dont know why
            
            embed.set_footer(text=f"ID: {channel.id}")
            embed.add_field(name="Deleted at", value=f"{discord.utils.format_dt(deleted_at) if deleted_at else 'Not available'}", inline=True)
            embed.description = f"**Reason:** `{reason if reason else 'No reason provided'}`\n**User:** `{user}`"
            
            fp = io.BytesIO(self._overwrite_to_dict(channel.overwrites).encode())
            await webhook.send(
                content=f"**Channel Deleted**", 
                avatar_url=self.bot.user.avatar.url, 
                username=self.bot.user.name,
                file=discord.File(fp, filename='overwrites.json')
            )

    @Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if data := await self.collection.find_one({'_id': channel.guild.id, 'on_channel_create': {'$exists': True}}):
            webhook = discord.Webhook.from_url(data['on_channel_create'], session=self.bot.session)
            if not webhook: return
            embed = discord.Embed(title='Channel Create Event', color=self.bot.color)
            channel_type = str(channel.type)
            TYPE = channel_type.replace('_', ' ').title() + " Channel"
            data = [
                ("Name", f"{channel.name} (`{TYPE}`)"),
                ("Created at", f"<t:{int(channel.created_at.timestamp())}>"),
                ("Position", f"{channel.position}"),
                ("Category", f"{channel.category.mention if channel.category else 'None'}"),
                ("Synced with Category?", f"{channel.permissions_synced}"),
            ]
            async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
                reason = entry.reason or None
                user = entry.user or "UNKNOWN#0000"
                entryID = entry.id

            embed.set_footer(text=f"ID: {channel.id}")
            embed.add_field(name="Entry ID", value=f"{entryID}", inline=True)
            embed.description = f"**Reason:** `{reason if reason else 'No reason provided'}`\n**User:** `{user}`"
            
            fp = io.BytesIO(self._overwrite_to_dict(channel.overwrites).encode())
            await webhook.send(
                content=f"**Channel Created**", 
                avatar_url=self.bot.user.avatar.url, 
                username=self.bot.user.name,
                file=discord.File(fp, filename='overwrites.json')
            )
        if channel.permissions_for(channel.guild.me).manage_channels:
            pass # TODO: TO MAKE A OVERWRITE FOR MUTED ROLE

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
