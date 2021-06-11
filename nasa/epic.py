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

class EPIC(commands.Cog, name='NASA'):
	#'''Earth Polychromatic Imaging Camera'''
	def __init__(self, bot):
		self.bot = bot

	#https://epic.gsfc.nasa.gov/epic-archive/jpg/ file_name .jpg
	@commands.command(aliases=['earth'])
	async def epic(self, ctx, index:int = 0, _date:str = "2021-01-01"):
		'''Earth Polychromatic Imaging Camera'''
		s_link = 'https://epic.gsfc.nasa.gov/api/images.php?date=' + _date 
		req = requests.get(s_link)
		res = req.json()


		caption = res[index]['caption']
		im = res[index]['image']
		lat = res[index]['centroid_coordinates']['lat']
		lon = res[index]['centroid_coordinates']['lon']
		link = 'https://epic.gsfc.nasa.gov/epic-archive/jpg/'+ im +'.jpg'
		date__ = res[index]['date']
		embed = discord.Embed(title=f'{caption}', colour=discord.Colour.blue(), description=f'Lat: {lat} | Lon: {lon}')
		embed.set_image(url=f"{link}")
		embed.set_footer(text=f"Date of imagery: {date__} | {ctx.author.name}")

		try:
			await ctx.send(embed=embed)
		except:
			await ctx.send(f'```\nHTTP Response: 404\n```{ctx.author.mention} can not find the image in `{_date}` database. Use some other date, in `YYYY-MM-DD` format.')


def setup(bot):
	bot.add_cog(EPIC(bot))
