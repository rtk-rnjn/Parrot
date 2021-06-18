
import os 

from datetime import datetime
import discord, aiohttp 
from discord.ext import commands
import urllib.parse

from utils.paginator import Paginator

NASA_KEY = os.environ['NASA_KEY']

class NASA(commands.Cog, name='NASA'):
	'''Incridible NASA API Integration'''
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=['sat', 'satelite'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def nasa(self, ctx, longitute:float, latitude:float, date:str = "2021-01-01"):

		"""Satelite Imagery - NASA"""
		
		link = f'https://api.nasa.gov/planetary/earth/imagery?lon={longitute}&lat={latitude}&date={date}&dim=0.15&api_key={NASA_KEY}'
		
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

	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def apod(self, ctx):
		'''Asteroid Picture of the Day'''
		link = f'https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}'
		
		async with aiohttp.ClientSession() as session:
						async with session.get(link) as r:
								if r.status == 200:
										res = await r.json()
								else: 
									return
		
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

	@commands.command(aliases=['earth'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def epic(self, ctx, index:int = 0, _date:str = "2021-01-01"):
		'''Earth Polychromatic Imaging Camera'''
		s_link = 'https://epic.gsfc.nasa.gov/api/images.php?date=' + _date 
		
		async with aiohttp.ClientSession() as session:
						async with session.get(s_link) as r:
								if r.status == 200:
										res = await r.json()
								else: 
									return


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

	@commands.command(aliases=['finda', 'asteroid'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def findasteroid(self, ctx, start:str, end:str):
		'''You can literally find any asteroid in the space by date. "$help finda" for syntax'''
		link = f'https://api.nasa.gov/neo/rest/v1/feed?start_date={start}&end_date={end}&api_key={NASA_KEY}'
		
		async with aiohttp.ClientSession() as session:
						async with session.get(link) as r:
								if r.status == 200:
										res = await r.json()
								else: 
									return

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

	@commands.command(aliases=['findaid', 'asteroidid'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
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

	@commands.command(aliases=['mrp'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
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

	@commands.command(aliases=['nsearch', 'ns'])
	@commands.guild_only()
	@commands.cooldown(1, 5, commands.BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
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
	bot.add_cog(NASA(bot))