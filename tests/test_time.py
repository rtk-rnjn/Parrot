"""Tests for the human-time parsing module.

Assumes the module is importable as ``utils.human_time`` (it uses a relative
``.formats`` import, so it must live inside a package). Adjust the import
below if yours is elsewhere.

Tests marked ``xfail(strict=True)`` document *real bugs* found while writing
this suite. They turn into hard failures once the bug is fixed, which is your
cue to remove the marker.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta
from discord import app_commands
from discord.ext import commands

from core.utils.time import (
    BadTimeTransform,
    FriendlyTimeResult,
    FutureTime,
    HumanTime,
    RelativeDelta,
    ShortTime,
    Time,
    TimeTransformer,
    UserFriendlyTime,
    human_timedelta,
)
from tests.helpers import NOW, UTC, make_ctx, make_interaction, reminder_with, run

TD = datetime.timedelta
KOLKATA = ZoneInfo("Asia/Kolkata")  # has a `.key`, so dateparser sees the real zone
IST_FIXED = datetime.timezone(TD(hours=5, minutes=30))  # no `.key` -> exercises the "UTC" fallback
NEW_YORK = ZoneInfo("America/New_York")


class Upper(commands.Converter):
    async def convert(self, ctx, argument):
        return argument.upper()


class TestShortTimeGrammar:
    @pytest.mark.parametrize(
        ("text", "delta"),
        [
            # seconds
            ("1s", TD(seconds=1)),
            ("1sec", TD(seconds=1)),
            ("1secs", TD(seconds=1)),
            ("1second", TD(seconds=1)),
            ("45seconds", TD(seconds=45)),
            # minutes (note: bare "m" is MINUTES, months need "mo")
            ("1m", TD(minutes=1)),
            ("1min", TD(minutes=1)),
            ("1mins", TD(minutes=1)),
            ("1minute", TD(minutes=1)),
            ("5minutes", TD(minutes=5)),
            ("1M", TD(minutes=1)),
            # hours
            ("1h", TD(hours=1)),
            ("1hr", TD(hours=1)),
            ("1hrs", TD(hours=1)),
            ("1hour", TD(hours=1)),
            ("3hours", TD(hours=3)),
            # days / weeks
            ("1d", TD(days=1)),
            ("1day", TD(days=1)),
            ("3days", TD(days=3)),
            ("1w", TD(weeks=1)),
            ("1week", TD(weeks=1)),
            ("2weeks", TD(weeks=2)),
            # combinations
            ("1h30m", TD(hours=1, minutes=30)),
            ("1d12h", TD(days=1, hours=12)),
            ("1w2d3h4m5s", TD(weeks=1, days=2, hours=3, minutes=4, seconds=5)),
            # no normalisation required
            ("90m", TD(minutes=90)),
            ("3600s", TD(hours=1)),
            ("0030m", TD(minutes=30)),
            # case-insensitive
            ("1H30M", TD(hours=1, minutes=30)),
            ("2DAYS", TD(days=2)),
            # surrounding whitespace is stripped
            ("  1h  ", TD(hours=1)),
        ],
    )
    def test_fixed_length_units(self, text, delta):
        assert ShortTime(text, now=NOW).dt - NOW == delta

    @pytest.mark.parametrize("text", ["1mo", "1mon", "1month", "1months"])
    def test_month_spellings(self, text):
        assert ShortTime(text, now=NOW).dt == datetime.datetime(2026, 11, 3, 12, 0, tzinfo=UTC)

    @pytest.mark.parametrize("text", ["1y", "1year", "1years"])
    def test_year_spellings(self, text):
        assert ShortTime(text, now=NOW).dt == datetime.datetime(2027, 10, 3, 12, 0, tzinfo=UTC)

    def test_every_unit_at_once(self):
        got = ShortTime("1y2mo3w4d5h6m7s", now=NOW).dt
        assert got == NOW + relativedelta(years=1, months=2, weeks=3, days=4, hours=5, minutes=6, seconds=7)

    def test_month_end_clamps(self):
        jan31 = datetime.datetime(2026, 1, 31, tzinfo=UTC)
        assert ShortTime("1mo", now=jan31).dt.date() == datetime.date(2026, 2, 28)

    def test_leap_day_plus_one_year_clamps(self):
        leap = datetime.datetime(2024, 2, 29, tzinfo=UTC)
        assert ShortTime("1y", now=leap).dt.date() == datetime.date(2025, 2, 28)

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "abc",
            "1",
            "h",
            "1x",
            "-1h",
            "1.5h",
            "0s",
            "0h0m",  # all-zero is rejected
            "1h 30m",  # no internal spaces
            "30m1h",  # units must be in descending order
            "1h garbage",
            "garbage 1h",
            "1h1h",  # duplicate unit
        ],
    )
    def test_invalid(self, text):
        with pytest.raises(commands.BadArgument, match=r"invalid time provided"):
            ShortTime(text, now=NOW)


class TestShortTimeDiscordTimestamps:
    TS = 1_700_000_000
    EXPECTED = datetime.datetime.fromtimestamp(TS, UTC)

    @pytest.mark.parametrize("style", ["", ":R", ":F", ":f", ":D", ":d", ":T", ":t"])
    def test_all_styles(self, style):
        assert ShortTime(f"<t:{self.TS}{style}>", now=NOW).dt == self.EXPECTED

    def test_whitespace_stripped(self):
        assert ShortTime(f"  <t:{self.TS}>  ", now=NOW).dt == self.EXPECTED

    def test_converted_to_users_timezone(self):
        dt = ShortTime(f"<t:{self.TS}>", now=NOW, tzinfo=KOLKATA).dt
        assert dt == self.EXPECTED
        assert dt.utcoffset() == TD(hours=5, minutes=30)

    @pytest.mark.parametrize(
        "text",
        ["<t:abc>", "<t:>", "<t:1700000000:x>", "<t:-5>", f"<t:{TS}> hello", f"hello <t:{TS}>", "t:1700000000"],
    )
    def test_invalid(self, text):
        with pytest.raises(commands.BadArgument, match=r"invalid time provided"):
            ShortTime(text, now=NOW)

    def test_past_timestamps_are_allowed_here(self):
        # ShortTime doesn't police the past; callers (FutureTime etc.) do.
        assert ShortTime("<t:0>", now=NOW).dt == datetime.datetime(1970, 1, 1, tzinfo=UTC)


class TestShortTimeTimezones:
    def test_default_tz_is_utc(self):
        assert ShortTime("1h", now=NOW).dt.utcoffset() == TD(0)

    def test_result_is_in_requested_tz_and_same_instant(self):
        dt = ShortTime("1h", now=NOW, tzinfo=KOLKATA).dt
        assert dt == NOW + TD(hours=1)
        assert (dt.hour, dt.minute) == (18, 30)
        assert dt.utcoffset() == TD(hours=5, minutes=30)

    def test_fixed_offset_tz(self):
        dt = ShortTime("1h", now=NOW, tzinfo=IST_FIXED).dt
        assert dt == NOW + TD(hours=1)
        assert dt.utcoffset() == TD(hours=5, minutes=30)

    def test_naive_now_is_treated_as_utc(self):
        naive = datetime.datetime(2026, 10, 3, 12, 0, tzinfo=datetime.UTC)
        assert ShortTime("1h", now=naive).dt == NOW + TD(hours=1)

    def test_now_defaults_to_real_clock(self):
        before = datetime.datetime.now(UTC)
        dt = ShortTime("1h").dt
        after = datetime.datetime.now(UTC)
        assert before + TD(hours=1) <= dt <= after + TD(hours=1)

    def test_dst_gap_is_resolved_not_left_imaginary(self):
        # 2026-03-08 02:30 doesn't exist in New York (clocks jump 02:00 -> 03:00).
        now = datetime.datetime(2026, 3, 7, 2, 30, tzinfo=NEW_YORK)
        dt = ShortTime("1d", now=now, tzinfo=NEW_YORK).dt
        assert (dt.hour, dt.minute) == (3, 30)
        assert dt.utcoffset() == TD(hours=-4)


class TestShortTimeConvert:
    def test_no_reminder_cog_uses_utc(self):
        st = run(ShortTime.convert(make_ctx(None), "1h"))
        assert isinstance(st, ShortTime)
        assert st.dt == NOW + TD(hours=1)

    def test_uses_users_tz_and_message_timestamp(self):
        reminder = reminder_with(KOLKATA)
        created = datetime.datetime(2030, 1, 1, tzinfo=UTC)
        st = run(ShortTime.convert(make_ctx(reminder, user_id=7, created_at=created), "2h"))
        reminder.get_tzinfo.assert_awaited_once_with(7)
        assert st.dt == created + TD(hours=2)
        assert st.dt.utcoffset() == TD(hours=5, minutes=30)

    def test_bad_input(self):
        with pytest.raises(commands.BadArgument):
            run(ShortTime.convert(make_ctx(None), "nope"))


class TestRelativeDelta:
    def test_is_both_transformer_and_converter(self):
        rd = RelativeDelta()
        assert isinstance(rd, app_commands.Transformer)
        assert isinstance(rd, commands.Converter)

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1h30m", relativedelta(hours=1, minutes=30)),
            ("90m", relativedelta(hours=1, minutes=30)),  # relativedelta normalises
            ("2w", relativedelta(days=14)),
            ("1y2mo", relativedelta(years=1, months=2)),
            ("  5s ", relativedelta(seconds=5)),
            ("1M", relativedelta(minutes=1)),
        ],
    )
    def test_convert(self, text, expected):
        assert run(RelativeDelta().convert(make_ctx(), text)) == expected

    def test_transform_matches_convert(self):
        assert run(RelativeDelta().transform(make_interaction(), "1d")) == relativedelta(days=1)

    def test_zero_is_accepted_unlike_shorttime(self):
        # Pinning current behaviour: "0s" gives an empty delta here but is
        # rejected by ShortTime. Delete this test if you decide to unify them.
        assert run(RelativeDelta().convert(make_ctx(), "0s")) == relativedelta()

    @pytest.mark.parametrize("text", ["", "   ", "abc", "1x", "1h 30m", "30m1h"])
    def test_convert_invalid_raises_bad_argument(self, text):
        with pytest.raises(commands.BadArgument, match=r"invalid time provided") as exc:
            run(RelativeDelta().convert(make_ctx(), text))
        assert exc.value.__suppress_context__ is True

    @pytest.mark.parametrize("text", ["", "abc", "1x"])
    def test_transform_invalid_raises_app_command_error(self, text):
        with pytest.raises(app_commands.AppCommandError, match=r"invalid time provided") as exc:
            run(RelativeDelta().transform(make_interaction(), text))
        assert exc.value.__suppress_context__ is True


class TestHumanTime:
    def test_tomorrow_keeps_time_of_day(self):
        ht_ = HumanTime("tomorrow", now=NOW)
        assert ht_.dt == datetime.datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
        assert ht_._past is False

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("in 2 hours", NOW + TD(hours=2)),
            ("in 3 days", NOW + TD(days=3)),
            ("3 days", NOW + TD(days=3)),  # the example in the error hint must work
            ("in 1 month", datetime.datetime(2026, 11, 3, 12, tzinfo=UTC)),
            ("next week", NOW + TD(weeks=1)),
            ("2026-12-25", datetime.datetime(2026, 12, 25, tzinfo=UTC)),
        ],
    )
    def test_future_phrases(self, text, expected):
        parsed = HumanTime(text, now=NOW)
        assert parsed.dt == expected
        assert parsed._past is False

    def test_weekday_prefers_the_future(self):
        # NOW is a Saturday; "friday" must be the *next* Friday.
        parsed = HumanTime("friday", now=NOW)
        assert parsed.dt.date() == datetime.date(2026, 10, 9)
        assert parsed.dt.weekday() == 4
        assert parsed._past is False

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("yesterday", NOW - TD(days=1)),
            ("3 days ago", NOW - TD(days=3)),
        ],
    )
    def test_past_phrases_are_flagged(self, text, expected):
        parsed = HumanTime(text, now=NOW)
        assert parsed.dt == expected
        assert parsed._past is True

    def test_now_counts_as_past(self):
        # `<=`: an instant equal to the base is "past", so FutureTime("now") fails.
        parsed = HumanTime("now", now=NOW)
        assert parsed.dt == NOW
        assert parsed._past is True

    @pytest.mark.parametrize("text", ["", "   ", "asdf qwerty", "tomorrow buy milk", "1h garbage"])
    def test_unparseable(self, text):
        with pytest.raises(commands.BadArgument, match=r"invalid time provided"):
            HumanTime(text, now=NOW)

    def test_error_hint_mentions_examples(self):
        with pytest.raises(commands.BadArgument) as exc:
            HumanTime("asdf qwerty", now=NOW)
        assert '"tomorrow"' in str(exc.value)
        assert '"3 days"' in str(exc.value)

    def test_named_timezone_is_respected(self):
        # 12:00 UTC is 17:30 in Kolkata; "tomorrow" keeps that wall-clock time.
        dt = HumanTime("tomorrow", now=NOW, tzinfo=KOLKATA).dt
        assert dt.utcoffset() == TD(hours=5, minutes=30)
        assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 10, 4, 17, 30)

    def test_fixed_offset_timezone_gives_correct_instant(self):
        dt = HumanTime("in 2 hours", now=NOW, tzinfo=IST_FIXED).dt
        assert dt == NOW + TD(hours=2)
        assert dt.utcoffset() == TD(hours=5, minutes=30)

    def test_naive_now_is_treated_as_utc(self):
        naive = datetime.datetime(2026, 10, 3, 12, 0, tzinfo=datetime.UTC)
        assert HumanTime("in 2 hours", now=naive).dt == NOW + TD(hours=2)

    def test_convert(self):
        reminder = reminder_with(KOLKATA)
        got = run(HumanTime.convert(make_ctx(reminder, user_id=3), "in 2 hours"))
        reminder.get_tzinfo.assert_awaited_once_with(3)
        assert isinstance(got, HumanTime)
        assert got.dt == NOW + TD(hours=2)

    def test_convert_without_reminder_cog(self):
        got = run(HumanTime.convert(make_ctx(None), "tomorrow"))
        assert got.dt.utcoffset() == TD(0)


class TestTime:
    def test_is_a_humantime(self):
        assert issubclass(Time, HumanTime)

    def test_short_form_takes_priority(self):
        t = Time("1h30m", now=NOW)
        assert t.dt == NOW + TD(hours=1, minutes=30)
        assert t._past is False

    def test_discord_timestamp_via_short_path(self):
        ts = int((NOW + TD(hours=1)).timestamp())
        assert Time(f"<t:{ts}:R>", now=NOW).dt == NOW + TD(hours=1)

    def test_falls_back_to_natural_language(self):
        t = Time("tomorrow", now=NOW)
        assert t.dt == NOW + TD(days=1)
        assert t._past is False

    def test_past_natural_language_is_flagged_not_rejected(self):
        t = Time("3 days ago", now=NOW)
        assert t._past is True
        assert t.dt == NOW - TD(days=3)

    def test_garbage_raises_humantime_error(self):
        with pytest.raises(commands.BadArgument, match=r"invalid time provided"):
            Time("asdf qwerty", now=NOW)

    def test_tzinfo_threaded_through_both_paths(self):
        assert Time("1h", now=NOW, tzinfo=KOLKATA).dt.utcoffset() == TD(hours=5, minutes=30)
        assert Time("tomorrow", now=NOW, tzinfo=KOLKATA).dt.utcoffset() == TD(hours=5, minutes=30)


class TestFutureTime:
    @pytest.mark.parametrize("text", ["1h", "2d", "tomorrow", "in 3 days"])
    def test_future_accepted(self, text):
        assert FutureTime(text, now=NOW).dt > NOW

    @pytest.mark.parametrize("text", ["yesterday", "3 days ago", "now"])
    def test_past_or_present_rejected(self, text):
        with pytest.raises(commands.BadArgument, match=r"this time is in the past"):
            FutureTime(text, now=NOW)

    def test_garbage(self):
        with pytest.raises(commands.BadArgument, match=r"invalid time provided"):
            FutureTime("asdf qwerty", now=NOW)


class TestTimeTransformer:
    def transform(self, value, **kw):
        return run(TimeTransformer().transform(make_interaction(**kw), value))

    def test_bad_time_transform_is_app_command_error(self):
        assert issubclass(BadTimeTransform, app_commands.AppCommandError)

    def test_short(self):
        assert self.transform("1h") == NOW + TD(hours=1)

    def test_natural_language(self):
        assert self.transform("tomorrow") == NOW + TD(days=1)

    def test_applies_users_timezone(self):
        reminder = reminder_with(KOLKATA)
        dt = self.transform("tomorrow", reminder=reminder, user_id=9)
        reminder.get_tzinfo.assert_awaited_once_with(9)
        assert dt.utcoffset() == TD(hours=5, minutes=30)
        assert (dt.day, dt.hour, dt.minute) == (4, 17, 30)

    @pytest.mark.parametrize("text", ["yesterday", "3 days ago"])
    def test_past_rejected(self, text):
        with pytest.raises(BadTimeTransform, match=r"this time is in the past") as exc:
            self.transform(text)
        assert exc.value.__suppress_context__ is True

    def test_garbage_rejected(self):
        with pytest.raises(BadTimeTransform, match=r"invalid time provided"):
            self.transform("asdf qwerty")


class TestFriendlyTimeResult:
    def test_init_defaults(self):
        r = FriendlyTimeResult(NOW)
        assert r.dt == NOW
        assert r.arg == ""

    def test_uses_slots(self):
        r = FriendlyTimeResult(NOW)
        assert not hasattr(r, "__dict__")
        with pytest.raises(AttributeError):
            r.other = 1  # type: ignore[attr-defined]

    def ensure(self, dt, uft, remaining, now=NOW):
        r = FriendlyTimeResult(dt)
        run(r.ensure_constraints(make_ctx(), uft, now, remaining))
        return r

    def test_past_rejected(self):
        with pytest.raises(commands.BadArgument, match=r"This time is in the past."):
            self.ensure(NOW - TD(seconds=1), UserFriendlyTime(), "x")

    def test_exactly_now_is_allowed(self):
        assert self.ensure(NOW, UserFriendlyTime(), "x").arg == "x"

    def test_past_is_checked_before_missing_argument(self):
        with pytest.raises(commands.BadArgument, match=r"in the past"):
            self.ensure(NOW - TD(hours=1), UserFriendlyTime(), "")

    def test_missing_argument(self):
        with pytest.raises(commands.BadArgument, match=r"Missing argument after the time."):
            self.ensure(NOW + TD(hours=1), UserFriendlyTime(), "")

    def test_default_fills_missing_argument(self):
        assert self.ensure(NOW + TD(hours=1), UserFriendlyTime(default="..."), "").arg == "..."

    def test_empty_string_default_is_still_a_default(self):
        # `default is None` is the check, so "" counts as a real default.
        assert self.ensure(NOW + TD(hours=1), UserFriendlyTime(default=""), "").arg == ""

    def test_remaining_wins_over_default(self):
        assert self.ensure(NOW + TD(hours=1), UserFriendlyTime(default="d"), "real").arg == "real"

    def test_converter_applied_to_remaining(self):
        assert self.ensure(NOW + TD(hours=1), UserFriendlyTime(Upper), "hi").arg == "HI"

    def test_converter_applied_to_default(self):
        assert self.ensure(NOW + TD(hours=1), UserFriendlyTime(Upper, default="dflt"), "").arg == "DFLT"


class TestUserFriendlyTimeInit:
    def test_defaults(self):
        uft = UserFriendlyTime()
        assert uft.converter is None
        assert uft.default is None

    def test_converter_class_is_instantiated(self):
        assert isinstance(UserFriendlyTime(Upper).converter, Upper)

    def test_converter_instance_is_kept(self):
        inst = Upper()
        assert UserFriendlyTime(inst).converter is inst

    def test_default_stored(self):
        assert UserFriendlyTime(default="x").default == "x"

    @pytest.mark.parametrize("bad", [str, int, "not a converter", object(), 5])
    def test_non_converter_rejected(self, bad):
        with pytest.raises(TypeError, match=r"commands.Converter subclass necessary."):
            UserFriendlyTime(bad)


class TestUserFriendlyTimeConvert:
    def convert(self, argument, *, ctx=None, **kw):
        return run(UserFriendlyTime(**kw).convert(ctx or make_ctx(), argument))

    def test_short_then_text(self):
        r = self.convert("1h buy milk")
        assert r.dt == NOW + TD(hours=1)
        assert r.arg == "buy milk"

    def test_combined_short_then_text(self):
        r = self.convert("1h30m do the thing")
        assert r.dt == NOW + TD(hours=1, minutes=30)
        assert r.arg == "do the thing"

    def test_short_only_without_default_is_missing_argument(self):
        with pytest.raises(commands.BadArgument, match=r"Missing argument after the time."):
            self.convert("1h")

    def test_short_only_with_default(self):
        r = self.convert("1h", default="reminder")
        assert r.arg == "reminder"

    def test_converter_runs_on_remaining(self):
        assert self.convert("1h buy milk", converter=Upper).arg == "BUY MILK"

    def test_calendar_units(self):
        r = self.convert("1mo take out trash")
        assert r.dt == datetime.datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
        assert r.arg == "take out trash"

    def test_bare_m_is_minutes(self):
        assert self.convert("5m tea").dt == NOW + TD(minutes=5)

    def test_zero_short_time_falls_through_to_natural_language(self):
        # "0s ..." isn't a usable short time; whole string then goes to dateparser and fails.
        with pytest.raises(commands.BadArgument, match=r"Invalid time provided"):
            self.convert("0s do thing")

    def test_users_timezone_applied_and_awaited_once(self):
        reminder = reminder_with(KOLKATA)
        r = self.convert("2h x", ctx=make_ctx(reminder, user_id=11))
        reminder.get_tzinfo.assert_awaited_once_with(11)
        assert r.dt == NOW + TD(hours=2)
        assert r.dt.utcoffset() == TD(hours=5, minutes=30)

    def test_discord_timestamp_then_text(self):
        ts = int((NOW + TD(hours=2)).timestamp())
        r = self.convert(f"<t:{ts}:R> call mum")
        assert r.dt == NOW + TD(hours=2)
        assert r.arg == "call mum"

    def test_discord_timestamp_only_with_default(self):
        ts = int((NOW + TD(hours=2)).timestamp())
        assert self.convert(f"<t:{ts}>", default="ping").arg == "ping"

    def test_discord_timestamp_only_without_default(self):
        ts = int((NOW + TD(hours=2)).timestamp())
        with pytest.raises(commands.BadArgument, match=r"Missing argument"):
            self.convert(f"<t:{ts}>")

    def test_past_discord_timestamp_rejected(self):
        with pytest.raises(commands.BadArgument, match=r"This time is in the past."):
            self.convert("<t:1700000000> hi")

    def test_past_discord_timestamp_reports_past_not_missing(self):
        with pytest.raises(commands.BadArgument, match=r"in the past"):
            self.convert("<t:1700000000>")

    def test_discord_timestamp_converted_to_user_tz(self):
        ts = int((NOW + TD(hours=2)).timestamp())
        r = self.convert(f"<t:{ts}> x", ctx=make_ctx(reminder_with(KOLKATA)))
        assert r.dt.utcoffset() == TD(hours=5, minutes=30)

    def test_natural_language_needs_a_default(self):
        r = self.convert("tomorrow", default="reminder")
        assert r.dt == NOW + TD(days=1)
        assert r.arg == "reminder"

    def test_natural_language_without_default_is_missing_argument(self):
        with pytest.raises(commands.BadArgument, match=r"Missing argument after the time."):
            self.convert("tomorrow")

    def test_natural_language_runs_default_through_converter(self):
        assert self.convert("tomorrow", default="dflt", converter=Upper).arg == "DFLT"

    def test_natural_language_in_the_past_rejected(self):
        with pytest.raises(commands.BadArgument, match=r"This time is in the past."):
            self.convert("yesterday", default="x")

    def test_natural_language_user_tz(self):
        r = self.convert("tomorrow", default="x", ctx=make_ctx(reminder_with(KOLKATA)))
        assert (r.dt.day, r.dt.hour, r.dt.minute) == (4, 17, 30)

    @pytest.mark.parametrize("text", ["", "   ", "asdf qwerty"])
    def test_unparseable(self, text):
        with pytest.raises(commands.BadArgument, match=r"Invalid time provided"):
            self.convert(text, default="x")

    def test_natural_language_followed_by_text_is_not_supported(self):
        # Pinning *current, deliberate* behaviour ("whole argument as time"):
        # only short-forms and Discord timestamps may be followed by text.
        # "!remind tomorrow buy milk" therefore fails -- worth a conscious decision.
        with pytest.raises(commands.BadArgument, match=r"Invalid time provided"):
            self.convert("tomorrow buy milk", default="x")

    def test_result_type(self):
        assert isinstance(self.convert("1h x"), FriendlyTimeResult)


SRC = datetime.datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def htd(delta_or_dt, **kw):
    dt = SRC + delta_or_dt if isinstance(delta_or_dt, TD) else delta_or_dt
    return human_timedelta(dt, source=SRC, **kw)


class TestHumanTimedelta:
    @pytest.mark.parametrize(
        ("delta", "expected"),
        [
            (TD(seconds=1), "1 second"),
            (TD(seconds=2), "2 seconds"),
            (TD(minutes=1), "1 minute"),
            (TD(hours=1), "1 hour"),
            (TD(hours=2), "2 hours"),
            (TD(days=1), "1 day"),
            (TD(days=2), "2 days"),
            (TD(hours=1, minutes=30), "1 hour and 30 minutes"),
            (TD(hours=1, minutes=30, seconds=5), "1 hour, 30 minutes and 5 seconds"),
        ],
    )
    def test_future_units_and_plurals(self, delta, expected):
        assert htd(delta) == expected

    @pytest.mark.parametrize(
        ("delta", "expected"),
        [
            (TD(days=7), "1 week"),
            (TD(days=8), "1 week and 1 day"),
            (TD(days=10), "1 week and 3 days"),
            (TD(days=14), "2 weeks"),
            (TD(days=15, hours=2), "2 weeks, 1 day and 2 hours"),
        ],
    )
    def test_weeks_are_split_out_of_days(self, delta, expected):
        assert htd(delta) == expected

    def test_months_and_years(self):
        assert htd(datetime.datetime(2026, 11, 3, 12, tzinfo=UTC)) == "1 month"
        assert htd(datetime.datetime(2027, 10, 3, 12, tzinfo=UTC)) == "1 year"
        assert htd(datetime.datetime(2028, 10, 3, 12, tzinfo=UTC)) == "2 years"

    LONG = datetime.datetime(2027, 12, 6, 16, 0, tzinfo=UTC)  # +1y 2mo 3d 4h

    def test_default_accuracy_is_three(self):
        assert htd(self.LONG) == "1 year, 2 months and 3 days"

    @pytest.mark.parametrize(
        ("accuracy", "expected"),
        [
            (1, "1 year"),
            (2, "1 year and 2 months"),
            (4, "1 year, 2 months, 3 days and 4 hours"),
            (None, "1 year, 2 months, 3 days and 4 hours"),
        ],
    )
    def test_accuracy(self, accuracy, expected):
        assert htd(self.LONG, accuracy=accuracy) == expected

    def test_accuracy_counts_weeks_as_a_unit(self):
        assert htd(TD(days=10, hours=2), accuracy=1) == "1 week"
        assert htd(TD(days=10, hours=2), accuracy=2) == "1 week and 3 days"

    @pytest.mark.parametrize(
        ("delta", "expected"),
        [
            (TD(hours=1, minutes=30, seconds=5), "1h 30m 5s"),
            (TD(days=10), "1w 3d"),
            (TD(days=14), "2w"),
        ],
    )
    def test_brief(self, delta, expected):
        assert htd(delta, brief=True) == expected

    def test_brief_months_years(self):
        assert htd(self.LONG, brief=True) == "1y 2mo 3d"
        assert htd(self.LONG, brief=True, accuracy=None) == "1y 2mo 3d 4h"

    @pytest.mark.parametrize(
        ("delta", "expected"),
        [
            (-TD(seconds=1), "1 second ago"),
            (-TD(hours=2), "2 hours ago"),
            (-TD(days=10), "1 week and 3 days ago"),
        ],
    )
    def test_past_gets_ago(self, delta, expected):
        assert htd(delta) == expected

    def test_past_brief(self):
        assert htd(-TD(days=10), brief=True) == "1w 3d ago"

    def test_suffix_false_drops_ago(self):
        assert htd(-TD(hours=2), suffix=False) == "2 hours"

    def test_future_never_gets_a_prefix_or_suffix(self):
        assert htd(TD(hours=2)) == "2 hours"

    def test_past_and_future_magnitudes_match(self):
        delta = TD(days=3, hours=4)
        assert htd(-delta) == htd(delta) + " ago"

    def test_identical_is_now(self):
        assert htd(SRC) == "now"

    @pytest.mark.parametrize("delta", [TD(milliseconds=500), -TD(milliseconds=500)])
    def test_sub_second_is_now_without_ago(self, delta):
        assert htd(delta) == "now"

    @pytest.mark.parametrize("brief", [True, False])
    def test_now_ignores_brief(self, brief):
        assert htd(SRC, brief=brief) == "now"

    def test_naive_dt_is_treated_as_utc(self):
        assert human_timedelta(datetime.datetime(2026, 10, 3, 14, 0, tzinfo=datetime.UTC), source=SRC) == "2 hours"

    def test_non_utc_dt_is_compared_by_instant(self):
        two_hours_later_in_ist = (SRC + TD(hours=2)).astimezone(KOLKATA)
        assert human_timedelta(two_hours_later_in_ist, source=SRC) == "2 hours"

    def test_naive_source_is_treated_as_utc(self):
        naive_src = datetime.datetime(2026, 10, 3, 12, 0, tzinfo=datetime.UTC)
        assert human_timedelta(SRC + TD(hours=2), source=naive_src) == "2 hours"

    def test_source_defaults_to_real_clock(self):
        target = datetime.datetime.now(UTC) + TD(hours=2, minutes=1)
        assert human_timedelta(target, accuracy=1) == "2 hours"
        target = datetime.datetime.now(UTC) - TD(days=3, hours=1)
        assert human_timedelta(target, accuracy=1) == "3 days ago"


class TestKnownBugs:
    @pytest.mark.xfail(
        strict=True,
        reason="Leading short-time match has no word boundary: '1st of the month ...' is read "
        "as 1 second + 't of the month ...'. Any ordinal ending in 'st' is affected.",
    )
    @pytest.mark.parametrize("text", ["1st of the month pay rent", "21st birthday party"])
    def test_ordinals_are_not_short_times(self, text):
        # Acceptable fixes: raise BadArgument, or at least don't schedule +1s / +21s.
        try:
            r = run(UserFriendlyTime(default="x").convert(make_ctx(), text))
        except commands.BadArgument:
            return
        assert r.dt - NOW not in (TD(seconds=1), TD(seconds=21))

    @pytest.mark.xfail(
        strict=True,
        reason="Absurdly large values (years, Discord timestamps) make arrow raise ValueError "
        "instead of BadArgument, so users get a ConversionError / uncaught exception.",
    )
    @pytest.mark.parametrize("text", ["99999999y", "10000y", "<t:99999999999999999999>"])
    def test_overflow_is_a_bad_argument(self, text):
        with pytest.raises(commands.BadArgument):
            ShortTime(text, now=NOW)

    @pytest.mark.xfail(
        strict=True,
        reason="Same overflow, but through the slash-command path: ValueError escapes TimeTransformer instead of BadTimeTransform.",
    )
    def test_overflow_in_slash_command_is_a_bad_time_transform(self):
        with pytest.raises(BadTimeTransform):
            run(TimeTransformer().transform(make_interaction(), "99999999y"))

    @pytest.mark.xfail(
        strict=True,
        reason="ShortTime sets _past = False unconditionally, so FutureTime accepts a Discord timestamp that is already in the past.",
    )
    def test_futuretime_rejects_past_discord_timestamp(self):
        with pytest.raises(commands.BadArgument, match=r"in the past"):
            FutureTime("<t:1700000000>", now=NOW)
