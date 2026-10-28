from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import TYPE_CHECKING, Any

from .app import app
from .config import IPC_REQUEST_CHANNEL

if TYPE_CHECKING:
    from redis.asyncio import Redis


async def ipc_request(op: str, payload: dict[str, Any], timeout: float = 3.0):
    """
    Publish an IPC command to `parrot:ipc:request` and await the bot's reply
    on `parrot:ipc:response:<corr_id>` via Redis Pub/Sub.
    """
    redis_client: Redis = app.state.redis_client

    corr_id = uuid.uuid4().hex
    response_channel = f"parrot:ipc:response:{corr_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(response_channel)

    envelope = {
        "corr_id": corr_id,
        "op": op,
        "payload": payload,
        "sent_at": time.time(),
    }

    try:
        await redis_client.publish(IPC_REQUEST_CHANNEL, json.dumps(envelope))
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                message = f"Redis Pub/Sub IPC timed out waiting for {response_channel}"
                raise TimeoutError(message)
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=min(0.25, remaining))
            if msg and msg.get("type") == "message":
                return json.loads(msg["data"])
            await asyncio.sleep(0.02)
    finally:
        await pubsub.unsubscribe(response_channel)
        await pubsub.close()
