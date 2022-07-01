from __future__ import annotations

from core import Parrot, Context
import discord

from akinator.async_aki import Akinator
import akinator


class AkiView(discord.ui.View):
    message: discord.Message

    def __init__(
        self,
        *,
        bot: Parrot,
        ctx: Context,
        game: Akinator,
        player: discord.Member,
        q: str,
    ):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx

        self.game = game
        self.player = player

        self.q_n = 1
        self.q = q

    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user == self.player:
            return True
        await interaction.response.send_message(
            content="This isn't your game!", ephemeral=True
        )
        return False

    async def is_game_ended(self) -> None:
        if self.game.progression <= 80:
            await self.game.win()
            self.stop()
            embed = discord.Embed(
                title=f"It's {self.game.first_guess['name']} ({self.game.first_guess['description']})! Was I correct?\n\t",
                color=self.bot.color,
                timestamp=self.message.created_at,
            )
            embed.set_image(url=f"{self.game.first_guess['absolute_picture_path']}")
            val = await self.ctx.prompt(embed=embed)
            if val is None:
                return
            if val:
                await self.message.channel.send(
                    f"{self.message.author.mention} Yayy! Guessed right huh!"
                )
            else:
                await self.message.channel.send(
                    f"{self.message.author.mention} uff! Kinda hard one!"
                )

    def generate_embed(self) -> discord.Embed:
        return (
            discord.Embed(color=self.bot.color, timestamp=self.message.created_at)
            .set_footer(text=f"{self.player}", icon_url=self.player.display_avatar.url)
            .add_field(name=f"Q. {self.q_n}", value=self.q)
        )

    @discord.ui.button(
        label="Yes",
        style=discord.ButtonStyle.green,
    )
    async def yes_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.q = await self.game.answer("yes")
        self.q_n += 1

        await self.message.edit(
            content=self.message.author.mention, embed=self.generate_embed(), view=self
        )

    @discord.ui.button(
        label="No",
        style=discord.ButtonStyle.green,
    )
    async def no_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.q = await self.game.answer("no")
        self.q_n += 1
        await self.is_game_ended()
        await self.message.edit(
            content=self.message.author.mention, embed=self.generate_embed(), view=self
        )

    @discord.ui.button(
        label="I don't know",
        style=discord.ButtonStyle.green,
    )
    async def idk_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.q = await self.game.answer("idk")
        self.q_n += 1
        await self.is_game_ended()
        await self.message.edit(
            content=self.message.author.mention, embed=self.generate_embed(), view=self
        )

    @discord.ui.button(
        label="Probably",
        style=discord.ButtonStyle.green,
    )
    async def probably_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.q = await self.game.answer("probably")
        self.q_n += 1
        await self.is_game_ended()
        await self.message.edit(
            content=self.message.author.mention, embed=self.generate_embed(), view=self
        )

    @discord.ui.button(
        label="Probably Not",
        style=discord.ButtonStyle.green,
    )
    async def probably_not_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.q = await self.game.answer("probably")
        self.q_n += 1
        await self.is_game_ended()
        await self.message.edit(
            content=self.message.author.mention, embed=self.generate_embed(), view=self
        )

    @discord.ui.button(label="Go Back", style=discord.ButtonStyle.blurple)
    async def go_back_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            self.q = await self.game.back()
        except akinator.CantGoBackAnyFurther:
            pass
        else:
            self.q_n -= 1
        finally:
            await self.is_game_ended()
            await self.message.edit(
                content=self.message.author.mention,
                embed=self.generate_embed(),
                view=self,
            )

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def quit_game(
        self, interaction: discord.Inteaction, button: discord.ui.Button
    ):
        self.stop()
        await self.message.delete()
