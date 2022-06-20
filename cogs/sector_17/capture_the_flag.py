from __future__ import annotations

from core import Parrot, Context, Cog
import discord


class CaptureTheFlag(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.__required_nickname = "help"
        self.__required_guild_id = 988377761267736586
        self.__link_given = []

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self.__required_nickname not in str(after.nick):
            return
        if after.nick == self.__required_nickname and after.id not in self.__link_given:
            overwrites = {
                after.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            }
            await after.send("https://discord.gg/dw5B8V6b")
            self.__link_given.append(after.id)
    
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None and self.bot.get_guild(988381689136959508).get_member(message.author.id) is not None and message.content.lower() == "password":
            await message.author.send("https://discord.gg/Ag6qNAsD")
