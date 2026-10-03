"""Tests for the human-date parsing module.

Assumes the module is importable as ``human_date``; change the import below if
it lives elsewhere (e.g. ``from utils.human_date import ...``).

Tests marked ``xfail(strict=True)`` document *real bugs* found while writing
this suite. They flip to a hard failure the moment the bug is fixed, which is
your cue to delete the marker.
"""

from __future__ import annotations

import datetime

import pytest
from discord import app_commands
from discord.ext import commands

from core.utils.date import (
    _MONTH_ALT,
    MONTHS,
    BadDateTransform,
    DateTransformer,
    HumanDate,
    _expand_year,
    _match_date,
    _parse_time,
    _resolve_month_day,
    _shift_year,
)
from tests.helpers import NOW, UTC, make_ctx, make_interaction, reminder_with, run

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
D = datetime.date
T = datetime.time


def parse(text: str, **kw) -> HumanDate:
    kw.setdefault("now", NOW)
    return HumanDate(text, **kw)


class TestMonths:
    def test_all_twelve_months_covered(self):
        assert sorted(set(MONTHS.values())) == list(range(1, 13))

    def test_keys_are_lowercase(self):
        assert all(k == k.lower() for k in MONTHS)

    @pytest.mark.parametrize(
        ("name", "num"),
        [("jan", 1), ("january", 1), ("febuary", 2), ("february", 2), ("sept", 9), ("sep", 9), ("september", 9), ("dec", 12), ("may", 5)],
    )
    def test_specific_entries(self, name, num):
        assert MONTHS[name] == num

    def test_alternation_is_longest_first(self):
        # If A is a prefix of B, B must come first, or "march" would lose to "mar".
        alts = _MONTH_ALT.split("|")
        for a in alts:
            for b in alts:
                if a != b and b.startswith(a):
                    assert alts.index(b) < alts.index(a), (a, b)


class TestExpandYear:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2004", 2004),
            ("1999", 1999),
            ("0999", 999),
            ("04", 2004),
            ("00", 2000),
            ("68", 2068),
            ("69", 1969),
            ("99", 1999),  # pivot boundary
            ("'04", 2004),
            ("'99", 1999),
            ("\u201904", 2004),  # curly apostrophe
        ],
    )
    def test_expand(self, raw, expected):
        assert _expand_year(raw) == expected

    def test_custom_pivot(self):
        assert _expand_year("50", pivot=50) == 1950
        assert _expand_year("49", pivot=50) == 2049


class TestShiftYear:
    def test_normal(self):
        assert _shift_year(D(2024, 3, 15), 2025) == D(2025, 3, 15)

    def test_leap_day_to_leap_year(self):
        assert _shift_year(D(2024, 2, 29), 2028) == D(2028, 2, 29)

    def test_leap_day_to_non_leap_year_falls_back_to_28th(self):
        assert _shift_year(D(2024, 2, 29), 2025) == D(2025, 2, 28)
        assert _shift_year(D(2024, 2, 29), 2023) == D(2023, 2, 28)


class TestMatchDate:
    @pytest.mark.parametrize("text", ["", "hello", "March", "23", "remind me 23 March 2004"])
    def test_no_match(self, text):
        assert _match_date(text) is None

    def test_only_matches_at_start(self):
        assert _match_date("buy milk 23 March") is None

    def test_longest_match_wins_month_year_over_month_day(self):
        # MDY would grab "March 20"; MY grabs "March 2004". MY is longer.
        m = _match_date("March 2004")
        assert m is not None
        assert m.group(0) == "March 2004"
        assert m.group("year") == "2004"

    def test_tie_goes_to_earlier_pattern_month_day(self):
        # "Mar 23" matches MDY and MY at equal length; MDY must win.
        m = _match_date("Mar 23")
        assert m is not None
        assert m.groupdict().get("day") == "23"

    def test_iso_beats_numeric(self):
        m = _match_date("2004-03-23")
        assert m is not None
        assert m.group(0) == "2004-03-23"
        assert "first" not in m.groupdict() or m.group("first") is None


