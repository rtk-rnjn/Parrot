#API Key: qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC

#Account Email: ritik0ranjan@gmail.com
#Account ID: a37c9407-bed3-4379-a8ef-30abb1a0447c
#import os
#os.sys('pip install pillow')
#from PIL import Image

import discord

from discord.ext import commands
import requests

class APOD(commands.Cog, name='NASA'):
	#'''Asteroid Picture of the Day'''
	def __init__(self, bot):
		self.bot = bot


	@commands.command()
	async def apod(self, ctx):
		'''Asteroid Picture of the Day'''
		link = 'https://api.nasa.gov/planetary/apod?api_key=qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC'
		req = requests.get(link)
		res = req.json()

		title = res['title']
		expln = res['explanation']
		#authr = res['copyright']
		date_ = res['date']
		if res['media_type'] == "image":
			image = res['media_type']

		embed = discord.Embed(title=f"Astronomy Picture of the Day: {title}", description=f"{expln}")
		if res['media_type'] == "image":
			image = res['url']
			embed.set_image(url=f"{image}")
		#embed.set_author(name=f"Author: {authr}")
		embed.set_footer(text=f"{date_}")

		await ctx.send(embed=embed)


def setup(bot):
	bot.add_cog(APOD(bot))

