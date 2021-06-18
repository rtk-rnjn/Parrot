from discord.ext import commands
import discord, json

class commands(commands.Cog, name="Global Chat"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def broadcast(self, ctx, *, message:str):
        """
        To broadcast all over the global channel. Only for owners.

        Syntax:
        `Broadcast <Message:Text>`
        """
        with open("webhook.json") as f:
            webhooks = json.load(f)

        async for hook in webhooks:
            try:
                async def send_webhook():
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(f"{hook}", adapter=AsyncWebhookAdapter(session))

                        await webhook.send(content=f"{message}",
                                           username="SYSTEM",
                                           avatar_url=f"{self.bot.guild.me.avatar_url}")

                await send_webhook()
            except:
                continue


def setup(bot):
    bot.add_cog(commands(bot))