from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from utilities.wikihow import Parser


class TestWikihow(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.parser = Parser()
        await self.parser.init()

    async def asyncTearDown(self) -> None:
        await self.parser.close()

    async def test_get_wikihow(self) -> None:
        query = "How to make a Pizza"

        result: list[tuple[str, str, int]] = await self.parser.get_wikihow(query)
        self.assertIsInstance(result, list)

        for title, snippet, article_id in result:
            self.assertIsInstance(title, str)
            self.assertIsInstance(snippet, str)
            self.assertIsInstance(article_id, int)

            self.assertGreater(len(title), 0)

    async def test_get_wikihow_article(self):
        article_id = 4323292  # How to make a Pizza [Make Homemade Pizza Rolls]

        result: dict = await self.parser.get_wikihow_article(article_id)

        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    from unittest import main

    main()
