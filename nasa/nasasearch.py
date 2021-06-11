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

class NASASearch(commands.Cog, name='NASA'):
	#'''NASA Image and Video Library'''
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['nsearch', 'ns'])
	async def nasasearch(self, ctx, *, string:str):
		'''NASA Image and Video Library'''
		new_text = urllib.parse.quote(string)
		link = 'https://images-api.nasa.gov/search?q=' + new_text
		req = requests.get(link)

		res = req.json()

		if res['collection']['metadata']['total_hits'] == 0:
			await ctx.send(f'{ctx.author.mention} could not find **{string}** in NASA Image and Video Library.')
		
		_1_des = res['collection']['items'][0]['data'][0]['description'][:1000:]
		_1_mdT = res['collection']['items'][0]['data'][0]['media_type']
		_1_tit = res['collection']['items'][0]['data'][0]['title']
		_1_pre = res['collection']['items'][0]['links'][0]['href']

		_2_des = res['collection']['items'][1]['data'][0]['description'][:1000:]
		_2_mdT = res['collection']['items'][1]['data'][0]['media_type']
		_2_tit = res['collection']['items'][1]['data'][0]['title']
		_2_pre = res['collection']['items'][1]['links'][0]['href']
		
		_3_des = res['collection']['items'][2]['data'][0]['description'][:1000:]
		_3_mdT = res['collection']['items'][2]['data'][0]['media_type']
		_3_tit = res['collection']['items'][2]['data'][0]['title']
		_3_pre = res['collection']['items'][2]['links'][0]['href']

		
		embed = discord.Embed(title="NASA Image and Video Library", colour=discord.Colour.blue())
		embed.add_field(name=f"[1] {_1_tit}", value=f"{_1_des}", inline=False)
		embed.add_field(name=f"[2] {_2_tit}", value=f"{_2_des}", inline=False)
		embed.add_field(name=f"[3] {_3_tit}", value=f"{_3_des}", inline=False)


		await ctx.send(f'{ctx.author.mention} Found three results, media type:\n[1] **{_1_mdT}**\n[2] **{_2_mdT}**\n[3] **{_3_mdT}**\nFrom NASA Image and Video Library database. You may use the index [1,2,3] to get the media files.')
		await ctx.send(embed=embed)
	
		ans = []
		def check(m):
			return m.author == ctx.author and m.channel == ctx.channel
	
		message = await self.bot.wait_for('message', timeout=60, check=check)
	
	
		ans.append(message.content)

#		ind_ = ans[0]
	
		#pre_ = requests.get(_1_pre)
		col = res['collection']['items'][int(ans[0])]['href']
		print(col, "\n")
		req = requests.get(col)
		res = req.json()
		print(res, "\n")

		try:
			for i in range(len(res[0])):
					if ".mp4" in res[i]:
						url = res[i]
						print(url)
						await ctx.send(f'{url}')
						break
		except:
			pass
		
		try:	
			for i in range(len(res[0])):
					if ".jpg" in res[i]:
						url = res[i]
						await ctx.send(f'{url}')
						break
		except:
			pass

def setup(bot):
	bot.add_cog(NASASearch(bot))
