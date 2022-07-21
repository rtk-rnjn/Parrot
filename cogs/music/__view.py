from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

import discord
import wavelink
from core import Context, Parrot
from discord.ext import commands


class ModalInput(discord.ui.Modal, title="Name of Song"):
    name: discord.ui.TextInput = discord.ui.TextInput(
        label="Name",
        placeholder="Ex. Ice Cream - Blackpink",
        required=True,
        max_length=300,
    )

    def __init__(self, player: wavelink.Player, *, ctx: Context):
        super().__init__()
        self.player = player
        self.ctx = ctx

        self.bot = self.ctx.bot

    async def on_submit(self, interaction: discord.Interaction) -> None:

        cmd: commands.Command = self.bot.get_command("play")
        await interaction.response.send_message(f"Recieved `{self.name.value}`", ephemeral=True)

        try:
            await self.ctx.invoke(cmd, search=self.name.value)
        except commands.CommandError as e:
            return await self.__send_interal_error_response(interaction)

        await interaction.response.edit_message(
            content="Invoked `play` command",
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:  # type: ignore
        await interaction.response.send_message("Oops! Something went wrong.", ephemeral=True)

    async def __send_interal_error_response(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Running `loop` command from the context failed. Possible reasons:\n"
            "• The bot is not in a voice channel.\n"
            "• The bot is not in the same voice channel as you.\n"
            "• The bot is not playing music.\n"
            f"• You are missing DJ role or Manage Channels permission.\n",
            ephemeral=True,
        )


class MusicView(discord.ui.View):
    def __init__(self, vc: discord.VoiceChannel, *, timeout: Optional[float] = None, ctx: Context):
        super().__init__(timeout=timeout)
        self.vc = vc
        self.ctx = ctx

        self.bot: Parrot = self.ctx.bot
        self.player: wavelink.Player = self.ctx.voice_client

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [i.id for i in self.vc.members]:
            await interaction.response.send_message(
                "You must be in the bot's voice channel to use this command.", ephemeral=True
            )
            return False
        return True

    async def __like(self, user: Union[discord.User, discord.Member]):
        await self.bot.mongo.extra.user_misc.update_one(
            {"_id": user.id},
            {
                "$addToSet": {
                    "songs_liked": {
                        "id": self.player.track.id,
                        "song_name": getattr(self.player.track, "title"),
                        "url": getattr(self.player.track, "uri"),
                    }
                }
            },
            upsert=True,
        )
        await self.bot.mongo.extra.songs.update_one(
            {"id": self.player.track.id},
            {"$inc": {"likes": 1}},
            upsert=True,
        )

    async def __dislike(self, user: Union[discord.User, discord.Member]):
        await self.bot.mongo.extra.user_misc.update_one(
            {"_id": user.id},
            {
                "$addToSet": {
                    "songs_disliked": {
                        "id": self.player.track.id,
                        "song_name": getattr(self.player.track, "title"),
                        "url": getattr(self.player.track, "uri"),
                    }
                }
            },
            upsert=True,
        )
        await self.bot.mongo.extra.songs.update_one(
            {"id": self.player.track.id},
            {"$inc": {"dislikes": 1}},
            upsert=True,
        )

    async def __add_to_playlist(self, user: Union[discord.User, discord.Member]):
        await self.bot.mongo.extra.user_misc.update_one(
            {"_id": user.id},
            {
                "$addToSet": {
                    "playlist": {
                        "id": self.player.track.id,
                        "song_name": getattr(self.player.track, "title"),
                        "url": getattr(self.player.track, "uri"),
                    }
                }
            },
            upsert=True,
        )

    async def __remove_from_playlist(self, user: Union[discord.User, discord.Member]):
        await self.bot.mongo.extra.user_misc.update_one(
            {"_id": user.id},
            {
                "$pull": {
                    "playlist": {
                        "id": self.player.track.id,
                        "song_name": getattr(self.player.track, "title"),
                        "url": getattr(self.player.track, "uri"),
                    }
                }
            },
            upsert=True,
        )

    async def __send_interal_error_response(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Running `loop` command from the context failed. Possible reasons:\n"
            "• The bot is not in a voice channel.\n"
            "• The bot is not in the same voice channel as you.\n"
            "• The bot is not playing music.\n"
            f"• You are missing DJ role or Manage Channels permission.\n",
            ephemeral=True,
        )

    @discord.ui.button(
        custom_id="LOOP", emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
    )
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):

        cmd: commands.Command = self.bot.get_command("loop")
        try:
            await self.ctx.invoke(cmd)
        except commands.CommandError as e:
            return await self.__send_interal_error_response(interaction)
        await interaction.response.send_message("Invoked `loop` command.", ephemeral=True)

    @discord.ui.button(
        custom_id="LOOP_CURRENT",
        emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}",
    )
    async def loop_current(self, interaction: discord.Interaction, button: discord.ui.Button):

        cmd: commands.Command = self.bot.get_command("loop")
        try:
            await self.ctx.invoke(cmd, "current")
        except commands.CommandError as e:
            return await self.__send_interal_error_response(interaction)
        await interaction.response.send_message("Invoked `loop current` command.", ephemeral=True)

    @discord.ui.button(custom_id="SHUFFLE", emoji="\N{TWISTED RIGHTWARDS ARROWS}")
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):

        cmd: commands.Command = self.bot.get_command("shuffle")
        try:
            await self.ctx.invoke(cmd)
        except commands.CommandError as e:
            return await self.__send_interal_error_response(interaction)
        await interaction.response.send_message("Invoked `shuffle` command.", ephemeral=True)

    @discord.ui.button(custom_id="UPVOTE", emoji="\N{UPWARDS BLACK ARROW}")
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):

        await self.__like(interaction.user)
        await interaction.response.send_message("Added song to liked songs.", ephemeral=True)

    @discord.ui.button(custom_id="DOWNVOTE", emoji="\N{DOWNWARDS BLACK ARROW}")
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):

        await self.__dislike(interaction.user)
        await interaction.response.send_message("Removed song to liked songs.", ephemeral=True)

    @discord.ui.button(
        custom_id="PLAY_PAUSE",
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR}",
        row=1,
    )
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.player.is_paused():
            cmd: commands.Command = self.bot.get_command("resume")  # type: ignore
            try:
                await self.ctx.invoke(cmd)
            except commands.CommandError as e:
                return await self.__send_interal_error_response(interaction)
            await interaction.response.send_message("Invoked `resume` command.", ephemeral=True)
            return

        if self.player.is_playing():
            cmd: commands.Command = self.bot.get_command("pause")  # type: ignore
            try:
                await self.ctx.invoke(cmd)
            except commands.CommandError as e:
                return await self.__send_interal_error_response(interaction)
            await interaction.response.send_message("Invoked `pause` command.", ephemeral=True)
            return

        await interaction.response.send_modal(ModalInput(self.player, ctx=self.ctx))

    @discord.ui.button(custom_id="STOP", emoji="\N{BLACK SQUARE FOR STOP}", row=1)
    async def _stop(self, interaction: discord.Interaction, button: discord.ui.Button):

        cmd: commands.Command = self.bot.get_command("stop")
        try:
            await self.ctx.invoke(cmd)
        except commands.CommandError as e:
            return await self.__send_interal_error_response(interaction)
        await interaction.response.send_message("Invoked `stop` command.", ephemeral=True)

    @discord.ui.button(
        custom_id="SKIP", emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", row=1
    )
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):

        cmd: commands.Command = self.bot.get_command("skip")
        try:
            await self.ctx.invoke(cmd)
        except commands.CommandError as e:
            return await self.__send_interal_error_response(interaction)
        await interaction.response.send_message("Invoked `skip` command.", ephemeral=True)

    @discord.ui.button(custom_id="LOVE", emoji="\N{HEAVY BLACK HEART}", row=1)
    async def love(self, interaction: discord.Interaction, button: discord.ui.Button):

        await self.__add_to_playlist(interaction.user)
        await interaction.response.send_message("Added song to loved songs (Playlist).", ephemeral=True)

    @discord.ui.button(
        label="Filter",
        custom_id="FILTER",
        row=1,
    )
    async def _filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            view=MusicViewFilter(self.vc, timeout=self.timeout, ctx=self.ctx)
        )


