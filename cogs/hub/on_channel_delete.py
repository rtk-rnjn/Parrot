from discord.ext import commands
import discord, json

class event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        @commands.Cog.listener()
        async def on_guild_channel_delete(self, channel):
            """
            To check whether the Hub channel itself got deleted.

            Syntax:
            None

            Permissions:
            None
            """

            with open("json/hub.json") as f:
                hub = json.load(f)

            for current_guild in hub['guilds']:
                if current_guild['id'] == channel.guild.id:
                    hub['guild'].remove(current_guild)
                    break

            with open("hub.json") as f:
                json.dump(hub, f)

def setup(bot):
    bot.add_cog(event(bot))