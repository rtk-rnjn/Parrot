from __future__ import annotations

import asyncio
import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

from bson import ObjectId
from pymongo.results import DeleteResult, InsertOneResult

from core.utils.timer_dispatcher import AsyncTimerDispatcher, TimerData
from tests.helpers import run

UTC = datetime.UTC


def timer_data(*, timer_id: ObjectId | None = None, event_name: str = "reminder", **metadata: object) -> TimerData:
    timer: TimerData = {
        "expires_at": datetime.datetime(2026, 10, 3, 13, 0, tzinfo=UTC),
        "created_at": datetime.datetime(2026, 10, 3, 12, 0, tzinfo=UTC),
        "event_name": event_name,  # type: ignore[typeddict-item]
        "metadata": metadata,
    }
    if timer_id is not None:
        timer["_id"] = timer_id
    return timer


class AsyncCursor:
    def __init__(self, documents: list[TimerData]) -> None:
        self.documents = documents

    async def to_list(self, *, length: int | None = None) -> list[TimerData]:
        return self.documents if length is None else self.documents[:length]


class MemoryTimerCollection:
    def __init__(self, documents: list[TimerData] | None = None) -> None:
        self.documents = documents or []

    @staticmethod
    def _matches(document: TimerData, filters: dict[str, object]) -> bool:
        for key, expected in filters.items():
            value: Any = document
            for part in key.split("."):
                if not isinstance(value, dict):
                    return False
                value = value.get(part)
            if value != expected:
                return False
        return True

    async def find_one(self, filters: dict[str, object], *, sort: list[tuple[str, int]] | None = None) -> TimerData | None:
        matches = [document for document in self.documents if self._matches(document, filters)]
        if sort:
            key, direction = sort[0]
            matches.sort(key=lambda document: document[key], reverse=direction < 0)
        return matches[0] if matches else None

    async def insert_one(self, document: TimerData) -> InsertOneResult:
        timer_id = ObjectId()
        stored = {**document, "_id": timer_id}
        self.documents.append(cast(TimerData, stored))
        return InsertOneResult(timer_id, True)

    async def delete_one(self, filters: dict[str, object]) -> DeleteResult:
        for index, document in enumerate(self.documents):
            if self._matches(document, filters):
                del self.documents[index]
                return DeleteResult({"n": 1, "ok": 1}, True)
        return DeleteResult({"n": 0, "ok": 1}, True)

    async def delete_many(self, filters: dict[str, object]) -> DeleteResult:
        remaining = [document for document in self.documents if not self._matches(document, filters)]
        deleted = len(self.documents) - len(remaining)
        self.documents = remaining
        return DeleteResult({"n": deleted, "ok": 1}, True)

    def find(self, filters: dict[str, object], *, sort: list[tuple[str, int]]) -> AsyncCursor:
        matches = [document for document in self.documents if self._matches(document, filters)]
        key, direction = sort[0]
        matches.sort(key=lambda document: document[key], reverse=direction < 0)
        return AsyncCursor(matches)


async def make_dispatcher(documents: list[TimerData] | None = None) -> tuple[AsyncTimerDispatcher, MemoryTimerCollection, Mock]:
    collection = MemoryTimerCollection(documents)
    bot = SimpleNamespace(
        database=SimpleNamespace(mongo_db={"timers": collection}),
        loop=asyncio.get_running_loop(),
        dispatch=Mock(),
        is_closed=Mock(return_value=False),
    )
    return AsyncTimerDispatcher(cast(Any, bot)), collection, bot.dispatch


def test_create_timer_persists_document_and_wakes_dispatcher() -> None:
    async def scenario() -> None:
        dispatcher, collection, _ = await make_dispatcher()
        expires_at = datetime.datetime(2026, 10, 3, 14, 0, tzinfo=UTC)

        result = await dispatcher.create_timer(event_name="todo_due", expires_at=expires_at, metadata={"todo_id": 7})

        assert result.inserted_id == collection.documents[0].get("_id")
        assert collection.documents[0]["event_name"] == "todo_due"
        assert collection.documents[0]["metadata"] == {"todo_id": 7}
        assert dispatcher._have_data.is_set()

    run(scenario())


