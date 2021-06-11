import discord, json
from discord.ext import commands

class hubsetup(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setuphub")
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True, manage_permissions=True)
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def setuphub(self, ctx, name:str=None):
        """
        To create a hub, to create a Temporary Voice Channel.

        Syntax:
        `Setuphub [Name:Text]`

        Cooldown of 30 seconds after one time use, per guild

        Permissions:
        Need Manage Channels, Manage Roles, and Manage Permissions permissions for the bot, and Manage Server permissions for the user.
        """
        with open("json/hub.json") as f:
            hub = json.load(f)

        for current_guild in hub['guilds']:
            if current_guild['id'] == ctx.guild.id:
                return await ctx.send(f"{ctx.author.mention} Hub is already setup in this server")

        else:
            channel = await ctx.guild.create_voice_channel("HUB - Join to create one", reason=f"Action requested by {ctx.author.name} ({ctx.author.id})")
            hub['guild'].append(
                {
                    "id": ctx.guild.id,
                    "channel": channel.id
                }
            )
            await ctx.send(f"{ctx.author.mention} successfully created **{channel.name}**")

        with open("json/hub.json", "w") as f:
            json.dump(hub, f)

def setup(bot):
    bot.add_cog(hubsetup(bot))