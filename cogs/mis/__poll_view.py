from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from discord.interactions import Interaction

import discord
from core import Context, Parrot, ParrotModal, ParrotSelect, ParrotView
from utilities.strawpoll import DatePollOption, ImagePollOption, Media, TextPollOption, TimeRangePollOption
from utilities.time import ShortTime

options_lookup = {
    "text": TextPollOption,
    "image": ImagePollOption,
    "date": DatePollOption,
    "time_range": TimeRangePollOption,
}


def conveter_text(value: Any) -> TextPollOption:
    return TextPollOption(value=value, type="text")


def conveter_image(url: Any) -> ImagePollOption:
    return ImagePollOption(media=Media(url=url), type="image")


def convert_date(date: Any) -> DatePollOption:
    return DatePollOption(date=date, type="date")


def convert_time_range(start_time: Any, end_time: Any) -> TimeRangePollOption:
    return TimeRangePollOption(
        start_time=int(ShortTime(start_time).dt.timestamp()),
        end_time=int(ShortTime(end_time).dt.timestamp()),
        type="time_range",
    )


input_lookup: dict[str, tuple[str, list[discord.ui.TextInput], Callable]] = {
    "text": (
        "value",
        [
            discord.ui.TextInput(
                label="Enter the option for the poll.",
                min_length=1,
                max_length=100,
                custom_id="value",
            ),
        ],
        conveter_text,
    ),
    "image": (
        "url",
        [
            discord.ui.TextInput(
                label="Enter Image URL for the poll.",
                min_length=1,
                max_length=100,
                custom_id="url",
            ),
        ],
        conveter_image,
    ),
    "date": (
        "date",
        [
            discord.ui.TextInput(
                label="Enter Date for the poll.",
                placeholder="Date Format: YYYY-MM-DD",
                min_length=1,
                max_length=100,
                custom_id="date",
            ),
        ],
        convert_date,
    ),
    "time_range": (
        "time_range",
        [
            discord.ui.TextInput(
                label="Enter Start Time for the poll.",
                placeholder="Ex. 1h",
                min_length=1,
                max_length=100,
                custom_id="start_time",
            ),
            discord.ui.TextInput(
                label="Enter End Time for the poll.",
                placeholder="Ex. 1h",
                min_length=1,
                max_length=100,
                custom_id="end_time",
            ),
        ],
        convert_time_range,
    ),
}


class PollModal(ParrotModal):
    text: Callable[[Any], TextPollOption]
    image: Callable[[Any], ImagePollOption]
    date: Callable[[Any], DatePollOption]
    time_range: Callable[[Any, Any], TimeRangePollOption]

    def __init__(self, poll_type: str, view: PollView):
        super().__init__(title="Setting up Poll")
        self.poll_type = poll_type
        self.view = view

        data = input_lookup[poll_type]
        item_var, text_inputs, converter = data
        self.item_var = item_var
        for text_input in text_inputs:
            setattr(self, item_var, converter)
            setattr(self, f"item_{text_input.custom_id}", text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        assert isinstance(self.view, PollView)

        raw_data = []
        for item in self.children:
            if isinstance(item, discord.ui.TextInput):
                i: discord.ui.TextInput = getattr(self, f"item_{item.custom_id}")
                raw_data.append(i.value)

        response = input_lookup[self.poll_type][2](*raw_data)
        self.view.options.append(response)

        await interaction.followup.send(f"Added {self.poll_type} option.", ephemeral=True)


class PollSelect(ParrotSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select Type of Poll",
            options=[
                discord.SelectOption(label="Text Poll", value="text"),
                discord.SelectOption(label="Image Poll", value="image"),
                discord.SelectOption(label="Date Poll", value="date"),
                discord.SelectOption(label="Time Range Poll", value="time_range"),
            ],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        assert isinstance(self.view, PollView)

        await interaction.response.defer()
        self.view.poll_type = self.values[0]

        self.view.remove_item(self)


class PollView(ParrotView):
    def __init__(self, ctx: Context[Parrot]):
        super().__init__(ctx=ctx, timeout=120)
        self.bot = ctx.bot

        self.question = None
        self.options: list[TextPollOption | ImagePollOption | DatePollOption | TimeRangePollOption] = []
        self.poll_type: str = "text"

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Poll",
            description=self.question,
            color=discord.Color.blurple(),
        )

        for option in self.options:
            if isinstance(option, ImagePollOption | TextPollOption):
                embed.add_field(
                    name="Type: Text",
                    value=option.value,
                    inline=False,
                )
            elif isinstance(option, DatePollOption):
                embed.add_field(
                    name="Type: Date",
                    value=option.date,
                    inline=False,
                )
            elif isinstance(option, TimeRangePollOption):
                embed.add_field(
                    name="Type: Time Range",
                    value=f"Start Time: <t:{option.start_time}:R>\nEnd Time: <t:{option.end_time}:R>",
                    inline=False,
                )

        return embed

    @discord.ui.button(label="Add/Edit Question")
    async def add_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter the question for the poll.", ephemeral=True)

        def check(m: discord.Message):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg: discord.Message = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to respond.", ephemeral=True)
            return

        self.question = msg.content
        await msg.delete(delay=0)
        await self.message.edit(embed=self.embed, view=self)

    @discord.ui.button(label="Add/Edit Option")
    async def add_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        item = PollSelect()
        self.add_item(item)
        await interaction.response.send_message("Enter the option for the poll.", ephemeral=True)
        await self.message.edit(embed=self.embed, view=self)

    async def start(self):
        self.message = await self.ctx.send("Setting up Poll", view=self)
        self.message = await self.message.edit(embed=self.embed, view=self)
