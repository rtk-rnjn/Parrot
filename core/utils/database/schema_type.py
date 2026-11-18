from typing import Any, Literal, TypedDict

type BsonType = Literal[
    "double",
    "string",
    "object",
    "array",
    "binData",
    "objectId",
    "bool",
    "date",
    "null",
    "regex",
    "javascript",
    "int",
    "timestamp",
    "long",
    "decimal",
    "minKey",
    "maxKey",
    "number",
]

type JsonType = Literal["object", "array", "number", "boolean", "string", "null"]

type Number = int | float


class Schema(TypedDict, total=False):
    bsonType: BsonType | list[BsonType]
    type: JsonType | list[JsonType]
    enum: list[Any]
    title: str
    description: str

    allOf: list[Schema]
    anyOf: list[Schema]
    oneOf: list[Schema]

    properties: dict[str, Schema]
    patternProperties: dict[str, Schema]
    additionalProperties: bool | Schema
    required: list[str]
    minProperties: int
    maxProperties: int
    dependencies: dict[str, list[str] | Schema]

    items: Schema | list[Schema]
    additionalItems: bool | Schema
    minItems: int
    maxItems: int
    uniqueItems: bool

    minimum: Number
    maximum: Number
    exclusiveMinimum: bool
    exclusiveMaximum: bool
    multipleOf: Number

    minLength: int
    maxLength: int
    pattern: str
