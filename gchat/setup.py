from discord.ext import commands
import json, discord

class WorldChatSetup(commands.Cog, name="Global Chat"):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	@commands.has_permissions(manage_guild=True)
	@commands.guild_only()
	@commands.cooldown(1, 60, commands.BucketType.guild)
	@commands.bot_has_permissions(manage_channels=True, manage_webhooks=True, manage_roles=True)
	async def setupgchat(self, ctx):
		"""
		This command will connect your server with other servers which then connected to #global-chat must try this once
		
		Syntax:
		`Setupgchat`

		Cooldown of 60 seconds after one time use, per guild.

		Permissions:
		Need Manage Channels, Manage Webhook, and Manage Roles permissions for the bot, and Manage Server permission for the user.
		"""
		with open("jsonwchat.json") as f:
			wchat = json.load(f)
		
		with open("json/webhook.json") as g:
			hook = json.load(g) 
		
		guild = ctx.guild
		overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)}
		channel = await guild.create_text_channel('global-chat', topic="Hmm. Please be calm, be very calm", overwrites=overwrites)

		try:
				webhook = await channel.create_webhook(name="GlobalChat", avatar=await ctx.me.avatar_url.read())
		except:
				await ctx.send("Bot need **Manage Webhook** permission to work properly")
				return await channel.delete()

		wchat.append(channel.id)
		hook.append(f"{webhook.url}")

		with open("json/webhook.json", "w+") as f:
			json.dump(hook, f)

		with open("wchat.json", "w+") as g:
			json.dump(wchat, g)

		await ctx.send(f"{channel.mention} created successfully.")


def setup(bot):
	bot.add_cog(WorldChatSetup(bot))