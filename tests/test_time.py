from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from utilities.time import ShortTime


class TestShortTime(TestCase):
    def setUp(self) -> None:
        self.arguments: list[tuple[str, timedelta]] = [
            ("10h", timedelta(hours=10)),
            ("3h2m", timedelta(hours=3, minutes=2)),
            ("7h30m40s", timedelta(hours=7, minutes=30, seconds=40)),
            ("1d", timedelta(days=1)),
            ("2d3h", timedelta(days=2, hours=3)),
            ("1w", timedelta(weeks=1)),
            ("2w3d", timedelta(weeks=2, days=3)),
            (
                "3w4d5h40m30s",
                timedelta(weeks=3, days=4, hours=5, minutes=40, seconds=30),
            ),
        ]

    def test_shorttime(self):
        # sourcery skip: no-loop-in-tests
        for argument, expected in self.arguments:
            with self.subTest(argument=argument, expected=expected):
                self.assertEqual(
                    ShortTime(argument).dt.timestamp(),
                    (datetime.now(timezone.utc) + expected).timestamp(),
                )


if __name__ == "__main__":
    from unittest import main

    main()
