from discord.ext import commands

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
        data = await collection.find_one({'_id': ctx.guild.id})
        role = ctx.guild.get_role(data['mod_role'])
        if not role: 
            return False
        if role in ctx.author.roles:
            return True
        else:
            raise ex.NoModRole()

    return commands.check(predicate)

def is_cmd_enabled():
    async def predicate(ctx):
        collection = enable_disable[f'{ctx.guild.id}']
        data = collection.find_one({'_id': ctx.command.qualified_name})
        if not data:
            return True
        channels = data['channel']
        categories = data['category']
        server = data['server']
        if ctx.channel.id in channels:
            raise ex.CommandDisabledChannel()
        elif ctx.channel.category:
            if ctx.channel.category.id in categories:
                raise ex.CommandDisabledCategory()
        elif server is True:
            raise ex.CommandDisabledServer()
        else:
            return True
        data = collection.find_one({'_id': ctx.command.cog.qualified_name})
        if not data:
            return True
        channels = data['channel']
        categories = data['category']
        server = data['server']
        if ctx.channel.id in channels:
            raise ex.CommandDisabledChannel()
        elif ctx.channel.category:
            if ctx.channel.category.id in categories:
                raise ex.CommandDisabledCategory()
        elif server is True:
            raise ex.CommandDisabledServer()
        else:
            return True