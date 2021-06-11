import datetime, time
from discord_slash import SlashCommand
import asyncio, jishaku, traceback, sys, __main__, discord, os
from keep_alive import keep_alive
from discord.ext import commands, tasks
## something
client = commands.AutoShardedBot(command_prefix=commands.when_mentioned_or("$"), case_insensitive=True, intents=discord.Intents.all(), strip_after_prefix=True, owner_ids=[741614468546560092, 813647101392846848], member_cache_flags=discord.MemberCacheFlags.from_intents(discord.Intents.all()), shard_count=3)

slash = SlashCommand(client, sync_commands=True, override_type=True)

client.strip_after_prefix = True


@client.event
async def on_ready():
		print('Bot is ready to take commands. Status OK')
		print(discord.version_info)
		print(discord.__version__)
		await client.get_channel(819858263767908392).connect()
		await client.get_channel(843694135571120129).send(f'> Successfully added cogs: :white_check_mark:    {len(temp_success)}\n'
													f'> Falied to add cogs: :negative_squared_cross_mark: {len(temp_error) if temp_error else "None"}\n'
						    f'> Today at: {datetime.datetime.utcnow()}\n'
						    f'> Time Taken: {fin-ini}s\n> Owner ID: 741614468546560092\n'
						    f'> Connected to?: 819858263767908392\n'
						    f'> Server: {len(client.guilds)}\n'
						    f'> Users: {len(client.users)}')

		await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, status=discord.Status.dnd, name="$help"))

# COGS ADDITIONS

cogs = [
		'cogs.ult', 'cogs.mod', 'cogs.fun', 'cogs.memegen', 'cogs.ticket',
		'cogs.mis', 'cogs.nsfw', 'rtfm.queries', 'cogs.help', 'cogs.mee6', 
		'cogs.applymod', 'telephone.telephone', 'cogs.unbiboat', 'gchat.setup', 'gchat.on_message',
		'leveling.on_message', 'leveling.leaderboard',
		'events.on_command_error', 'events.on_member_join', 'events.on_guild_join',
		'economy.balance', 'economy.beg', 'economy.deposit', 'economy.slots', 'economy.steal', 'economy.withdraw',
		'nasa.nasasearch', 'nasa.nasa', 'nasa.mars', 'nasa.findasteroidid', 'nasa.findasteroid', 'nasa.epic', 'nasa.apod',
		'jishaku'
]

ini = time.time()
if __name__ == '__main__':

		temp_success = []
		temp_error = []

		print("\nAdding cogs...\n")

		for _temp in cogs:
				try:
						client.load_extension(_temp)
						print(f"{_temp} loaded")
						temp_success.append(f":white_check_mark: `{datetime.datetime.utcnow()}` {_temp}\n")

				except Exception as e:
						print(f'Error loading in {_temp}', file=sys.stderr)
						temp_error.append(f":negative_squared_cross_mark: `{datetime.datetime.utcnow()}` {_temp}```\n{e}\n```\n")
						traceback.print_exc()
fin = time.time() 

keep_alive()

client.run(os.environ['TOKEN'])
print(f"Session closed at {datetime.datetime.utcnow()}")