class TestResolveMonthDay:
    @pytest.mark.parametrize(
        ("data", "dayfirst", "expected"),
        [
            # Genuinely ambiguous numeric
            ({"first": "3", "second": "4"}, True, (4, 3)),
            ({"first": "3", "second": "4"}, False, (3, 4)),
            ({"first": "12", "second": "12"}, True, (12, 12)),
            # First > 12 can only be a day, whatever dayfirst says
            ({"first": "23", "second": "3"}, True, (3, 23)),
            ({"first": "23", "second": "3"}, False, (3, 23)),
            # Second > 12 can only be a day
            ({"first": "3", "second": "23"}, True, (3, 23)),
            ({"first": "3", "second": "23"}, False, (3, 23)),
            # Named months ignore dayfirst
            ({"month": "march", "day": "23"}, True, (3, 23)),
            ({"month": "March", "day": "23"}, False, (3, 23)),
            # ISO: digit month
            ({"month": "03", "day": "23"}, True, (3, 23)),
            # Month-year: no day -> the 1st
            ({"month": "march", "day": None}, True, (3, 1)),
            ({"month": "march"}, True, (3, 1)),
        ],
    )
    def test_resolve(self, data, dayfirst, expected):
        assert _resolve_month_day(data, dayfirst=dayfirst) == expected

    def test_both_over_twelve_yields_invalid_month(self):
        # 13/13 -> (13, 13): month 13 is later rejected by datetime.date.
        assert _resolve_month_day({"first": "13", "second": "13"}, dayfirst=True) == (13, 13)


class TestParseTime:
    @pytest.mark.parametrize(
        ("text", "expected_time", "expected_end"),
        [
            ("at 5pm", T(17, 0), 6),
            ("5pm", T(17, 0), 3),
            ("5 pm", T(17, 0), 4),
            ("5 PM", T(17, 0), 4),
            ("5 p.m.", T(17, 0), 6),
            ("9am", T(9, 0), 3),
            ("9 a.m.", T(9, 0), 6),
            ("17:30", T(17, 30), 5),
            ("17:30:15", T(17, 30, 15), 8),
            ("0:00", T(0, 0), 4),
            ("23:59:59", T(23, 59, 59), 8),
            ("@9:15am", T(9, 15), 7),
            ("@ 9", T(9, 0), 3),
            ("at 17", T(17, 0), 5),  # explicit "at" allows a bare 24h hour
        ],
    )
    def test_valid(self, text, expected_time, expected_end):
        assert _parse_time(text) == (expected_time, expected_end)

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("12am", T(0, 0)),  # midnight
            ("12pm", T(12, 0)),  # noon
            ("12:30 am", T(0, 30)),
            ("12:59pm", T(12, 59)),
            ("1am", T(1, 0)),
            ("11pm", T(23, 0)),
            ("11:59 PM", T(23, 59)),
        ],
    )
    def test_12_hour_clock_edges(self, text, expected):
        result = _parse_time(text)
        assert result is not None
        assert result[0] == expected

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "hello",
            "5",  # bare number is deliberately NOT a time
            "5 apples",
            "at 13pm",
            "13pm",
            "at 0am",
            "0pm",  # 12h clock only allows 1-12
            "at 24",
            "24:00",
            "at 25:00",
            "10:60",
            "10:61",
            "10:30:60",
            "10:30:75",
        ],
    )
    def test_invalid_returns_none(self, text):
        assert _parse_time(text) is None


