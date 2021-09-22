from discord.ext import commands
import discord
from utilities import exceptions as ex
from utilities.config import SUPER_USER

from utilities.database import parrot_db, enable_disable

collection = parrot_db['server_config']
c = parrot_db['ticket']

def is_guild_owner():
    async def predicate(ctx):
        if ctx.guild is not None and ctx.guild.owner_id == ctx.author.id:
            return True
        else:
            raise ex.NotGuildOwner()

    return commands.check(predicate)


def is_me():
    async def predicate(ctx):
        if ctx.message.author.id == SUPER_USER:  # !! Ritik Ranjan [*.*]#9230
            return True
        else:
            raise ex.NotMe()

    return commands.check(predicate)


def has_verified_role_ticket():
    async def predicate(ctx):
        data = await c.find_one({'_id': ctx.guild.id})
        if not data:
            return False
        data = await c.find_one({'_id': ctx.guild.id})
        roles = data['verified-roles']
        if not roles: return False
        for role in roles:
            if ctx.guild.get_role(role) in ctx.author.roles: return True
        else:
            raise ex.NoVerifiedRoleTicket()

    return commands.check(predicate)


def is_mod():
    async def predicate(ctx):
        data = await collection.find_one({'_id': ctx.guild.id})
        if not data:
            return False
        role = ctx.guild.get_role(data['mod_role'])
        if not role: 
            return False
        if role in ctx.author.roles:
            return True
        else:
            raise ex.NoModRole()

    return commands.check(predicate)

def can_run():
    async def predicate(ctx):
        data = await collection.find_one({'_id': ctx.author.id})
        if not data:
            return True
        if data['cmd']:
            return False
        if data['global']:
            return False
    return commands.check(predicate)

async def _can_run(ctx):
    if ctx.guild is not None:
        roles = set(ctx.author.roles)
        collection = enable_disable[f'{ctx.guild.id}']
        if data := await collection.find_one({'_id': ctx.command.qualified_name}):
            if ctx.channel.id in data['channel_in']: 
                return True
            for role in roles:
                if role.id in data['role_in']: 
                    return True
            for role in roles:
                if role.id in data['role_out']: 
                    return False
            if ctx.channel.id in data['channel_out']: 
                return False
            if data['server']: 
                return False
            if not data['server']: 
                return True
        if data := await collection.find_one({'_id': ctx.command.cog.qualified_name}):
            if ctx.channel.id in data['channel_in']: 
                return True
            for role in roles:
                if role.id in data['role_in']: 
                    return True
            for role in roles:
                if role.id in data['role_out']: 
                    return False
            if ctx.channel.id in data['channel_out']: 
                return False
            if data['server']: 
                return False
            if not data['server']: 
                return True
        if data := await collection.find_one({'_id': 'all'}):
            if ctx.channel.id in data['channel_in']: 
                return True
            for role in roles:
                if role.id in data['role_in']: 
                    return True
            for role in roles:
                if role.id in data['role_out']: 
                    return False
            if ctx.channel.id in data['channel_out']: 
                return False
            if data['server']: 
                return False
            if not data['server']: 
                return True
        return True
    return False