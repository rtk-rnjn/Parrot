from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Mapping, MutableMapping, Sequence
from typing import Any, Generic, Union

from bson.codec_options import CodecOptions
from bson.raw_bson import RawBSONDocument
from pymongo import MongoClient, WriteConcern
from pymongo.client_session import ClientSession
from pymongo.collection import Collection, ReturnDocument
from pymongo.command_cursor import CommandCursor
from pymongo.cursor import Cursor, RawBatchCursor
from pymongo.database import Database
from pymongo.operations import (
    DeleteMany,
    DeleteOne,
    IndexModel,
    InsertOne,
    ReplaceOne,
    UpdateMany,
    UpdateOne,
    _IndexKeyHint,
    _IndexList,
)
from pymongo.read_concern import ReadConcern
from pymongo.results import BulkWriteResult, DeleteResult, InsertManyResult, InsertOneResult, UpdateResult
from pymongo.typings import _CollationIn, _DocumentType, _Pipeline

_WriteOp = Union[  # noqa: UP007
    InsertOne,
    DeleteOne,
    DeleteMany,
    ReplaceOne,
    UpdateOne,
    UpdateMany,
]


class AsyncMongoClient(MongoClient, Generic[_DocumentType]):
    def __getattr__(self, name: str) -> MongoDatabase[_DocumentType]:
        ...

    def __getitem__(self, name: str) -> MongoDatabase[_DocumentType]:
        ...


