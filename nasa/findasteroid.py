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

class FindAsteroid(commands.Cog, name='NASA'):
	#'''You can literally find any asteroid in the space by date. "[p]help finda" for syntax'''
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['finda', 'asteroid'])
	async def findasteroid(self, ctx, start:str, end:str, index:int = 0):
		'''You can literally find any asteroid in the space by date. "$help finda" for syntax'''
		link = 'https://api.nasa.gov/neo/rest/v1/feed?start_date=' + start + '&end_date=' + end + '&api_key=qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC'
		req = requests.get(link)
		res = req.json()

		link_self = res['near_earth_objects'][end][index]['nasa_jpl_url']

		tasteroid = res['element_count']

		name_end = res['near_earth_objects'][end][index]['name']
		id_end = res['near_earth_objects'][end][index]['neo_reference_id']
		dia = round(float(res['near_earth_objects'][end][index]['estimated_diameter']['meters']['estimated_diameter_min']))
		danger = res['near_earth_objects'][end][index]['is_potentially_hazardous_asteroid']
		approach_date = res['near_earth_objects'][end][index]['close_approach_data'][0]['close_approach_date']
		velocity = res['near_earth_objects'][end][index]['close_approach_data'][0]['relative_velocity']['kilometers_per_hour']
		miss_dist = res['near_earth_objects'][end][index]['close_approach_data'][0]['miss_distance']['kilometers']
		orbiting = res['near_earth_objects'][end][index]['close_approach_data'][0]['orbiting_body']
		is_sentry_object = res['near_earth_objects'][end][index]['is_sentry_object']

		embed = discord.Embed(title=f"Total Asteroid count: {tasteroid}", description=f"Retriving data from {start} to {end}", url=f"{link_self}")
		embed.add_field(name="Asteroid Name:", value=f"{name_end}", inline=True)
		embed.add_field(name="Asteroid ID:", value=f"{id_end}", inline=True)
		embed.add_field(name="Estimated Diameter:", value=f"{dia} M", inline=True)
		embed.add_field(name="Is Danger?", value=f"{danger}", inline=True)
		embed.add_field(name="Approach Date:", value=f"{approach_date}", inline=True)
		embed.add_field(name="Relative velocity:", value=f"{velocity} KM/hr", inline=True)
		embed.add_field(name="Miss Distance:", value=f"{miss_dist} KM", inline=True)
		embed.add_field(name="Orbiting:", value=f"{orbiting}", inline=True)
		embed.add_field(name="Is sentry?", value=f"{is_sentry_object}", inline=True)
		embed.set_thumbnail(url='https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png')
		embed.set_footer(text=f"{ctx.author.name}")

		await ctx.send(embed=embed)


def setup(bot):
	bot.add_cog(FindAsteroid(bot))