def test_get_and_search_return_matching_timers_in_expiry_order() -> None:
    async def scenario() -> None:
        later = timer_data(timer_id=ObjectId(), user_id=1)
        earlier = timer_data(timer_id=ObjectId(), event_name="mute", user_id=1)
        earlier["expires_at"] -= datetime.timedelta(minutes=30)
        dispatcher, _, _ = await make_dispatcher([later, earlier])

        get_timer = cast(Any, dispatcher.get)
        found = await get_timer(event_name="mute")
        searched = await dispatcher.search(event_name="reminder", metadata_filter={"user_id": 1})

        assert found == earlier
        assert searched == [later]

    run(scenario())


def test_delete_builds_nested_metadata_filter_and_restarts_after_deletion() -> None:
    async def scenario() -> None:
        dispatcher, collection, _ = await make_dispatcher([timer_data(timer_id=ObjectId(), user_id=42)])
        dispatcher.restart = AsyncMock()

        result = await dispatcher.delete(event_name="reminder", metadata_filter={"user_id": 42})

        assert result.deleted_count == 1
        assert collection.documents == []
        dispatcher.restart.assert_awaited_once_with()

    run(scenario())


def test_delete_multiple_removes_all_matching_timers() -> None:
    async def scenario() -> None:
        dispatcher, collection, _ = await make_dispatcher([timer_data(timer_id=ObjectId(), user_id=42), timer_data(timer_id=ObjectId(), user_id=7)])
        dispatcher.restart = AsyncMock()

        result = await dispatcher.delete(event_name="reminder", metadata_filter={"user_id": 42}, multiple=True)

        assert result.deleted_count == 1
        assert len(collection.documents) == 1
        assert collection.documents[0]["metadata"] == {"user_id": 7}
        dispatcher.restart.assert_awaited_once_with()

    run(scenario())


def test_delete_without_match_does_not_restart() -> None:
    async def scenario() -> None:
        dispatcher, _, _ = await make_dispatcher()
        dispatcher.restart = AsyncMock()

        result = await dispatcher.delete(event_name="giveaway", metadata_filter={"guild_id": 99})

        assert result.deleted_count == 0
        dispatcher.restart.assert_not_awaited()

    run(scenario())


def test_wait_for_active_timer_waits_until_data_is_signaled() -> None:
    async def scenario() -> None:
        dispatcher, collection, _ = await make_dispatcher()
        wait_for_active_timer = cast(Any, dispatcher)._AsyncTimerDispatcher__wait_for_active_timer
        waiting = asyncio.create_task(wait_for_active_timer())
        await asyncio.sleep(0)
        assert not waiting.done()
        assert not dispatcher._have_data.is_set()

        collection.documents.append(timer_data(timer_id=ObjectId()))
        dispatcher._have_data.set()
        result = await waiting

        assert result == collection.documents[0]

    run(scenario())


def test_call_timer_dispatches_only_after_successful_delete() -> None:
    async def scenario() -> None:
        timer_id = ObjectId()
        dispatcher, _, dispatch = await make_dispatcher()
        dispatcher.timers_collection.delete_one = AsyncMock(return_value=DeleteResult({"n": 1, "ok": 1}, True))

        call_timer = cast(Any, dispatcher)._AsyncTimerDispatcher__call_timer
        await call_timer(**timer_data(timer_id=timer_id, event_name="mute", user_id=4))

        dispatcher.timers_collection.delete_one.assert_awaited_once_with({"_id": timer_id})
        dispatch.assert_called_once_with("mute_timer_complete", metadata={"user_id": 4})

    run(scenario())


def test_call_timer_does_not_dispatch_when_another_worker_consumed_it() -> None:
    async def scenario() -> None:
        dispatcher, _, dispatch = await make_dispatcher()
        dispatcher.timers_collection.delete_one = AsyncMock(return_value=DeleteResult({"n": 0, "ok": 1}, True))

        call_timer = cast(Any, dispatcher)._AsyncTimerDispatcher__call_timer
        await call_timer(**timer_data(timer_id=ObjectId()))

        dispatch.assert_not_called()

    run(scenario())
