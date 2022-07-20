from __future__ import annotations

from discord.ext import commands

class KaraokeFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    level: float = 1
    mono_level: float = 1
    filter_band: float = 220
    filter_width: float = 100


class TimescaleFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    speed: float = 1
    pitch: float = 1
    rate: float = 1

class TremoloFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    frequency: float = 2.0
    depth: float = 0.5

class VibratoFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    frequency: float = 2.0
    depth: float = 0.5

class RotationFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    speed: float = 5

class DistortionFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    sin_offset: float = 0
    sin_scale: float = 1
    cos_offset: float = 0
    cos_scale: float = 1
    tan_offset: float = 0
    tan_scale: float = 1
    offset: float = 0
    scale: float = 1

class ChannelMixFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    left_to_left: float = 1
    left_to_right: float = 0
    right_to_left: float = 0
    right_to_right: float = 1

class LowPassFlag(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    smoothing: float = 20