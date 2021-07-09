import json
from random import randint
from discord.ext import commands


class MessageLevel(commands.Cog, name="Leveling"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.author.bot: return
        if ctx.author.dm_channel: return
        with open("json/config.json") as f:
            guild = json.load(f)

        if ctx.guild.id in guild['guilds']: return

        with open('json/level.json', encoding='utf-8') as f:
            level = json.load(f)

        for current_guild in level['levels']:
            xp_to_add = randint(1, 10)

            if (current_guild['guild_id']
                    == ctx.guild.id) and (current_guild['name']
                                          == ctx.author.id):
                xp = current_guild['xp']
                current_guild['lvl'] = current_guild['lvl'] + int(
                    ((xp + xp_to_add) // 420)**0.05)
                current_guild['xp'] = current_guild['xp'] + xp_to_add
                with open('json/level.json', 'w+') as f:
                    json.dump(level, f)
                break
        else:
            level['levels'].append({
                'guild_id': ctx.guild.id,
                'name': ctx.author.id,
                'xp': 10,
                'lvl': 1
            })
        with open('json/level.json', 'w+') as f:
            json.dump(level, f)
        return


def setup(bot):
    bot.add_cog(MessageLevel(bot))
