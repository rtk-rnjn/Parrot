from discord.ext import commands
import discord, asyncio, time, datetime, aiohttp


class dm_mod(commands.Cog):
    """This Section will only used in support server for asking for moderation!"""

    def __init__(self, bot):
        self.bot = bot
   
            
    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.cooldown(1, 900, commands.BucketType.user)
    async def applymod(self, ctx):
        """
        Want mod? Consider asking us out!

        Usage:
        `Applymod`

        NOTE: If you want, the same rule set then consider asking out `!! Ritik Ranjan#9230` this guy.
        """
        if ctx.guild.id != 741614680652644382:  return await ctx.send("This command is only used in Support Server")
        await ctx.send(f"{ctx.author.mention} check your DM!", delete_after=3)
        

        try:
            message = await ctx.author.send("Hey there!")
            await asyncio.sleep(2)
            await message.edit(content="Please wait for few seconds to initiate!")
            await asyncio.sleep(5.5)
            await message.edit(content="Success")
            await asyncio.sleep(0.5)
            await message.delete()
        except Exception as e:
            return await ctx.send("Can NOT DM the user. Make sure your DM(s) are turned. ```\nError: {}```".format(e))

        start_msg = await ctx.author.send("You have 5 mins to reply to each questions, else bot get asyncio.timeout Exception! Then try again later! If you changed your mind, and don't want to be the moderator then ignore this DM channel for 3 mins")
        await asyncio.sleep(15)
        await start_msg.edit(content="~~You have 5 mins to reply to each questions, else you will get the Timeout! Then try again later! If you changed your mind, and don't want to be the moderator then ignore this DM channel for 3 mins~~")


        questions = [
            'Real Name, and age (if age below 13, then please disable your discord account)',
            'Do you know how to know, which action is being performed by whom (reading Audit Log I mean); also the basic moderation of Dyno, and MEE6',
            'Do you want Moderation access for name and fame?',
            'Are you aware of Discord Terms and Conditions, Server Rules and Moderation Set?',
            'A member with account age more than 200 days joined the server, after talkin for a while, he said, "I am 12 years old", then what you will do? \n`[1]` Warn\n`[2]` Mute\n`[3]` Ban\n`[4]` Ignore \n`[5]` Report to the higher mods\n`[6]` Other(s) [Mention the reason if you think something else]',
            'While you were reading the logs, you saw, a tons of Webhooks are being created in different different channel, then what you will do? \n`[1]` Warn\n`[2]` Mute\n`[3]` Ban\n`[4]` Ignore \n`[5]` Report to the higher mods',
            'If someone starts to abuse you, me, or any other member of the server, then what you will do? \n`[1]` Warn\n`[2]` Mute\n`[3]` Ban\n`[4]` Ignore \n`[5]` Report to the higher mods\n`[6]` Other(s) [Mention the reason if you think something else]',
            'You must be knowing there is a NukeBot in the server, if someone triggers the command `n!killall`, then what you will do? (If you don\'t know what this command do then consider typing `n!help killall`) \n`[1]` Warn\n`[2]` Mute\n`[3]` Ban\n`[4]` Ignore \n`[5]` Report to the higher mods\n`[6]` Other(s) [Mention the reason if you think something else]',
            'If you found some other mod is just kicking/muting/banning the member with no reason provided, then what you will do? \n`[1]` Warn\n`[2]` Mute\n`[3]` Ban\n`[4]` Ignore \n`[5]` Report to the higher mods\n`[6]` Other(s) [Mention the reason if you think something else]',
            'Type the following statement as fast as you could: \n```\nA QuIcK bRoWn FoX jUmPs OvEr ThE lAzY dOg.\n```',
            'IQ Test: If it takes eight men ten hours to build a wall, how long would it take four men?',
            'Presence of Mind Test: Tell how many members are in total in server SECTOR 17-29',
            'Do you know about the Default Permission management of the Discord and it\'s working?',
            '``@everyone`` role are denied to send message in any specific ``#channel-abc``, suppose, ``@Role-ABC`` are allowed to send messages in ``#channel-abc``, if user ``@User-ABC`` with role ``@Role-ABC`` is even manually denied to send messages in channel ``#channel-abc``, then, will the user ``@User-ABC`` will able to send messages in that channel?',
            '``@Role-PQR`` is above the ``@Muted-Role``, suppose, user ``@User-PQR`` was hell annoying with the moderators, so ``@Mod-PQR`` muted ``@User-PQR``, then, will the user will be Muted?',
            'SECTOR 17-29 is Support Server as well, do you know about the stream Beasty Stats (YouTube Channel)?',
            'Why you want to be Moderator?',
            'Anything else you want to say?',
            'Swearing is allowed but in limit, promise us that if your get the moderation, you won\'t be f*cking dick or rule the Server, if not, then OK. LOL. ||Don\'t mind||'
        ]

        def check(m):
            return m.author == ctx.author and str(m.channel.type) == "private"

        ans = []

        main_ini = time.time()

        for question in questions:
            temp_time_ini = time.time()
            temp_msg = await ctx.author.send(f'{question}')
            try:
                msg = await self.bot.wait_for('message', timeout=300.0, check=check)
            except Exception as e:
                await ctx.author.send(f"```\nError: You didn't answer on time.```")
                return ctx.author.send(f"Try again after a while")

            temp_time_fin = time.time()
            ans.append(f"{msg.content}\n\nTime Taken: {round(temp_time_fin - temp_time_ini, 3)}s")
            await temp_msg.edit(content=f'[QUESTION RETRACTED] Time taken to answer: `{round(temp_time_fin - temp_time_ini, 3)}`s')

        main_fin = time.time()
        confirm_msg = await ctx.author.send("Please wait a seconds!")

        await asyncio.sleep(1)
        
        main_str = ""
        for q, a in zip(questions, ans):
            main_str = main_str + f"{q.replace('`', '')}\n{a}\n\n"
        
        try:
            async with aiohttp.ClientSession() as aioclient:
                post = await aioclient.post('https://hastebin.com/documents', data=main_str)
                if post.status == 200:
                    response = await post.text()
                    link = f'https://hastebin.com/{response[8:-2]}'
                    em = discord.Embed(title="MODERATION APPLY", description=f"```\nNAME : {ctx.author.name}\nID   : {ctx.guild.id}\nAT   : {datetime.datetime.utcnow()}\n\nTIME TAKEN : {round((main_fin - main_ini), 3)}```", url=f"{link}")
                    await self.bot.get_channel(840114964353384448).send(embed=em)
                    await confirm_msg.edit(content="Success! You will be notified ASAP! Thanks for your patience")
                    return
                
                post = await aioclient.post("https://bin.readthedocs.fr/new", data={'code': main_str, 'lang': 'txt'})
                if post.status == 200:
                    link = post.url
                    em = discord.Embed(title="MODERATION APPLY", description=f"```\nNAME : {ctx.author.name}\nID   : {ctx.author.id}\nAT   : {datetime.datetime.utcnow()}\n\nTIME TAKEN : {round((main_fin - main_ini), 3)}```", url=f"{link}")
                    await self.bot.get_channel(840114964353384448).send(embed=em)
                    await confirm_msg.edit(content="Success! You will be notified ASAP! Thanks for your patience")
                    return
        except Exception as e:
            await self.bot.get_channel(840114964353384448).send(f"Something not right!```\nError: {e}```\n{ans}")

def setup(bot):
    bot.add_cog(dm_mod(bot))
