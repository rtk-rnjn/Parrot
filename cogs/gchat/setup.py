from discord.ext import commands
import discord

from core.cog import Cog
from core.bot import Parrot
from core.ctx import Context

from database.global_chat import gchat_update


class WorldChatSetup(Cog, name="global chat"):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_webhooks=True,
                                  manage_roles=True)
    async def setupgchat(self, ctx: Context):
        """
		This command will connect your server with other servers which then connected to #global-chat must try this once
		
		Syntax:
		`Setupgchat`

		Cooldown of 60 seconds after one time use, per guild.

		Permissions:
		Need Manage Channels, Manage Webhook, and Manage Roles permissions for the bot, and Manage Server permission for the user.

		NOTE: Running the command twice will create a another #global-chat and previus #global-chat will no longer work. In future update, that channel will be delete! Stay Tuned
		"""

        guild = ctx.guild
        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(read_messages=True,
                                        send_messages=True,
                                        read_message_history=True),
            guild.me:
            discord.PermissionOverwrite(read_messages=True,
                                        send_messages=True,
                                        read_message_history=True)
        }
        channel = await guild.create_text_channel(
            'global-chat',
            topic="Hmm. Please be calm, be very calm",
            overwrites=overwrites)

        webhook = await channel.create_webhook(name="GlobalChat",
                                               avatar=await
                                               ctx.me.avatar_url.read())

        post = {'chanel_id': channel.id, 'webhook': webhook.url}

        await gchat_update(guild.id, post)
        await ctx.send(f"{channel.mention} created successfully.")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.bot_has_permissions(manage_channels=True,
                                  manage_webhooks=True,
                                  manage_roles=True)
    async def gchatignore(self, ctx: Context, role: discord.Role):
        """
		To igonre the member to type in global chat, via Role.

		Syntax:
		`Gchatignore <Role:Mention/ID>`
		"""
        post = {'ignore-role': role.id}
        await gchat_update(ctx.guild.id, post)
        await ctx.send(
            f"{ctx.author.mention} *{role.name} ({role.id})* will be ignored from global chat!"
        )


def setup(bot):
    bot.add_cog(WorldChatSetup(bot))