class MongoCollection(Collection, Generic[_DocumentType]):
    def __init__(
        self,
        database: Database,
        name: str,
        create: bool = False,
        codec_options: CodecOptions | None = None,
        session: ClientSession | None = None,
        write_concern: WriteConcern | None = None,
        read_concern: ReadConcern | None = None,
        **kwargs,
    ) -> None:
        ...

    def __getattr__(self, name: str) -> Collection[_DocumentType]:
        ...

    def __getitem__(self, name: str) -> Collection[_DocumentType]:
        ...

    @property
    def database(self) -> Database[_DocumentType]:
        ...

    async def bulk_write(
        self,
        requests: Sequence[InsertOne | DeleteOne | DeleteMany | ReplaceOne | UpdateOne | UpdateMany],
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: ClientSession | None = None,
        comment: Any | None = None,
        let: Mapping | None = None,
    ) -> BulkWriteResult:
        ...

    async def insert_one(
        self,
        document: Any | RawBSONDocument,
        bypass_document_validation: bool = False,
        session: ClientSession | None = None,
        comment: Any | None = None,
    ) -> InsertOneResult:
        ...

    async def insert_many(
        self,
        documents: Iterable[Any | RawBSONDocument],
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: ClientSession | None = None,
        comment: Any | None = None,
    ) -> InsertManyResult:
        ...

    async def replace_one(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        replacement: Mapping[str, Any],
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: _CollationIn | None = None,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None,
    ) -> UpdateResult:
        ...

    async def update_one(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        update: Mapping[str, Any] | _Pipeline,
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: _CollationIn | None = None,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None,
    ) -> UpdateResult:
        ...

    async def update_many(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        update: Mapping[str, Any] | _Pipeline,
        upsert: bool = False,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
        bypass_document_validation: bool | None = None,
        collation: _CollationIn | None = None,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None,
    ) -> UpdateResult:
        ...

    async def drop(
        self,
        session: ClientSession | None = None,
        comment: Any | None = None,
        encrypted_fields: Mapping[str, Any] | None = None,
    ) -> None:
        ...

    async def delete_one(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        collation: _CollationIn | None = None,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        comment: Any | None = None,
    ) -> DeleteResult:
        ...

    async def delete_many(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        collation: _CollationIn | None = None,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        comment: Any | None = None,
    ) -> DeleteResult:
        ...

    async def find_one(self, filter: Any | None = None, *args: Any, **kwargs: Any) -> Any:  # noqa: A002
        ...

    def find(self, *args: Any, **kwargs: Any) -> AsyncIterator[Cursor[_DocumentType] | dict]:
        ...

    async def find_raw_batches(self, *args: Any, **kwargs: Any) -> RawBatchCursor:
        ...

    async def estimated_document_count(self, comment: Any | None = None, **kwargs: Any) -> int:
        ...

    async def count_documents(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        session: ClientSession | None = None,
        comment: Any | None = None,
        **kwargs: Any,
    ) -> int:
        ...

    async def create_index(self, keys: _IndexList, session: ClientSession | None = None, **kwargs: Any) -> str:
        ...

    async def create_indexes(
        self,
        indexes: Sequence[IndexModel],
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> Sequence[str]:
        ...

    async def drop_index(self, index_or_name: _IndexKeyHint, session: ClientSession | None = None, **kwargs: Any) -> None:
        ...

    async def drop_indexes(self, session: ClientSession | None = None, **kwargs: Any) -> None:
        ...

    async def list_indexes(
        self,
        session: ClientSession | None = None,
        comment: Any | None = None,
    ) -> CommandCursor[MutableMapping[str, Any]]:
        ...

    async def index_information(
        self,
        session: ClientSession | None = None,
        comment: Any | None = None,
    ) -> MutableMapping[str, Any]:
        ...

    async def options(self, session: ClientSession | None = None, comment: Any | None = None) -> MutableMapping[str, Any]:
        ...

    async def aggregate(
        self,
        pipeline: _Pipeline,
        session: ClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None,
        **kwargs: Any,
    ) -> CommandCursor:
        ...

    async def aggregate_raw_batches(
        self,
        pipeline: _Pipeline,
        session: ClientSession | None = None,
        comment: Any | None = None,
        **kwargs: Any,
    ) -> RawBatchCursor:
        ...

    async def distinct(
        self,
        key: str,
        filter: Mapping[str, Any] | None = None,  # noqa: A002
        session: ClientSession | None = None,
        comment: Any | None = None,
        **kwargs: Any,
    ) -> list:
        ...

    async def find_one_and_delete(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        projection: Mapping[str, Any] | Iterable[str] | None = None,
        sort: _IndexList | None = None,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        ...

    async def find_one_and_replace(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        replacement: Mapping[str, Any],
        projection: Mapping[str, Any] | Iterable[str] | None = None,
        sort: _IndexList | None = None,
        upsert: bool = False,
        return_document: bool = ReturnDocument.BEFORE,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        ...

    async def find_one_and_update(
        self,
        filter: Mapping[str, Any],  # noqa: A002
        update: Mapping[str, Any] | _Pipeline,
        projection: Mapping[str, Any] | Iterable[str] | None = None,
        sort: _IndexList | None = None,
        upsert: bool = False,
        return_document: bool = ReturnDocument.BEFORE,
        array_filters: Sequence[Mapping[str, Any]] | None = None,
        hint: _IndexKeyHint | None = None,
        session: ClientSession | None = None,
        let: Mapping[str, Any] | None = None,
        comment: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        ...


class MongoDatabase(Database, Generic[_DocumentType]):
    def __init__(
        self,
        client: Any,
        name: str,
        codec_options: CodecOptions | None = None,
        read_preference: Any | None = None,
        write_concern: WriteConcern | None = None,
        read_concern: ReadConcern | None = None,
        **kwargs: Any,
    ) -> None:
        ...

    def __getitem__(self, name: str) -> MongoCollection[_DocumentType]:
        ...

    async def create_collection(
        self,
        name: str,
        codec_options: CodecOptions | None = None,
        read_preference: Any | None = None,
        write_concern: WriteConcern | None = None,
        read_concern: ReadConcern | None = None,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> MongoCollection[_DocumentType]:
        ...

    async def drop_collection(
        self,
        name_or_collection: str | MongoCollection[_DocumentType],
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> None:
        ...

    async def list_collection_names(
        self,
        session: ClientSession | None = None,
        filter: Mapping[str, Any] | None = None,  # noqa: A002
        **kwargs: Any,
    ) -> list[str]:
        ...

    async def list_collections(
        self,
        session: ClientSession | None = None,
        filter: Mapping[str, Any] | None = None,  # noqa: A002
        **kwargs: Any,
    ) -> CommandCursor[MutableMapping[str, Any]]:
        ...

    async def command(
        self,
        command: MutableMapping[str, Any],
        value: Any = 1,
        check: bool = True,
        allowable_errors: Any | None = None,
        read_preference: Any | None = None,
        codec_options: CodecOptions | None = None,
        **kwargs: Any,
    ) -> MutableMapping[str, Any]:
        ...

    async def command_cursor(
        self,
        command: MutableMapping[str, Any],
        value: Any = 1,
        check: bool = True,
        allowable_errors: Any | None = None,
        read_preference: Any | None = None,
        codec_options: CodecOptions | None = None,
        **kwargs: Any,
    ) -> CommandCursor[MutableMapping[str, Any]]:
        ...

    async def aggregate(
        self,
        pipeline: _Pipeline,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> CommandCursor:
        ...