class TestFormats:
    @pytest.mark.parametrize(
        "text",
        [
            "23 March 2004",
            "23rd of March, 2004",
            "23rd March 2004",
            "23 Mar 04",
            "23 mar '04",
            "23 Mar \u201904",
            "March 23 2004",
            "March 23rd, 2004",
            "Mar 23, 04",
            "2004-03-23",
            "2004-3-23",
            "23/03/2004",
            "23-03-2004",
            "23.03.2004",
            "23/03/04",
            "3-23-04",  # unambiguous: 23 can't be a month
            "3/23/2004",
            "23 MARCH 2004",  # case-insensitive
            "MARCH 23 2004",
        ],
    )
    def test_same_date_many_spellings(self, text):
        hd = parse(text)
        assert hd.date == D(2004, 3, 23), text
        assert hd.has_year is True
        assert hd.has_time is False
        assert hd.remaining == ""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("May 13 '12", D(2012, 5, 13)),
            ("May 13 \u201912", D(2012, 5, 13)),
            ("5th May 1999", D(1999, 5, 5)),
            ("1st Jan 2000", D(2000, 1, 1)),
            ("2nd Feb 2000", D(2000, 2, 2)),
            ("sept 5 2004", D(2004, 9, 5)),
            ("Sept. 5, 2004", D(2004, 9, 5)),  # trailing period
            ("5 Sep. 2004", D(2004, 9, 5)),
            ("febuary 3 2004", D(2004, 2, 3)),  # the famous typo
            ("31 dec 1999", D(1999, 12, 31)),
        ],
    )
    def test_named_month_variants(self, text, expected):
        assert parse(text).date == expected

    def test_surrounding_whitespace_is_ignored(self):
        assert parse("   23 March 2004   ").date == D(2004, 3, 23)

    def test_extra_spaces_and_commas_between_parts(self):
        assert parse("23   March ,  2004").date == D(2004, 3, 23)


class TestMonthYear:
    def test_full_year(self):
        hd = parse("March 2004")
        assert hd.date == D(2004, 3, 1)
        assert hd.has_year is True

    def test_apostrophe_year(self):
        assert parse("May '12").date == D(2012, 5, 1)

    def test_month_day_tie_is_not_misread_as_month_year(self):
        # If MY won the tie this would be 2023-03-01.
        hd = parse("Mar 23")
        assert hd.date == D(2026, 3, 23)
        assert hd.has_year is False


class TestTwoDigitYears:
    @pytest.mark.parametrize(
        ("text", "year"),
        [("1 Jan 00", 2000), ("1 Jan 68", 2068), ("1 Jan 69", 1969), ("1 Jan 99", 1999)],
    )
    def test_pivot(self, text, year):
        assert parse(text).date.year == year


class TestDayFirst:
    def test_default_is_day_first(self):
        assert parse("03/04/2005").date == D(2005, 4, 3)

    def test_dayfirst_false_is_us_order(self):
        assert parse("03/04/2005", dayfirst=False).date == D(2005, 3, 4)

    @pytest.mark.parametrize("dayfirst", [True, False])
    def test_unambiguous_ignores_flag(self, dayfirst):
        assert parse("25/12/2005", dayfirst=dayfirst).date == D(2005, 12, 25)
        assert parse("12/25/2005", dayfirst=dayfirst).date == D(2005, 12, 25)

    @pytest.mark.parametrize("dayfirst", [True, False])
    def test_named_month_ignores_flag(self, dayfirst):
        assert parse("03 April 2005", dayfirst=dayfirst).date == D(2005, 4, 3)

    def test_numeric_without_year(self):
        hd = parse("23.03")
        assert hd.date == D(2026, 3, 23)
        assert hd.has_year is False


