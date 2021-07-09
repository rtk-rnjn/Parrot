from discord.ext import commands

from utilities import exceptions as ex
from utilities.config import SUPER_USER

from database.ticket import collection as c, ticket_on_join
from database.premium import collection_guild as collection_pre_guild
from database.premium import collection_user as collection_pre_user
from database.server_config import collection, guild_join


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


def is_user_premium():
    async def predicate(ctx):
        user = collection_pre_user.find({"_id": ctx.message.author.id})
        if not user:
            raise ex.NotPremiumUser()
        elif user:
            return True

    return commands.check(predicate)


def is_guild_premium():
    async def predicate(ctx):
        guild = collection_pre_guild.find({"_id": ctx.guild.id})
        if guild:
            return True
        elif not guild:
            raise ex.NotPremiumGuild()


def user_premium_cd():
    async def predicate(ctx):
        user = collection_pre_user.find({"_id": ctx.message.author.id})
        if user:
            return commands.cooldown(0, 0, commands.BucketType.member)
        else:
            return commands.cooldown(1, 5, commands.BucketType.member)

    return commands.check(predicate)


def mod_cd():
    async def predicate(ctx):
        guild = collection_pre_guild.find({"_id": ctx.guild.id})
        if guild:
            return commands.cooldown(0, 0, commands.BucketType.guild)
        else:
            return commands.cooldown(3, 30, commands.BucketType.guild)

    return commands.check(predicate)


# [{"cmd": ctx.command.name, "channel": []}]
def id_cmd_disabled():
    async def predicate(ctx):
        data = collection.find({"_id": ctx.guild.id})
        if ctx.command.name in data['disabled_cmds']:
            raise commands.DisabledCommand()
        else:
            return True

    return commands.check(predicate)


def id_cog_disabled():
    async def predicate(ctx):
        data = collection.find({"_id": ctx.guild.id})
        if ctx.command.name in data['disabled_cogs']:
            raise commands.DisabledCommand()
        else:
            return True

    return commands.check(predicate)


def has_verified_role_ticket():
    async def predicate(ctx):
        data = c.find_one({'_id': ctx.guild.id})
        if not data: await ticket_on_join(ctx.guild.id)
        data = c.find_one({'_id': ctx.guild.id})
        roles = data['verified-roles']
        for role in roles:
            if ctx.guild.get_role(role) in ctx.author.roles: return True
        else:
            raise ex.NoVerifiedRoleTicket()

    return commands.check(predicate)


def is_mod():
    async def predicate(ctx):
        if not collection.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)
        data = collection.find_one({'_id': ctx.guild.id})
        role = ctx.guild.get_role(data['mod_role'])
        if role in ctx.author.roles:
            return True
        else:
            raise ex.NoModRole()

    return commands.check(predicate)


def can_giveaway():
    async def predicate(ctx):
        if not collection.find_one({'_id': ctx.guild.id}):
            await guild_join(ctx.guild.id)
        data = collection.find_one({'_id': ctx.guild.id})
        role_id = data['giveaway_role']
        if role_id in [role.id for role in ctx.author.roles]: return True
        elif 'giveaway' in [role.name.lower() for role in ctx.author.roles]:
            return True
        elif 'giveaway manager' in [
                role.name.lower() for role in ctx.author.roles
        ]:
            return True
        else:
            raise ex.NoGiveawayRole()

    return commands.check(predicate)
