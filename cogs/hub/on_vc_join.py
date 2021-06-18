from discord.ext import commands
import discord, json

class event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        @commands.Cog.listener()
        async def on_voice_state_update(self, member, before, after):
            """
            To check whether someone joins the Hub channel.

            Syntax:
            None

            Permissions:
            None
            """

            with open("json/hub.json") as f:
                hub = json.load(f)

            if before.channel is None: pass
            else: pass

            for current_guild in hub['guilds']:
                if current_guild['id'] == after.channel.guild.id:
                    break
            else:
                return

            guild = self.bot.get_guild(current_guild['id'])

            if len(f'{member.name} VC') > 25: name = str({member.name})[:22:] + " VC"
            else: name = f'{member.name} VC'

            channel = await guild.create_voice_channel(f"{name} VC", reason=f"Parrot Auto Hub! Requested by, and created for {member.name} ({member.id})")

            await channel.set_permissions(member, view_channel=True, connect=True, speak=True, stream=True, manage_permissions=True, move_members=True, mute_members=True, priority_speaker=True, reason=f"Parrot Auto Hub! Requested by and created for {member.name} ({member.id})")
            await channel.set_permissions(after.channel.guild.default_role, view_channel=False, connect=False, manage_permissions=False, move_members=False, mute_members=False, reason=f"Parrot Auto Hub! Requested by and created for {member.name} ({member.id})")

def setup(bot):
    bot.add_cog(event(bot))