class TestPrefer:
    # NOW is 2026-10-03.
    def test_current_keeps_current_year_even_if_past(self):
        hd = parse("5 March")
        assert hd.date == D(2026, 3, 5)
        assert hd.has_year is False

    def test_current_keeps_current_year_even_if_future(self):
        assert parse("5 December").date == D(2026, 12, 5)

    def test_future_rolls_forward_when_passed(self):
        assert parse("5 March", prefer="future").date == D(2027, 3, 5)

    def test_future_keeps_year_when_still_ahead(self):
        assert parse("5 December", prefer="future").date == D(2026, 12, 5)

    def test_past_rolls_back_when_ahead(self):
        assert parse("5 December", prefer="past").date == D(2025, 12, 5)

    def test_past_keeps_year_when_already_passed(self):
        assert parse("5 March", prefer="past").date == D(2026, 3, 5)

    @pytest.mark.parametrize("prefer", ["current", "future", "past"])
    def test_today_is_never_rolled(self, prefer):
        # Boundary: strict < and > mean "today" stays today.
        assert parse("3 October", prefer=prefer).date == D(2026, 10, 3)

    @pytest.mark.parametrize("prefer", ["current", "future", "past"])
    def test_explicit_year_is_never_rolled(self, prefer):
        hd = parse("5 March 2020", prefer=prefer)
        assert hd.date == D(2020, 3, 5)
        assert hd.has_year is True

    def test_leap_day_rolls_with_fallback_to_28th(self):
        leap_now = datetime.datetime(2024, 3, 1, tzinfo=UTC)
        assert parse("29 Feb", now=leap_now, prefer="future").date == D(2025, 2, 28)
        early = datetime.datetime(2024, 2, 1, tzinfo=UTC)
        assert parse("29 Feb", now=early, prefer="past").date == D(2023, 2, 28)

    def test_leap_day_stays_when_current_year_is_leap_and_not_rolled(self):
        leap_now = datetime.datetime(2024, 2, 10, tzinfo=UTC)
        assert parse("29 Feb", now=leap_now, prefer="future").date == D(2024, 2, 29)

    def test_no_time_is_midnight(self):
        hd = parse("23 March 2004")
        assert hd.has_time is False
        assert hd.datetime == datetime.datetime(2004, 3, 23, 0, 0, tzinfo=UTC)

    def test_with_at_pm(self):
        hd = parse("23 March 2004 at 5pm")
        assert hd.has_time is True
        assert hd.datetime == datetime.datetime(2004, 3, 23, 17, 0, tzinfo=UTC)
        assert hd.remaining == ""

    def test_remaining_text_only(self):
        hd = parse("23 March 2004 buy milk")
        assert hd.has_time is False
        assert hd.remaining == "buy milk"

    def test_time_then_remaining(self):
        hd = parse("23 March 2004 at 5pm buy milk")
        assert hd.has_time is True
        assert hd.remaining == "buy milk"
        assert hd.datetime.hour == 17

    def test_iso_date_with_bare_24h_time(self):
        hd = parse("2004-03-23 17:30 standup")
        assert hd.datetime == datetime.datetime(2004, 3, 23, 17, 30, tzinfo=UTC)
        assert hd.remaining == "standup"

    def test_numeric_date_with_bare_24h_time(self):
        hd = parse("23/03/2004 17:30:15")
        assert hd.datetime == datetime.datetime(2004, 3, 23, 17, 30, 15, tzinfo=UTC)

    def test_yearless_date_with_at_time(self):
        hd = parse("23 March at 5pm")
        assert hd.date == D(2026, 3, 23)
        assert hd.has_year is False
        assert hd.datetime.hour == 17

    def test_bare_number_after_date_is_not_a_time(self):
        hd = parse("23 March 2004 5 apples")
        assert hd.has_time is False
        assert hd.remaining == "5 apples"

    def test_invalid_time_is_left_in_remaining(self):
        hd = parse("23 March 2004 at 13pm")
        assert hd.has_time is False
        assert hd.datetime.hour == 0
        assert hd.remaining == "at 13pm"

    def test_midnight_and_noon(self):
        assert parse("23 March 2004 at 12am").datetime.hour == 0
        assert parse("23 March 2004 at 12pm").datetime.hour == 12


