#API Key: qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC

#Account Email: ritik0ranjan@gmail.com
#Account ID: a37c9407-bed3-4379-a8ef-30abb1a0447c

from datetime import datetime
import discord, json, requests 
from discord.ext import commands
import urllib.parse

class NASA(commands.Cog, name='NASA'):
	#'''Incridible NASA API Integration'''
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['sat', 'satelite'])
	async def nasa(self, ctx, lon:float, lat:float, _date:str = "2021-01-01"):

		"""Satelite Imagery - NASA"""
		
		link = 'https://api.nasa.gov/planetary/earth/imagery?lon='+ str(lon) +'&lat='+ str(lat) +'&date='+ _date +'&dim=0.15&api_key=qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC'
		
		#link = 'https://api.nasa.gov/planetary/earth/assets?lon=' + str(lon) + '&lat=' + str(lat) + '&date=' + str(date) +'&dim=0.15&api_key=qFkn3NAu3LfQL4IKKCXWQYDZhHaaJdEw6QqP7vSC'
		#req = requests.get(link)
		#res = req.json()

		#planet = res['resource']['planet'].capitalize()
		#url = res['url']
		#print(link)

		embed = discord.Embed(title='Earth', colour=discord.Colour.blue())
		embed.set_image(url=f"{link}")
		#embed.set_thumbnail(url='https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png')
		embed.set_footer(text=f"{ctx.author.name}")

		await ctx.send(embed=embed)


def setup(bot):
	bot.add_cog(NASA(bot))