class MusicViewFilter(discord.ui.View):
    def __init__(self, vc: discord.VoiceChannel, *, timeout: Optional[float] = None, ctx: Context):
        super().__init__(timeout=timeout)
        self.vc = vc
        self.ctx = ctx

        self.bot: Parrot = self.ctx.bot
        self.player: wavelink.Player = self.ctx.voice_client

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        dj_role = await self.ctx.dj_role()

        assert hasattr(interaction.user, "roles")

        if dj_role not in interaction.user.roles:  # type: ignore
            await interaction.response.send_message(
                "You must have the `DJ` role to use this command.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(custom_id="EQUALIZER", label="Equalizer", style=discord.ButtonStyle.red)
    async def equalizer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            view=_InternalMusicFilterView(
                options=["boost", "flat", "metal", "piano"],
                _type="Equalizer",
                timeout=self.timeout,
                player=self.player,
                vc=self.vc,
                ctx=self.ctx,
            )
        )

    @discord.ui.button(custom_id="CHANNELMIX", label="Channel Mix", style=discord.ButtonStyle.red)
    async def channel_mix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            view=_InternalMusicFilterView(
                options=["full_left", "full_right", "mono", "only_left", "only_right", "switch"],
                _type="ChannelMix",
                timeout=self.timeout,
                player=self.player,
                vc=self.vc,
                ctx=self.ctx,
            )
        )

    @discord.ui.button(custom_id="BACK", label="Back", style=discord.ButtonStyle.red)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            view=MusicView(self.vc, timeout=self.timeout, ctx=self.ctx)
        )


class _InternalMusicFilterView(discord.ui.View):
    def __init__(
        self,
        *,
        options: List[str],
        timeout: Optional[float],
        _type: str,
        player: wavelink.Player,
        vc: discord.VoiceChannel,
        ctx: Context,
    ):
        super().__init__(timeout=timeout)
        for option in options:
            self.add_item(_InternalMusicFilterButton(_type=_type, label=option, player=player))
        self.vc = vc
        self.ctx = ctx

    @discord.ui.button(custom_id="BACK", label="Back", style=discord.ButtonStyle.red)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            view=MusicViewFilter(self.vc, timeout=self.timeout, ctx=self.ctx)
        )


class _InternalMusicFilterButton(discord.ui.Button["_InternalMusicFilterView"]):
    def __init__(self, *, _type: str, label: str, player: wavelink.Player):
        super().__init__(
            label=label.title(),
            style=discord.ButtonStyle.blurple,
        )
        self._type = _type
        self._label = label
        self.player = player

    async def callback(self, interaction: discord.Interaction) -> Any:
        _class = getattr(wavelink, self._type.title())
        _filter = getattr(_class, self._label)
        await self.player.set_filter(wavelink.Filter(**{self._type: _filter}))

        await interaction.response.send_message(
            f"Filter added of Type: {self._type}.", ephemeral=True
        )
