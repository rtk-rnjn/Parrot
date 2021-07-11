import discord 
import random 
import io, base64, datetime, aiohttp, urllib, asyncio
from discord.ext import commands
from discord.ext.commands import command, guild_only, bot_has_permissions, cooldown, BucketType
from random import choice
from discord import Embed 
from aiohttp import request

import akinator
from akinator.async_aki import Akinator

aki = Akinator()

from utilities.paginator import Paginator
from core import Parrot, Context, Cog

from utilities.checks import user_premium_cd

with open("extra/truth.txt") as f:
  _truth = f.read()

with open("extra/dare.txt") as g:
  _dare = g.read()

class fun(Cog, name="fun"):
  '''Parrot gives you huge amount of fun commands, so that you won't get bored'''

  def __init__(self, bot: Parrot):
    self.bot = bot
    
  @command(name='8ball')
  @user_premium_cd()
  async def _8ball(self, ctx: Context, *, question:commands.clean_content):
    """
    8ball Magic, nothing to say much
    """
    response = ["All signs point to yes...","Yes!", "My sources say nope.", "You may rely on it.", "Concentrate and ask again...", "Outlook not so good...", "It is decidedly so!", "Better not tell you.", "Very doubtful.", "Yes - Definitely!", "It is certain!", "Most likely.", "Ask again later.", "No!", "Outlook good.", "Don't count on it.", "Why not", "Probably", "Can't say", "Well well..."]
    await ctx.reply(f'Question: **{question}**\nAnswer: **{random.choice(response)}**')


  @commands.command()
  @user_premium_cd()
  async def choose(self, ctx: Context, *, options:commands.clean_content):
    '''
    Confuse something with your decision? Let Parrot choose from your choice.
    NOTE: The `Options` should be seperated by commas `,`.
    '''
    options = options.split(',')
    await ctx.reply(f'{ctx.author.mention} I choose {choice(options)}')
  

  @commands.command(aliases=['colours', 'colour'])
  @user_premium_cd()
  @commands.bot_has_permissions(embed_links=True)
  async def color(self, ctx: Context, colour):
    '''
    To get colour information using the hexademical codes.
    '''
    
    link = f"https://www.thecolorapi.com/id?format=json&hex={colour}"
    async with aiohttp.ClientSession() as session:
      async with session.get(link) as response:
        if response.status == 200:
          res = await response.json()
        else:
          return

    green = round(res['rgb']['fraction']['g'], 2)
    red = round(res['rgb']['fraction']['r'], 2)
    blue = round(res['rgb']['fraction']['b'], 2)
    _green = res['rgb']['g']
    _red = res['rgb']['r']
    _blue = res['rgb']['b']
    
    #HSL VALUE
    hue = round(res['hsl']['fraction']['h'], 2)
    saturation = round(res['hsl']['fraction']['s'], 2)
    lightness = round(res['hsl']['fraction']['l'], 2)
    _hue = res['hsl']['h']
    _saturation = res['hsl']['s']
    _lightness = res['hsl']['l']
    
    #HSV VALUE
    hue_ = round(res['hsv']['fraction']['h'], 2)
    saturation_ = round(res['hsv']['fraction']['s'], 2)
    value_ = round(res['hsv']['fraction']['v'], 2)
    _hue_ = res['hsv']['h']
    _saturation_ = res['hsv']['s']
    _value_ = res['hsv']['v']
    
    #GENERAL
    name = res['name']['value']
    close_name_hex = res['name']['closest_named_hex']
    exact_name = res['name']['exact_match_name']
    distance = res['name']['distance']

    embed = discord.Embed(title="Parrot colour prompt", timestamp=datetime.datetime.utcnow(), colour = discord.Color.from_rgb(_red, _green, _blue), description=f"Colour name: `{name}` | Close Hex code: `{close_name_hex}` | Having exact name? `{exact_name}` | Distance: `{distance}`")
    embed.set_thumbnail(url=f"https://some-random-api.ml/canvas/colorviewer?hex={colour}")
    embed.set_footer(text=f"{ctx.author.name}")
    feilds = [
      ("RGB value (fraction)", f"Red: `{_red}` (`{red}`)\nGreen: `{_green}` (`{green}`)\nBlue: `{_blue}` (`{blue}`)", True),
      ("HSL value (fraction)", f"Hue: `{_hue}` (`{hue}`)\nSaturation: `{_saturation}` (`{saturation}`)\nLightness: `{_lightness}` (`{lightness}`)", True),
      ("HSV value (fraction)", f"Hue: `{_hue_}` (`{hue_}`)\nSaturation: `{_saturation_}` (`{saturation_}`)\nValue: `{_value_}` (`{value_}`)", True)		
      ]
    for name, value, inline in feilds:
      embed.add_field(name=name, value=value, inline=inline)
    await ctx.reply(embed=embed)
      
  
  @command()
  @user_premium_cd()
  @bot_has_permissions(embed_links=True)
  async def decode(self, ctx: Context, *, string:str):
    '''
    Decode the code to text from Base64 encryption
    '''
    base64_string = string
    base64_bytes = base64_string.encode("ascii") 
    
    sample_string_bytes = base64.b64decode(base64_bytes) 
    sample_string = sample_string_bytes.decode("ascii") 
    
    embed = discord.Embed(title="Decoding...", colour=discord.Colour.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Encoded text:", value=f'```\n{base64_string}\n```', inline=False)
    embed.add_field(name="Decoded text:", value=f'```\n{sample_string}\n```', inline=False)
    embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/4/45/Parrot_Logo.png')
    embed.set_footer(text=f"{ctx.author.name}", icon_url=f'{ctx.author.avatar_url}')
    await ctx.reply(embed=embed)



  @command()
  @bot_has_permissions(embed_links=True)
  @user_premium_cd()
  async def encode(self, ctx: Context, *, string:str):
    '''
    Encode the text to Base64 Encryption and in Binary
    '''
    sample_string = string
    sample_string_bytes = sample_string.encode("ascii") 
    res = ''.join(format(ord(i), 'b') for i in string)
    base64_bytes = base64.b64encode(sample_string_bytes) 
    base64_string = base64_bytes.decode("ascii") 
    
    embed = discord.Embed(title="Encoding...", colour=discord.Colour.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Normal [string] text:", value=f'```\n{sample_string}\n```', inline=False)
    embed.add_field(name="Encoded [base64]:", value=f'```\n{base64_string}\n```', inline=False)
    embed.add_field(name="Encoded [binary]:", value=f'```\n{str(res)}\n```', inline=False)
    embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/4/45/Parrot_Logo.png')
    embed.set_footer(text=f"{ctx.author.name}", icon_url=f'{ctx.author.avatar_url}')
    await ctx.reply(embed=embed)

  
      
  @command(name="fact")
  @user_premium_cd()
  @bot_has_permissions(embed_links=True)
  async def animal_fact(self, ctx: Context, *, animal: str):
    '''
    Return a random Fact. It's useless command, I know

    NOTE: Available animals - Dog, Cat, Panda, Fox, Bird, Koala
    '''
    if (animal := animal.lower()) in ("dog", "cat", "panda", "fox", "bird", "koala"):
      fact_url = f"https://some-random-api.ml/facts/{animal}"
      image_url = f"https://some-random-api.ml/img/{'birb' if animal == 'bird' else animal}"

      async with request("GET", image_url, headers={}) as response:
        if response.status == 200:
          data = await response.json()
          image_link = data["link"]

        else:
          image_link = None

      async with request("GET", fact_url, headers={}) as response:
        if response.status == 200:
          data = await response.json()

          embed = Embed(title=f"{animal.title()} fact", description=data["fact"], colour=ctx.author.colour)
          if image_link is not None:
            embed.set_image(url=image_link)
          await ctx.reply(embed=embed)

        else:
          await ctx.reply(f"{ctx.author.mention} API returned a {response.status} status.")

    else:
      await ctx.reply(f"{ctx.author.mention} no facts are available for that animal. Available animals: `dog`, `cat`, `panda`, `fox`, `bird`, `koala`")


  @commands.command()
  @user_premium_cd()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  async def gay(self, ctx: Context, *, member:discord.Member=None):
    """
    Image Generator. Gay Pride.
    """
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/gay?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'gay.png')) # replying the file


  @commands.command()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  @user_premium_cd()
  async def glass(self, ctx: Context, *, member:discord.Member=None):
    '''
    Provide a glass filter on your profile picture, try it!
    '''
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/glass?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'glass.png')) # replying the file


  @commands.command()
  @user_premium_cd()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  async def horny(self, ctx: Context, *, member:discord.Member=None):
    """
    Image generator, Horny card generator.
    """
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/horny?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'horny.png')) # replying the file


  @commands.command(aliases=['insult'])
  @user_premium_cd()
  async def roast(self, ctx: Context, *, member: discord.Member = None):
    '''
    Insult your enemy, Ugh!
    '''
    if member == None: member = ctx.author
    async with aiohttp.ClientSession() as session:
      async with session.get("https://insult.mattbas.org/api/insult") as response:
        insult = await response.text()
        await ctx.reply(f"**{member.name}** {insult}")



  @commands.command(aliases=['its-so-stupid'])
  @user_premium_cd()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  async def itssostupid(self, ctx, *, comment:str):
    """
    :| I don't know what is this, I think a meme generator.
    """
    member = ctx.author
    if len(comment) > 20: comment = comment[:19:]
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/its-so-stupid?avatar={member.avatar_url_as(format="png", size=1024)}&dog={comment}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'itssostupid.png')) # replying the file

      

  @commands.command()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  @user_premium_cd()
  async def jail(self, ctx: Context, *, member:discord.Member=None):
    """
    Image generator. Makes you behind the bars. Haha
    """
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/jail?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'jail.png')) # replying the file
  

  @commands.command()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  @user_premium_cd()
  async def lolice(self, ctx: Context, *, member:discord.Member=None):
    """
    This command is not made by me. :\
    """
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/lolice?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'lolice.png')) # replying the file
  

      
      
  @commands.command(name='meme')
  @commands.bot_has_permissions(embed_links=True)
  @user_premium_cd()
  async def meme(self, ctx: Context):
    '''
    Random meme generator.
    '''
    link = "https://memes.blademaker.tv/api?lang=en"
    async with aiohttp.ClientSession() as session:
      async with session.get(link) as response:
        if response.status == 200:
          res = await response.json()
        else:
          return
    title = res['title']
    ups = res["ups"]
    downs = res["downs"]
    sub = res["subreddit"]

    embed = discord.Embed(title=f'{title}', discription=f"{sub}", timestamp=datetime.datetime.utcnow())
    embed.set_image(url = res["image"])
    embed.set_footer(text=f"UP(s): {ups} | DOWN(s): {downs}") 

    await ctx.reply(embed=embed)
      

  @commands.command()
  @user_premium_cd()
  @commands.bot_has_permissions(embed_links=True)
  async def fakepeople(self, ctx: Context):
    '''
    Fake Identity generator.
    '''
    link = "https://randomuser.me/api/"
    async with aiohttp.ClientSession() as session:
      async with session.get(link) as response:
        if response.status == 200:
          res = await response.json()
        else:
          return
    res = res['results'][0]
    name = f"{res['name']['title']} {res['name']['first']} {res['name']['last']}"
    address = f"{res['location']['street']['number']}, {res['location']['street']['name']}, {res['location']['city']}, {res['location']['state']}, {res['location']['country']}, {res['location']['postcode']}"
    cords = f"{res['location']['coordinates']['latitude']}, {res['location']['coordinates']['longitude']}"
    tz = f"{res['location']['timezone']['offset']}, {res['location']['timezone']['description']}"
    email = res['email']
    usrname = res['login']['username']
    pswd = res['login']['password']
    age = res['dob']['age']
    phone = f"{res['phone']}, {res['cell']}"
    pic = res['picture']['large']

    em = discord.Embed(title=f"{name}", description=f"```\n{address}\n{cords}```", timestamp=datetime.datetime.utcnow())
    em.add_field(name="Timezone", value=f"```\n{tz}```", inline=True)
    em.add_field(name="Email & Password", value=f"```\nUsername: {usrname}\nEmail: {email}\nPassword: {pswd}```", inline=True)
    em.add_field(name="Age", value=f"```\n{age}```", inline=True)
    em.set_thumbnail(url=pic)
    em.add_field(name="Phone", value=f"```\n{phone}```", inline=True)
    em.set_footer(text=f"{ctx.author.name}")

    await ctx.reply(embed=em)


  @commands.command()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  @user_premium_cd()
  async def simpcard(self, ctx: Context, *, member:discord.Member=None):
    """
    Good for those, who are hell simp! LOL
    """
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/simpcard?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'simpcard.png')) # replying the file
      
  
  @command(name="slap", aliases=["hit"])
  @commands.bot_has_permissions(manage_messages=True)
  @user_premium_cd()
  async def slap_member(self, ctx: Context, member: discord.Member, *, reason: commands.clean_content = "for no reason"):
    '''
    Slap virtually with is shit command.
    '''
    await ctx.message.delete()
    await ctx.reply(f"{ctx.author.display_name} slapped {member.mention} {reason}!")
  
    
  @commands.command(aliases=['trans'])
  @commands.bot_has_permissions(embed_links=True)
  @user_premium_cd()
  async def translate(self, ctx: Context, from_lang:str, to_lang:str, *, text:str):
    """
    This command is useful, to be honest, if and only if you use correctly, else it gives error. Not my fault.
    """
    from_lang = urllib.parse.quote(from_lang)
    to_lang = urllib.parse.quote(to_lang)
    text = urllib.parse.quote(text)
    link = 'https://api.mymemory.translated.net/get?q=' + text + '&langpair=' + from_lang + '|' + to_lang
    async with aiohttp.ClientSession() as session:
      async with session.get(link) as response:
        if response.status == 200:
          res = await response.json()
        else:
          return

    trans_text = res['responseData']['translatedText']

    embed = discord.Embed(title="Translated!!", description=f"Translation: {trans_text}")
    embed.set_footer(text=f"{ctx.author.name}")
    await ctx.reply(embed=embed)
    

  @commands.command(aliases=['triggered'])
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  @user_premium_cd()
  async def trigger(self, ctx: Context, *, member:discord.Member=None):
    """
    User Triggered!
    """
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/triggered?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'triggered.gif')) # replying the file



  @commands.command(aliases=['def', 'urban'])
  @user_premium_cd()
  @commands.bot_has_permissions(embed_links=True)
  async def urbandictionary(self, ctx: Context, *, text:str):
    '''
    LOL. This command is insane.
    '''
    t = text
    text = urllib.parse.quote(text)
    link = 'http://api.urbandictionary.com/v0/define?term=' + text 

    async with aiohttp.ClientSession() as session:
      async with session.get(link) as response:
        if response.status == 200:
          res = await response.json()
        else:
          return
    if res['list'] == []: return await ctx.reply(f"{ctx.author.mention} :\ **{t}** means nothings. Try something else")
    em_list = []
    for i in range(0, len(res['list'])):
      _def = res['list'][i]['definition']
      _link = res['list'][i]['permalink']
      thumbs_up = res['list'][i]['thumbs_up']
      thumbs_down = res['list'][i]['thumbs_down']
      author = res['list'][i]['author']
      example = res['list'][i]['example']
      word = res['list'][i]['word'].capitalize()	
      embed = discord.Embed(title=f"{word}", description=f"{_def}", url=f"{_link}", timestamp=datetime.datetime.utcnow())
      embed.add_field(name="Example", value=f"{example}")
      embed.set_author(name=f"Author: {author}")
      embed.set_footer(text=f"👍 {thumbs_up} | 👎 {thumbs_down}")
      em_list.append(embed)

    paginator = Paginator(pages=em_list, timeout=60.0)
    
    await paginator.start(ctx)


  @commands.command()
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  @user_premium_cd()
  async def wasted(self, ctx: Context, *, member:discord.Member=None):
    """
    Overlay 'WASTED' on your profile picture, just like GTA:SA
    """
    if member is None: member = ctx.author
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/wasted?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'wasted.png')) # replying the file
  

  @commands.command(aliases=['youtube-comment'])
  @commands.bot_has_permissions(attach_files=True, embed_links=True)
  @user_premium_cd()
  async def ytcomment(self, ctx: Context, *, comment:str):
    '''
    Makes a comment in YT. Best ways to fool your fool friends. :')
    '''
    member = ctx.author
    if len(comment) > 1000: comment = comment[:999:]
    if len(member.name) > 20: name = member.name[:20:]
    else: name = member.name
    async with aiohttp.ClientSession() as wastedSession:
        async with wastedSession.get(f'https://some-random-api.ml/canvas/youtube-comment?avatar={member.avatar_url_as(format="png", size=512)}&username={name}&comment={comment}') as wastedImage: # get users avatar as png with 1024 size
            imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
            
            await wastedSession.close() # closing the session and;
            
            await ctx.reply(file=discord.File(imageData, 'ytcomment.png')) # replying the file
  
  
  @commands.command() 
  @user_premium_cd()
  @commands.bot_has_permissions(embed_links=True)
  async def dare(self, ctx: Context, *, member:discord.Member=None):
    """
    I dared you to use this command.
    """
    dare = _dare.split("\n")
    if member is None:
      em = discord.Embed(title="Dare", description=f"{random.choice(dare)}", timestamp=datetime.datetime.utcnow())
    else:
      em = discord.Embed(title=f"{member.name} Dared", description=f"{random.choice(dare)}", timestamp=datetime.datetime.utcnow())
    
    em.set_footer(text=f'{ctx.author.name}')
    await ctx.reply(embed=em)


  @commands.command() 
  @user_premium_cd()
  @commands.bot_has_permissions(embed_links=True)
  async def truth(self, ctx: Context, *, member:discord.Member=None):
    """
    Truth: Who is your crush?
    """
    t = _truth.split("\n")
    if member is None:
      em = discord.Embed(title="Truth", description=f"{random.choice(t)}", timestamp=datetime.datetime.utcnow())
      em.set_footer(text=f'{ctx.author.name}')
    else:
      em = discord.Embed(title=f"{member.name} reply!", description=f"{random.choice(t)}", timestamp=datetime.datetime.utcnow())
      em.set_footer(text=f'{ctx.author.name}')
    await ctx.reply(embed=em)

  @commands.command()
  async def aki(self, ctx):
        q = await aki.start_game()
        question_num = 1
        while aki.progression <= 80:
            question = q + "\n\t"
            embed = discord.Embed(color=0xFF0000)
            embed.add_field(
                name=f"Q-{question_num}\n{question}",
                value=
                "Reply with `yes/y` `no/n` `i/idk/i don't know` `p/probably` `proably not/pn`",
            )
            await ctx.send(embed=embed)

            def check(m):
                replies = [
                    "yes", "y", "no", "n", "i", "idk", "i don't know",
                    "probably", "p", "probably not", "pn"
                ]
                return (m.content in replies and m.channel == ctx.channel
                        and m.author == ctx.author)
            try:
              msg = await self.client.wait_for("message", check=check, timeout=30)
            except Exception:
              return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
            if msg.content == "b":
                try:
                    q = await aki.back()
                except akinator.CantGoBackAnyFurther:
                    pass
            else:
                q = await aki.answer(msg.content)
            question_num += 1
        await aki.win()

        embed = discord.Embed(
            title=
            f"It's {aki.first_guess['name']} ({aki.first_guess['description']})! Was I correct?\n\t",
            color=0xFF0000,
        )
        embed.add_field(name="Reply with `yes/y` `no/n`", value="\u200b")
        await ctx.send(embed=embed)

        def check(m):
            return (m.content.lower() in ["yes", "y"]
                    and m.channel == ctx.channel and m.author == ctx.author)

        try: correct = await self.client.wait_for("message", check=check, timeout=30)
        except Exception: return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
        if correct.content.lower() == "yes" or correct.content.lower() == "y":
            embed = discord.Embed(title="Yay! I guessed it right",
                                  color=0xFF0000)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Oof! Kinda hard one",
                                  color=0xFF0000)
            await ctx.send(embed=embed)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(GuessName.guess())
        loop.close()

def setup(bot):
  bot.add_cog(fun(bot))
