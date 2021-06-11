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

class MARS(commands.Cog, name='NASA'):
	#"""Mars Rovers Pictures"""
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['mrp'])
	async def mars(self, ctx, index:int = 0, _date:str = "2021-01-02"):
		"""Mars Rovers Pictures"""
		link = 'https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?earth_date='+ _date +'&api_key=qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC'

		req = requests.get(link)
		res = req.json()
		
		img = res['photos'][index]['img_src']
		date_ = res['photos'][index]['earth_date']
		status = res['photos'][index]['rover']['status'].capitalize()

		embed = discord.Embed(title="Mars Rover Photos", description=f"Status: {status}")
		embed.set_image(url=f"{img}")
		embed.set_footer(text=f"Date of imagery: {date_} | {ctx.author.name}")

		try:
			await ctx.send(embed=embed)
		except:
			await ctx.send(f'```\nHTTP Response: 404\n```{ctx.author.mention} can not find the image in `{_date}` database. Use some other date, in `YYYY-MM-DD` format.')

def setup(bot):
	bot.add_cog(MARS(bot))
