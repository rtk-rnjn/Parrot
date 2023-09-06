from __future__ import annotations

import logging

import aiohttp
import aiosqlite
import yarl

log = logging.getLogger("updater")

# SCAM LINK URL
API = yarl.URL("https://api.github.com/")
RAW_API = yarl.URL("https://raw.githubusercontent.com/")
REPO = "Discord-AntiScam/scam-links"

_COMMIT_URL = API / "repos" / REPO / "commits"
_ORIGINAL_RAW_REPO = RAW_API / REPO

COMMIT_URL = _COMMIT_URL
ORIGINAL_REPO = _ORIGINAL_RAW_REPO


async def init():
    db = await aiosqlite.connect("cached.sqlite", iter_chunk_size=2**8, cached_statements=2**10)

    query = """
        BEGIN;
        CREATE TABLE IF NOT EXISTS scam_links (id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT NOT NULL, UNIQUE(link));
        CREATE TABLE IF NOT EXISTS discord_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT NOT NULL, UNIQUE(token));
        CREATE TABLE IF NOT EXISTS nsfw_links (id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT NOT NULL, UNIQUE(link));
        CREATE TABLE IF NOT EXISTS nsfw_links_grouped (id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT NOT NULL UNIQUE, type TEXT);
        COMMIT;
    """

    await db.executescript(query)
    await db.commit()

    return db


async def insert_all_scams(db: aiosqlite.Connection):
    url = ORIGINAL_REPO / "main" / "list.json"

    async with aiohttp.ClientSession() as session:
        log.debug("Downloading Data... %s", url)
        response = await session.get(url)
        log.debug("Downloaded Data... %s. return code: %s", url, response.status)

        if response.status != 200:
            log.warning("Failed to download data... exiting...")
            return

        log.debug("parsing data from %s", url)
        data = await response.json(content_type="text/plain")
        log.debug("parsed data from %s. Total Links: %s", url, len(data))

    query = """INSERT INTO scam_links (link) VALUES (?) ON CONFLICT DO NOTHING"""

    for link in data:
        await db.execute(query, (link,))
        log.info("inserted link: %s", link)

    await db.commit()


async def insert_new(db: aiosqlite.Connection):
    async with aiohttp.ClientSession() as session:
        log.debug("Downloading Data... %s", COMMIT_URL)
        response = await session.get(COMMIT_URL)
        log.debug("Downloaded Data... %s. return code: %s", COMMIT_URL, response.status)

        if response.status != 200:
            log.info("Failed to download data... trying to download all data...")
            await insert_all_scams(db)
            return

        log.debug("parsing data from %s", COMMIT_URL)
        data = await response.json()
        log.debug("parsed data from %s. Total Links: %s", COMMIT_URL, len(data))

    insert_query = """INSERT INTO scam_links (link) VALUES (?) ON CONFLICT DO NOTHING"""
    delete_query = """DELETE FROM scam_links WHERE link = ?"""

    for commit in data:
        message = commit["commit"]["message"]
        if message.startswith("+ "):
            link = message[2:]
            cur = await db.execute(insert_query, (link,))
            if cur.rowcount:
                log.info("inserted link: %s", link)
        elif message.startswith("- "):
            link = message[2:]
            cur = await db.execute(delete_query, (link,))
            if cur.rowcount:
                log.info("deleted link: %s", link)

    await db.commit()
