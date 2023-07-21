from __future__ import annotations

import asyncio

import aiohttp
import aiosqlite

# SCAM LINK URL
_COMMIT_URL = "https://api.github.com/repos/{REPO}/commits"
_ORIGINAL_REPO = "https://raw.githubusercontent.com/{REPO}"

REPO = "Discord-AntiScam/scam-links"

COMMIT_URL = _COMMIT_URL.format(REPO=REPO)
ORIGINAL_REPO = _ORIGINAL_REPO.format(REPO=REPO)


async def init():
    db = await aiosqlite.connect("cached.sqlite")

    query = """CREATE TABLE IF NOT EXISTS scam_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT NOT NULL,
        UNIQUE(link)
    )"""

    await db.execute(query)
    await db.commit()

    return db


async def insert_all_scams(db: aiosqlite.Connection):
    url = f"{ORIGINAL_REPO}//main/list.json"

    async with aiohttp.ClientSession() as session:
        print("Downloading Data...", url)
        response = await session.get(url)
        print("Downloaded Data...", url, response.status)

        if response.status != 200:
            print("Failed to download data... Trying to download from original repo...")
            return

        print("Parsing Data...", url)
        data = await response.json(content_type="text/plain")
        print("Parsed Data... Total Links:", len(data))

    query = "INSERT INTO scam_links (link) VALUES (?) ON CONFLICT DO NOTHING"

    for link in data:
        await db.execute(query, (link,))
        print("Inserted Link:", link)

    await db.commit()


async def insert_new(db: aiosqlite.Connection):
    async with aiohttp.ClientSession() as session:
        print("Downloading Data...", COMMIT_URL)
        response = await session.get(COMMIT_URL)
        print("Downloaded Data...", COMMIT_URL, response.status)

        if response.status != 200:
            print("Failed to download data... Trying to download from original repo...")
            await insert_all_scams(db)
            return

        print("Parsing Data...", COMMIT_URL)
        data = await response.json()
        print("Parsed Data... Total Links:", len(data))

    insert_query = "INSERT INTO scam_links (link) VALUES (?) ON CONFLICT DO NOTHING"
    delete_query = "DELETE FROM scam_links WHERE link = ?"

    for commit in data:
        message = commit["commit"]["message"]
        if message.startswith("+ "):
            link = message[2:]
            cur = await db.execute(insert_query, (link,))
            if cur.rowcount:
                print("Inserted Link:", link)
        elif message.startswith("- "):
            link = message[2:]
            cur = await db.execute(delete_query, (link,))
            if cur.rowcount:
                print("Deleted Link:", link)

    await db.commit()


async def main():
    db = await init()
    await insert_new(db)

    while True:
        user_input = input("SQLite > ")
        if user_input == "exit":
            break

        try:
            result = await db.execute(user_input)
            await db.commit()
            rows = await result.fetchall()
            if rows and user_input.lower().startswith("select"):
                for row in rows:
                    print(row)
            else:
                print("Affected Rows:", result.rowcount)

        except Exception as e:
            print(e)

    await db.close()


if __name__ == "__main__":
    _ = asyncio.run(main())
