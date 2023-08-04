from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from utilities.youtube_search import YoutubeSearch


class TestYoutubeSearch(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.query = "How to make a discord bot in python"
        self.max_result = 5
        self.youtube_search = YoutubeSearch(max_results=self.max_result)
        await self.youtube_search.init()

    async def asyncTearDown(self) -> None:
        await self.youtube_search.close()

    async def test_youtube_search(self):
        result = await self.youtube_search.to_dict(self.query)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), self.max_result)

        for data in result:
            self.assertIsInstance(data, dict)


if __name__ == "__main__":
    from unittest import main

    main()
