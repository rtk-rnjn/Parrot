import discord, json
from discord.ext import commands

class commandshub(commands.Cog, name="Hub"):
    """

    """
    def __init__(self, bot):
        self.bot = bot


    #    with open("hub.json") as f:
    #       hub = json.load(f)

    #    for current_guild in hub['guilds']:
    #        if current_guild['id'] == ctx.guild.id:
    #            return True
    #    else:
    #        return False


    @commands.guild_only()
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions()
    async def hubvoicekick(self, ctx, member:discord.Member, *, reason:str=None):
        """
        To remove the member from your personal VC, only works if you are in your personal VC created from Hub.

        Syntax:
        `HubVoiceKick <User:Mention/ID> [Reason:Text]`

        Cooldown of 5 seconds after one time use, per member.

        Permissions:
        Need Move Members permissions for the bot
        """