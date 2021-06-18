import datetime, time
from discord_slash import SlashCommand
import jishaku, sys, discord, os
from keep_alive import keep_alive
from discord.ext import commands, tasks
## something
client = commands.AutoShardedBot(command_prefix=commands.when_mentioned_or("$"), case_insensitive=True, intents=discord.Intents.all(), strip_after_prefix=True, owner_ids=[741614468546560092, 813647101392846848], member_cache_flags=discord.MemberCacheFlags.from_intents(discord.Intents.all()), shard_count=3)

slash = SlashCommand(client, sync_commands=True, override_type=True)

client.strip_after_prefix = True


@client.event
async def on_ready():
		print('Bot is ready to take commands. Status OK')
		

# COGS ADDITIONS

cogs = [
		'cogs.ult', 'cogs.mod', 'cogs.fun', 'cogs.memegen', 'cogs.ticket',
		'cogs.mis', 'cogs.nsfw', 'rtfm.queries', 'cogs.help', 'cogs.mee6', 
		'cogs.applymod', 'cogs.telephone', 'cogs.unbiboat', 'cogs.gchat.setup', 'cogs.gchat.on_message',
		'cogs.leveling.on_message', 'cogs.leveling.leaderboard',
		'cogs.events.on_command_error', 'cogs.events.on_member_join', 'cogs.events.on_guild_join',
		'cogs.economy',
		'cogs.nasa.nasasearch', 'cogs.nasa.nasa', 'cogs.nasa.mars', 'cogs.nasa.findasteroidid', 'cogs.nasa.findasteroid', 'cogs.nasa.epic', 'cogs.nasa.apod',
		'jishaku'
]

ini = time.time()
if __name__ == '__main__':


		print("\nAdding cogs...\n")

		for _temp in cogs:
				try:
						client.load_extension(_temp)
						print(f"{_temp} loaded")
						
				except Exception as e:
						print(f'Error loading in {_temp}', file=sys.stderr)
						print(e)

						
fin = time.time() 

keep_alive()

client.run(os.environ['TOKEN'])