class TestTimezones:
    def test_default_tz_is_utc(self):
        assert parse("23 March 2004").datetime.tzinfo is UTC

    def test_custom_tzinfo_applied_to_result(self):
        hd = parse("23 March 2004 at 5pm", tzinfo=IST)
        assert hd.datetime.tzinfo is IST
        assert hd.datetime.utcoffset() == datetime.timedelta(hours=5, minutes=30)
        assert hd.datetime.hour == 17  # wall-clock in the user's tz, not shifted

    def test_naive_now_is_treated_as_utc(self):
        naive = datetime.datetime(2026, 10, 3, 12, 0)  # noqa: DTZ001
        hd = HumanDate("5 March", now=naive, prefer="future")
        assert hd.date == D(2027, 3, 5)

    def test_today_is_computed_in_the_users_timezone(self):
        # 23:30 UTC on Oct 3 is already Oct 4 in IST.
        late = datetime.datetime(2026, 10, 3, 23, 30, tzinfo=UTC)
        in_utc = parse("3 October", now=late, tzinfo=UTC, prefer="future")
        in_ist = parse("3 October", now=late, tzinfo=IST, prefer="future")
        assert in_utc.date == D(2026, 10, 3)  # still today
        assert in_ist.date == D(2027, 10, 3)  # already yesterday -> rolls

    def test_now_defaults_to_real_clock(self):
        # An explicit year keeps this deterministic without freezing time.
        assert HumanDate("2004-03-23").date == D(2004, 3, 23)


class TestErrors:
    @pytest.mark.parametrize(
        "text",
        ["", "   ", "hello", "March", "23", "remind me 23 March 2004", "next friday"],
    )
    def test_no_date_found(self, text):
        with pytest.raises(commands.BadArgument, match="Couldn't find a date"):
            parse(text)

    @pytest.mark.parametrize(
        "text",
        [
            "31 February 2004",
            "30 Feb 2004",
            "31 April 2004",
            "32 March 2004",
            "0 March 2004",
            "29 Feb 2003",  # not a leap year
            "29 Feb 1900",  # century, not leap
            "29 Feb 2100",
            "2004-13-01",
            "2004-02-30",
            "2004-00-10",
            "13/13/2004",  # neither field can be a month
            "31/04/2004",
            "30 Feb",  # no year given, still impossible
        ],
    )
    def test_impossible_dates(self, text):
        with pytest.raises(commands.BadArgument, match="isn't a real date"):
            parse(text)

    def test_error_message_quotes_the_offending_text(self):
        with pytest.raises(commands.BadArgument) as exc:
            parse("31 February 2004 at 5pm")
        assert "`31 February 2004`" in str(exc.value)

    def test_error_has_no_chained_context(self):
        with pytest.raises(commands.BadArgument) as exc:
            parse("31 February 2004")
        assert exc.value.__suppress_context__ is True

    @pytest.mark.parametrize("text", ["29 Feb 2004", "29 Feb 2000", "29 Feb 00", "29 Feb 04"])
    def test_real_leap_days_are_accepted(self, text):
        assert parse(text).date.month == 2
        assert parse(text).date.day == 29


class TestObject:
    def test_repr(self):
        hd = parse("23 March 2004 buy milk")
        assert repr(hd) == ("<HumanDate date=datetime.date(2004, 3, 23) has_year=True remaining='buy milk'>")

    def test_uses_slots(self):
        hd = parse("23 March 2004")
        assert not hasattr(hd, "__dict__")
        with pytest.raises(AttributeError):
            hd.something_else = 1  # pyright: ignore[reportAttributeAccessIssue]

    def test_all_documented_attributes_exist(self):
        hd = parse("23 March 2004")
        for attr in ("date", "datetime", "has_year", "has_time", "remaining"):
            assert hasattr(hd, attr)


class TestConvert:
    def test_no_reminder_cog_uses_utc(self):
        hd = run(HumanDate.convert(make_ctx(None), "23 March 2004 at 5pm"))
        assert isinstance(hd, HumanDate)
        assert hd.datetime.tzinfo is UTC
        assert hd.datetime.hour == 17

    def test_uses_users_timezone_from_reminder_cog(self):
        reminder = reminder_with(IST)
        hd = run(HumanDate.convert(make_ctx(reminder, user_id=7), "23 March 2004 at 5pm"))
        reminder.get_tzinfo.assert_awaited_once_with(7)
        assert hd.datetime.tzinfo is IST

    def test_uses_message_timestamp_as_now(self):
        ctx = make_ctx(None, created_at=datetime.datetime(2030, 1, 1, tzinfo=UTC))
        hd = run(HumanDate.convert(ctx, "5 March"))
        assert hd.date == D(2030, 3, 5)

    def test_bad_input_raises_bad_argument(self):
        with pytest.raises(commands.BadArgument):
            run(HumanDate.convert(make_ctx(None), "nope"))


