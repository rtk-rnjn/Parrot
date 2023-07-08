from __future__ import annotations

import json

from typing_extensions import Self


class BaseModel:
    def __init__(self, **kwargs) -> None:
        self._raw: dict = kwargs

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._raw}>"

    def _to_dict(self) -> dict:
        # recursively convert all BaseModel objects to dicts
        return {
            k: v._to_dict() if isinstance(v, BaseModel) else v
            for k, v in self._raw.items()
        }

    def _to_json(self) -> str:
        return json.dumps(self._raw, indent=4)

    @classmethod
    def _from_dict(cls, data: dict) -> Self:
        return cls(**data)
