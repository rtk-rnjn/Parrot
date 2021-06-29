from discord.ext import commands

from utilities import exceptions as ex
from utilities.config import SUPER_USER

from database.ticket import collection as c, ticket_on_join
from database.premium import collection_guild as collection_pre_guild
from database.premium import collection_user as collection_pre_user
from database.server_config import collection, guild_join

def is_guild_owner():
		def predicate(ctx):
				if ctx.guild is not None and ctx.guild.owner_id == ctx.author.id:
						return True
				else:
						raise ex.NotGuildOwner()

		return commands.check(predicate)


def is_me():
		def predicate(ctx):
				if ctx.message.author.id == SUPER_USER:  # !! Ritik Ranjan [*.*]#9230
						return True
				else:
						raise ex.NotMe()

		return commands.check(predicate)


def is_user_premium():
		def predicate(ctx):
				user = collection_pre_user.find({"_id": ctx.message.author.id})
				if not user:
						raise ex.NotPremiumUser()
				elif user:
						return True

		return commands.check(predicate)


def is_guild_premium():
		def predicate(ctx):
				guild = collection_pre_guild.find({"_id": ctx.guild.id})
				if guild:
						return True
				elif not guild:
						raise ex.NotPremiumGuild()


def user_premium_cd():
		def predicate(ctx):
				user = collection_pre_user.find({"_id": ctx.message.author.id})
				if user:
						return commands.cooldown(0, 0, commands.BucketType.member)
				else:
						return commands.cooldown(1, 5, commands.BucketType.member)

		return commands.check(predicate)


def mod_cd():
		def predicate(ctx):
				guild = collection_pre_guild.find({"_id": ctx.guild.id})
				if guild:
						return commands.cooldown(0, 0, commands.BucketType.guild)
				else:
						return commands.cooldown(3, 30, commands.BucketType.guild)

		return commands.check(predicate)

 # [{"cmd": ctx.command.name, "channel": []}]
def id_cmd_disabled():
		def predicate(ctx):
				data = collection.find({"_id": ctx.guild.id})
				if ctx.command.name in data['disabled_cmds']:
						raise commands.DisabledCommand()
				else:
						return True

		return commands.check(predicate)


def id_cog_disabled():
		def predicate(ctx):
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
				return commands.check_any(commands.has_any_role(*roles), commands.has_permissions(administrator=True))

		return commands.check(predicate)


def is_mod():
		async def predicate(ctx):
				if not collection.find_one({'_id': ctx.guild.id}): await guild_join(ctx.guild.id)
				data = collection.find_one({'_id': ctx.guild.id})
				role_id = data['mod_role']
				return commands.has_role(role_id)
