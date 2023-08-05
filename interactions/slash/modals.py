from __future__ import annotations

from discord.interactions import Interaction

import discord
from core import Parrot, ParrotModal


class WhisperModal(ParrotModal):
    def __init__(self, message: discord.Message) -> None:
        super().__init__(title="Whisper")
        self.message = message

        self.text_input = discord.ui.TextInput(
            label="Whisper Message",
            placeholder="Type your message here...",
            min_length=10,
            max_length=200,
        )
        self.add_item(self.text_input)

    async def on_submit(self, interaction: Interaction[Parrot]) -> None:
        bot = interaction.client
        user_collection = bot.user_collections_ind

        msg = self.text_input.value

        query = {
            "_id": self.message.author.id,
        }

        update = {
            "$addToSet": {
                "whisper_messages": {
                    "message": msg,
                    "created_at": self.message.created_at,
                    "guild_id": self.message.guild.id,  # type: ignore
                    "channel_id": self.message.channel.id,
                    "message_id": self.message.id,
                    "author_id": self.message.author.id,
                },
            },
        }

        await user_collection.update_one(query, update, upsert=True)
        await interaction.response.send_message(
            f"{interaction.user.mention} whispered to {self.message.author.mention} successfully.",
            ephemeral=True,
        )
