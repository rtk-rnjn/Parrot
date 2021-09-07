from discord.ext import commands
import discord

class GetMembers(discord.ui.View):
    def __init__(self, host):
        super().__init__(timeout=180)
        # self.value = []
        self.users = []
        self.host = host

    @discord.ui.button(label='Join the game', style=discord.ButtonStyle.green)
    async def join(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id not in self.users:
            await interaction.response.send_message("You joined the Game", ephemeral=True)
            self.users.append(interaction.user.id)
        else:
            await interaction.response.send_message("You are already in the game", ephemeral=True)

    @discord.ui.button(label='Leave the game', style=discord.ButtonStyle.danger)
    async def leave(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id == self.host.id:
            await interaction.response.send_message("You can't leave the game as you are the host", ephemeral=True)
        else:
            try:
                self.users.remove(interaction.user.id)
            except ValueError:
                await interaction.reponse.send_message("You aren't in the game", ephemeral=True)
            else:
                await interaction.response.send_message("Removed from the list", ephemeral=True)

    @discord.ui.button(label='Start the game', style=discord.ButtonStyle.grey)
    async def start(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id == self.host.id:
            await interaction.response.send_message('Starting the game...')
            self.stop()
        else:
            await interaction.response.send_message("You can not start the game as you are not the host", ephemeral=True)


class Game(discord.ui.view):
    def __init__(self, users: list):
        self.users = users
        self.cards = {}

    @disocrd.ui.button(label='Ready', style=discord.ButtonStyle.green)
    async def ready(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id not in self.users:
            await interaction.response.send_message(f"{interaction.user.mention} you are not playing this game, so stay away", ephemeral=True)
        else:
            self.cards[interaction.user.id] = self.get_cards()
            await interaction.response.send_message(f"{self.cards[interaction.user.id]}", ephemeral=True)
    
    @disocrd.ui.button(label='Leave', style=discord.ButtonStyle.danger)
    async def leave(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass