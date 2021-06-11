#API Key: qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC

#Account Email: ritik0ranjan@gmail.com
#Account ID: a37c9407-bed3-4379-a8ef-30abb1a0447c
#import os
#os.sys('pip install pillow')
#from PIL import Image

from datetime import datetime
import discord
import json
from discord.ext import commands
import requests
import urllib.parse
import json

class FindAsteroidID(commands.Cog, name='NASA'):
	#'''Find any asteroid in the space by ID. "[p]help findaid" for syntax'''
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['findaid', 'asteroidid'])
	async def findasteroididid(self, ctx, _id:int):
		'''Find any asteroid in the space by ID. "$help findaid" for syntax'''
		link = 'https://api.nasa.gov/neo/rest/v1/neo/' + str(_id) + '?api_key=qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC'

		try:
			req = requests.get(link)
			res = req.json()
		except:
			await ctx.send(f"```\nHTTP Response: 404\n```{ctx.author.mention} Asteroid ID invalid!!")
		name = res['name']
		link_self = res['nasa_jpl_url']

		dia = round(res['estimated_diameter']['meters']['estimated_diameter_min'])
		danger = res['is_potentially_hazardous_asteroid']
		sentry = res['is_sentry_object']
		orbitaldata = res['orbital_data']['orbit_class']['orbit_class_description']
		orbital_ran = res['orbital_data']['orbit_class']['orbit_class_range']
		last_obs = res['orbital_data']['last_observation_date']
		orbit_sp = res['close_approach_data'][0]['relative_velocity']['kilometers_per_hour']
		orbital_p = res['close_approach_data'][0]['orbiting_body']
		embed = discord.Embed(title = f"Asteroid Name: {name}", url = f"{link_self}", description=f"{orbitaldata}\nRange: {orbital_ran}")
		embed.add_field(name="Estimated Diameter:", value=f"{dia} M", inline=True)
		embed.add_field(name="Is Danger?", value=f"{danger}", inline=True)
		embed.add_field(name="Is sentry?", value=f"{sentry}", inline=True)
		embed.add_field(name="Relative velocity:", value=f"{orbit_sp} KM/hr", inline=True)
		embed.add_field(name="Orbiting:", value=f"{orbital_p}", inline=True)
		embed.add_field(name="Last observation date:", value=f"{last_obs}", inline=True)
		embed.set_thumbnail(url='https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png')
		embed.set_footer(text=f"{ctx.author.name}")

		await ctx.send(embed=embed)



def setup(bot):
	bot.add_cog(FindAsteroidID(bot))