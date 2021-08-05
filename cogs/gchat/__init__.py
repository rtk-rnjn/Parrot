import aiohttp, re, asyncio, json
from discord import Webhook
from database.global_chat import collection
from core import Parrot, Cog
from discord.ext import commands

with open('extra/profanity.json') as f:
    bad_dict = json.load(f)


class MessageEvents(Cog, name="Global Chat"):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.channel)

    async def refrain_message(self, msg: str) -> bool:
        for bad_word in bad_dict:
            if bad_word in msg:
                return False
            elif bad_word not in msg:
                return True

    @Cog.listener()
    async def on_message(self, message):

        if not message.guild or message.author.bot:
            return

        channel = collection.find_one({
            '_id': message.guild.id,
            'channel_id': message.channel.id
        })

        if not channel: return

        bucket = self.cd_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            return await message.channel.send(
                f"Chill out | Reached the ratelimit", delete_after=5.0)

        guild = collection.find_one({'_id': message.guild.id})
        data = collection.find({})

        role = message.guild.get_role(guild['ignore-role'])
        if role:
            if role in message.author.roles:
                return

        if message.content.startswith("$"):
            return

        urls = re.findall(
            'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            message.content.lower())
        if urls:
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | URLs aren't allowed.",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | URLs aren't allowed.",
                    delete_after=5)

        if "discord.gg" in message.content.lower():
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)

        if "discord.com" in message.content.lower():
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | Advertisements aren't allowed.",
                    delete_after=5)

        to_send = await self.refrain_message(message.content)
        if to_send:
            pass
        elif not to_send:
            try:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} | Sending Bad Word not allowed",
                    delete_after=5)
            except Exception:
                return await message.channel.send(
                    f"{message.author.mention} | Sending Bad Word not allowed",
                    delete_after=5)

        try:
            await asyncio.sleep(0.1)
            await message.delete()
        except:
            return await message.channel.send(
                "Bot requires **Manage Messages** permission(s) to function properly."
            )

        for webhook in data:
            hook = webhook['webhook']
            try:

                async def send_webhook():
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(f"{hook}", session=session)

                        await webhook.send(
                            content=message.clean_content,
                            username=message.author.name + "#" +
                            message.author.discriminator,
                            avatar_url=message.author.avatar.url)

                await send_webhook()
            except Exception:
                continue


def setup(bot):
    bot.add_cog(MessageEvents(bot))
