# strawpoll

A simple strawpoll.me API wrapper for Python 3.10+ for my discord bot.

## Usage

```py
from strawpoll import HTTPClient as StrawpollClient
from strawpoll import Poll, TextPollOption


async def main():
    client = StrawpollClient(TOKEN)
    await client.init()

    poll = Poll(
        title="What is your favorite color?",
        poll_options=[
            TextPollOption(value="Red"),
            TextPollOption(value="Blue"),
            TextPollOption(value="Green"),
        ],
    )

    poll = await client.create_poll(poll)
    print(poll)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```