class TestDateTransformer:
    def test_is_a_transformer(self):
        assert issubclass(DateTransformer, app_commands.Transformer)

    def test_bad_date_transform_is_an_app_command_error(self):
        assert issubclass(BadDateTransform, app_commands.AppCommandError)

    def test_returns_aware_datetime(self):
        result = run(DateTransformer().transform(make_interaction(None), "2004-03-23 17:30"))
        assert result == datetime.datetime(2004, 3, 23, 17, 30, tzinfo=UTC)

    def test_applies_user_timezone(self):
        reminder = reminder_with(IST)
        result = run(DateTransformer().transform(make_interaction(reminder, user_id=9), "23 March 2004 at 5pm"))
        reminder.get_tzinfo.assert_awaited_once_with(9)
        assert result.tzinfo is IST
        assert result.hour == 17

    def test_converts_bad_argument_to_bad_date_transform(self):
        with pytest.raises(BadDateTransform) as exc:
            run(DateTransformer().transform(make_interaction(None), "gibberish"))
        assert "Couldn't find a date" in str(exc.value)
        assert exc.value.__suppress_context__ is True

    def test_impossible_date_message_is_forwarded(self):
        with pytest.raises(BadDateTransform, match="isn't a real date"):
            run(DateTransformer().transform(make_interaction(None), "31 February 2004"))

    def test_remaining_text_is_discarded(self):
        result = run(DateTransformer().transform(make_interaction(None), "23 March 2004 buy milk"))
        assert result.date() == D(2004, 3, 23)


class TestKnownBugs:
    @pytest.mark.xfail(
        strict=True,
        reason="Yearless 'DD Month' followed by a bare time: the two-digit year "
        "pattern swallows the hour ('17' -> 2017) and leaves ':00' as remaining text.",
    )
    @pytest.mark.parametrize(
        ("text", "hour"),
        [("23 March 17:00", 17), ("March 23 10:30", 10), ("23 March 10am", 10)],
    )
    def test_bare_time_after_yearless_date_is_not_a_year(self, text, hour):
        hd = parse(text)
        assert hd.date == D(2026, 3, 23)
        assert hd.has_year is False
        assert hd.datetime.hour == hour

    @pytest.mark.xfail(
        strict=True,
        reason="Yearless '29 Feb' builds date(current_year, 2, 29) before rolling, "
        "so it raises in a non-leap year even though prefer='future' could resolve it.",
    )
    def test_leap_day_without_year_in_non_leap_year_with_future(self):
        # Today is 2027-01-01; the next 29 Feb is 2028-02-29.
        now = datetime.datetime(2027, 1, 1, tzinfo=UTC)
        assert parse("29 Feb", now=now, prefer="future").date == D(2028, 2, 29)

    @pytest.mark.xfail(
        strict=True,
        reason="am/pm has no word boundary, so 'amazon' is read as 'am' + 'azon'.",
    )
    def test_ampm_requires_word_boundary(self):
        hd = parse("23 March 2004 at 5 amazon delivery")
        assert hd.remaining in {"delivery", "amazon delivery"}
        assert hd.remaining != "azon delivery"

    @pytest.mark.xfail(
        strict=True,
        reason="Month names have no trailing word boundary, so 'Mayday' parses as 'May' with 'day' left over, and 'decade' as 'Dec' + 'ade'.",
    )
    @pytest.mark.parametrize("text", ["1 Mayday celebration", "2 decade plan"])
    def test_month_requires_word_boundary(self, text):
        with pytest.raises(commands.BadArgument):
            parse(text)
